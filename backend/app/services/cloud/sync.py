"""Cloud sync orchestrator — uploads a backup run to all configured cloud accounts."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.retention import compute_deletions
from app.core.security import decrypt_secret
from app.models.backup import BackupRun
from app.models.cloud import CloudAccount, CloudProvider, InstanceCloudBinding

logger = logging.getLogger(__name__)


def _build_provider(account: CloudAccount) -> object:
    """Instantiate the correct provider for *account*."""
    credentials_json = decrypt_secret(account.credentials_enc)

    if account.provider == CloudProvider.gdrive:
        from app.services.cloud.drive import build_provider as drive_build

        return drive_build(credentials_json)
    if account.provider == CloudProvider.dropbox:
        from app.services.cloud.dropbox_provider import build_provider as dropbox_build

        return dropbox_build(credentials_json)
    if account.provider == CloudProvider.onedrive:
        from app.services.cloud.onedrive import build_provider as onedrive_build

        return onedrive_build(credentials_json)

    msg = f"Unknown cloud provider: {account.provider}"
    raise ValueError(msg)


def sync_run(run: BackupRun, db: Session) -> None:
    """Upload *run*'s file to all enabled cloud destinations and apply remote retention."""
    if not run.file_path or not Path(run.file_path).is_file():
        logger.warning("BackupRun %d has no file on disk — skipping cloud sync", run.id)
        return

    bindings: list[InstanceCloudBinding] = (
        db.query(InstanceCloudBinding)
        .filter(
            InstanceCloudBinding.instance_id == run.instance_id,
            InstanceCloudBinding.enabled.is_(True),
        )
        .all()
    )

    cloud_status: dict[str, str] = json.loads(run.cloud_sync_status or "{}")

    for binding in bindings:
        account = db.get(CloudAccount, binding.cloud_account_id)
        if account is None or not account.enabled:
            continue

        provider_key = account.provider.value
        try:
            provider = _build_provider(account)
            provider.upload(Path(run.file_path), binding.remote_folder)  # type: ignore[attr-defined]
            cloud_status[provider_key] = "uploaded"
            logger.info(
                "Synced run %d to %s folder %s",
                run.id,
                provider_key,
                binding.remote_folder,
            )

            if binding.apply_retention_remotely:
                _apply_remote_retention(run, binding, provider, db)

        except Exception:
            logger.exception("Cloud sync failed for run %d to %s", run.id, provider_key)
            cloud_status[provider_key] = "failed"

    run.cloud_sync_status = json.dumps(cloud_status)
    db.commit()


def _apply_remote_retention(
    run: BackupRun,
    binding: InstanceCloudBinding,
    provider: object,
    db: Session,
) -> None:
    """Apply the instance's retention policy to remote files in *binding.remote_folder*."""
    instance = run.instance
    if instance is None:
        return

    remote_files = provider.list_files(binding.remote_folder)  # type: ignore[attr-defined]
    if not remote_files:
        return

    # Build (remote_id, modified_at) list oldest-first
    files_oldest_first = sorted(remote_files, key=lambda f: f.modified_at)
    run_pairs = [(f.remote_id, f.modified_at) for f in files_oldest_first]

    deletions, safety_triggered = compute_deletions(
        run_pairs,
        instance.retention_mode.value,
        instance.retention_value,
    )

    if safety_triggered:
        logger.warning(
            "Remote retention for instance %s would delete all files in %s — skipped",
            instance.slug,
            binding.remote_folder,
        )
        return

    for remote_id in deletions:
        try:
            provider.delete_file(remote_id)  # type: ignore[attr-defined]
        except Exception:
            logger.exception("Could not delete remote file %s", remote_id)
