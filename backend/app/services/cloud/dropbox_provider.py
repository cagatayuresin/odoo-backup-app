"""Dropbox cloud provider."""

from __future__ import annotations

import json
import logging
from datetime import UTC
from pathlib import Path

from app.services.cloud.base import RemoteFile

logger = logging.getLogger(__name__)


class DropboxProvider:
    """Upload / list / delete via Dropbox API v2."""

    def __init__(self, credentials: dict[str, str]) -> None:
        """Initialise with OAuth2 credentials (access_token + optional refresh_token)."""
        import dropbox

        access_token = credentials.get("access_token")
        refresh_token = credentials.get("refresh_token")
        app_key = credentials.get("app_key")
        app_secret = credentials.get("app_secret")

        if refresh_token and app_key and app_secret:
            self._dbx: dropbox.Dropbox = dropbox.Dropbox(
                oauth2_refresh_token=refresh_token,
                app_key=app_key,
                app_secret=app_secret,
            )
        else:
            self._dbx = dropbox.Dropbox(oauth2_access_token=access_token)

    def upload(self, local_path: Path, remote_folder: str) -> str:
        """Upload *local_path* to *remote_folder* and return the Dropbox path."""
        import dropbox

        remote_path = f"{remote_folder.rstrip('/')}/{local_path.name}"
        chunk_size = 10 * 1024 * 1024  # 10 MiB

        file_size = local_path.stat().st_size
        if file_size <= chunk_size:
            with local_path.open("rb") as fh:
                self._dbx.files_upload(
                    fh.read(),
                    remote_path,
                    mode=dropbox.files.WriteMode.overwrite,
                )
        else:
            with local_path.open("rb") as fh:
                session_start = self._dbx.files_upload_session_start(fh.read(chunk_size))
                cursor = dropbox.files.UploadSessionCursor(
                    session_id=session_start.session_id,
                    offset=fh.tell(),
                )
                commit = dropbox.files.CommitInfo(
                    path=remote_path,
                    mode=dropbox.files.WriteMode.overwrite,
                )
                while fh.tell() < file_size:
                    chunk = fh.read(chunk_size)
                    if (fh.tell() - len(chunk)) + len(chunk) == file_size:
                        self._dbx.files_upload_session_finish(chunk, cursor, commit)
                    else:
                        self._dbx.files_upload_session_append_v2(chunk, cursor)
                        cursor.offset = fh.tell()

        logger.info("Uploaded %s to Dropbox at %s", local_path.name, remote_path)
        return remote_path

    def list_files(self, remote_folder: str) -> list[RemoteFile]:
        """Return files in *remote_folder*."""
        try:
            result = self._dbx.files_list_folder(remote_folder)
        except Exception:
            logger.warning("Cannot list Dropbox folder %s — may not exist yet", remote_folder)
            return []

        remote_files = []
        for entry in result.entries:
            import dropbox.files

            if isinstance(entry, dropbox.files.FileMetadata):
                remote_files.append(
                    RemoteFile(
                        remote_id=entry.id,
                        name=entry.name,
                        size_bytes=entry.size,
                        modified_at=entry.server_modified.replace(tzinfo=UTC),
                    )
                )
        return sorted(remote_files, key=lambda f: f.modified_at, reverse=True)

    def delete_file(self, remote_id: str) -> None:
        """Delete a Dropbox file by path (remote_id is the path)."""
        self._dbx.files_delete_v2(remote_id)
        logger.info("Deleted Dropbox file %s", remote_id)


def build_provider(credentials_json: str) -> DropboxProvider:
    """Construct a DropboxProvider from credentials JSON."""
    credentials = json.loads(credentials_json)
    return DropboxProvider(credentials)
