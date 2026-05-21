"""Google Drive cloud provider."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from app.services.cloud.base import RemoteFile

logger = logging.getLogger(__name__)


class GoogleDriveProvider:
    """Upload / list / delete via Google Drive API v3."""

    def __init__(self, credentials: dict[str, str]) -> None:
        """Initialise with OAuth credentials dict (token, refresh_token, client_id, etc.)."""
        import google.oauth2.credentials
        from googleapiclient.discovery import build

        creds = google.oauth2.credentials.Credentials(
            token=credentials.get("token"),
            refresh_token=credentials.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=credentials.get("client_id"),
            client_secret=credentials.get("client_secret"),
            scopes=["https://www.googleapis.com/auth/drive.file"],
        )
        self._service = build("drive", "v3", credentials=creds, cache_discovery=False)

    def _get_or_create_folder(self, folder_name: str) -> str:
        """Return the ID of a Drive folder, creating it if absent."""
        q = (
            f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
            " and trashed=false"
        )
        results = (
            self._service.files()  # type: ignore[attr-defined]
            .list(q=q, fields="files(id)", pageSize=1)
            .execute()
        )
        files: list[dict[str, str]] = results.get("files", [])
        if files:
            return files[0]["id"]

        metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        folder = (
            self._service.files()  # type: ignore[attr-defined]
            .create(body=metadata, fields="id")
            .execute()
        )
        return folder["id"]  # type: ignore[no-any-return]

    def upload(self, local_path: Path, remote_folder: str) -> str:
        """Upload a file to *remote_folder* and return the Drive file ID."""
        from googleapiclient.http import MediaFileUpload

        folder_id = self._get_or_create_folder(remote_folder.lstrip("/"))
        media = MediaFileUpload(str(local_path), resumable=True)
        metadata = {"name": local_path.name, "parents": [folder_id]}
        result = (
            self._service.files()  # type: ignore[attr-defined]
            .create(body=metadata, media_body=media, fields="id")
            .execute()
        )
        file_id: str = result["id"]
        logger.info("Uploaded %s to Google Drive folder %s (id=%s)", local_path.name, remote_folder, file_id)
        return file_id

    def list_files(self, remote_folder: str) -> list[RemoteFile]:
        """Return files in *remote_folder*."""
        folder_id = self._get_or_create_folder(remote_folder.lstrip("/"))
        q = f"'{folder_id}' in parents and trashed=false"
        results = (
            self._service.files()  # type: ignore[attr-defined]
            .list(
                q=q,
                fields="files(id,name,size,modifiedTime)",
                orderBy="modifiedTime desc",
                pageSize=100,
            )
            .execute()
        )
        remote_files = []
        for f in results.get("files", []):
            remote_files.append(
                RemoteFile(
                    remote_id=f["id"],
                    name=f["name"],
                    size_bytes=int(f.get("size", 0)),
                    modified_at=datetime.fromisoformat(
                        f["modifiedTime"].replace("Z", "+00:00")
                    ),
                )
            )
        return remote_files

    def delete_file(self, remote_id: str) -> None:
        """Delete a Drive file by ID."""
        self._service.files().delete(fileId=remote_id).execute()  # type: ignore[attr-defined]
        logger.info("Deleted Google Drive file %s", remote_id)


def build_provider(credentials_json: str) -> GoogleDriveProvider:
    """Construct a GoogleDriveProvider from an encrypted-and-decrypted credentials JSON."""
    credentials = json.loads(credentials_json)
    return GoogleDriveProvider(credentials)
