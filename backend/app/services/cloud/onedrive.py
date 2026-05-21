"""Microsoft OneDrive / Graph API cloud provider."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

import httpx
import msal

from app.services.cloud.base import RemoteFile

logger = logging.getLogger(__name__)

_GRAPH = "https://graph.microsoft.com/v1.0"
_TIMEOUT = httpx.Timeout(connect=30.0, read=3600.0, write=60.0, pool=5.0)
_SCOPES = ["https://graph.microsoft.com/Files.ReadWrite"]


class OneDriveProvider:
    """Upload / list / delete via Microsoft Graph API."""

    def __init__(self, credentials: dict[str, str]) -> None:
        """Initialise with MSAL credentials (client_id, client_secret, tenant_id, refresh_token)."""
        self._client_id = credentials["client_id"]
        self._client_secret = credentials["client_secret"]
        self._tenant_id = credentials.get("tenant_id", "common")
        self._refresh_token = credentials.get("refresh_token", "")

        self._msal_app = msal.ConfidentialClientApplication(
            client_id=self._client_id,
            client_credential=self._client_secret,
            authority=f"https://login.microsoftonline.com/{self._tenant_id}",
        )

    def _access_token(self) -> str:
        """Acquire an access token using the stored refresh token."""
        result = self._msal_app.acquire_token_by_refresh_token(
            self._refresh_token,
            scopes=_SCOPES,
        )
        if "access_token" not in result:
            msg = f"Cannot acquire OneDrive token: {result.get('error_description', result)}"
            raise RuntimeError(msg)
        return result["access_token"]  # type: ignore[no-any-return]

    def _get_or_create_folder(self, token: str, folder_path: str) -> str:
        """Return the Drive item ID for *folder_path*, creating it if absent."""
        parts = folder_path.strip("/").split("/")
        current_id = "root"

        with httpx.Client(timeout=_TIMEOUT) as client:
            for part in parts:
                url = f"{_GRAPH}/me/drive/items/{current_id}/children?$filter=name eq '{part}' and folder ne null"
                resp = client.get(url, headers={"Authorization": f"Bearer {token}"})
                resp.raise_for_status()
                items = resp.json().get("value", [])
                if items:
                    current_id = items[0]["id"]
                else:
                    # Create the folder
                    create_url = f"{_GRAPH}/me/drive/items/{current_id}/children"
                    resp = client.post(
                        create_url,
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json",
                        },
                        content=json.dumps(
                            {
                                "name": part,
                                "folder": {},
                                "@microsoft.graph.conflictBehavior": "rename",
                            }
                        ).encode(),
                    )
                    resp.raise_for_status()
                    current_id = resp.json()["id"]

        return current_id

    def upload(self, local_path: Path, remote_folder: str) -> str:
        """Upload *local_path* to *remote_folder* via Graph upload session."""
        token = self._access_token()
        folder_id = self._get_or_create_folder(token, remote_folder)

        create_url = f"{_GRAPH}/me/drive/items/{folder_id}:/{local_path.name}:/createUploadSession"
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(
                create_url,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                content=json.dumps({"@microsoft.graph.conflictBehavior": "replace"}).encode(),
            )
            resp.raise_for_status()
            upload_url = resp.json()["uploadUrl"]

            chunk_size = 5 * 1024 * 1024  # 5 MiB
            file_size = local_path.stat().st_size
            with local_path.open("rb") as fh:
                start = 0
                item_id = ""
                while start < file_size:
                    chunk = fh.read(chunk_size)
                    end = start + len(chunk) - 1
                    put_resp = client.put(
                        upload_url,
                        content=chunk,
                        headers={
                            "Content-Range": f"bytes {start}-{end}/{file_size}",
                            "Content-Length": str(len(chunk)),
                        },
                    )
                    if put_resp.status_code in {200, 201}:
                        item_id = put_resp.json().get("id", "")
                    start = end + 1

        logger.info(
            "Uploaded %s to OneDrive folder %s (id=%s)", local_path.name, remote_folder, item_id
        )
        return item_id

    def list_files(self, remote_folder: str) -> list[RemoteFile]:
        """Return files in *remote_folder*."""
        token = self._access_token()
        folder_id = self._get_or_create_folder(token, remote_folder)

        url = f"{_GRAPH}/me/drive/items/{folder_id}/children?$select=id,name,size,lastModifiedDateTime&$orderby=lastModifiedDateTime desc"
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.get(url, headers={"Authorization": f"Bearer {token}"})
            resp.raise_for_status()

        remote_files = []
        for item in resp.json().get("value", []):
            if "folder" not in item:  # skip sub-folders
                remote_files.append(
                    RemoteFile(
                        remote_id=item["id"],
                        name=item["name"],
                        size_bytes=item.get("size", 0),
                        modified_at=datetime.fromisoformat(
                            item["lastModifiedDateTime"].replace("Z", "+00:00")
                        ),
                    )
                )
        return remote_files

    def delete_file(self, remote_id: str) -> None:
        """Delete a OneDrive item by ID."""
        token = self._access_token()
        url = f"{_GRAPH}/me/drive/items/{remote_id}"
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.delete(url, headers={"Authorization": f"Bearer {token}"})
            resp.raise_for_status()
        logger.info("Deleted OneDrive item %s", remote_id)


def build_provider(credentials_json: str) -> OneDriveProvider:
    """Construct an OneDriveProvider from credentials JSON."""
    credentials = json.loads(credentials_json)
    return OneDriveProvider(credentials)
