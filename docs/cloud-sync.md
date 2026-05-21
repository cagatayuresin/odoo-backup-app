# Cloud Sync

## Overview

After each successful backup, the orchestrator can automatically upload the archive to one or more cloud storage destinations. Supported providers:

| Provider | Auth method | SDK |
|----------|------------|-----|
| Google Drive | OAuth2 service account | `google-api-python-client` |
| Dropbox | App access token | `dropbox` |
| OneDrive | OAuth2 client credentials | `msal` + REST |

Uploads run on the `cloud` Celery queue, in parallel with retention and notification tasks, so they do not block the next scheduled backup.

## Adding a Cloud Account

Navigate to **Cloud → Add Account**, choose the provider, and follow the provider-specific setup below.

### Google Drive

You need a **service account** with Drive access.

1. In [Google Cloud Console](https://console.cloud.google.com), create a project (or use an existing one).
2. Enable the **Google Drive API**.
3. Create a **Service Account** under IAM & Admin → Service Accounts.
4. Download the JSON key file.
5. Share the target Google Drive folder with the service account email (e.g., `backup-agent@my-project.iam.gserviceaccount.com`). Give it **Editor** access.
6. In the orchestrator, paste the full JSON key content into the **Credentials JSON** field.
7. Enter the **Folder ID** — the long ID at the end of the folder's Drive URL.

!!! warning
    The credentials JSON contains a private key and is stored Fernet-encrypted in the database. Never commit it to version control.

### Dropbox

1. Go to [Dropbox App Console](https://www.dropbox.com/developers/apps).
2. Create an app with **Full Dropbox** or **App Folder** access (App Folder is more restrictive and recommended).
3. Generate an **Access Token** on the app's settings page.
4. In the orchestrator, paste the token into **Access Token**.
5. Set the **Remote path** where backups will be uploaded (e.g., `/odoo-backups/`).

### OneDrive

1. Register an app in [Azure Active Directory](https://portal.azure.com) → App Registrations.
2. Add the `Files.ReadWrite` Microsoft Graph permission and grant admin consent.
3. Create a **Client Secret** under Certificates & secrets.
4. Note the **Tenant ID**, **Client ID**, and **Client Secret**.
5. Enter these in the orchestrator's OneDrive account form along with the **Remote path**.

## Binding a Cloud Account to an Instance

A cloud account must be bound to an instance before uploads happen.

1. Open the Instance Detail page.
2. Scroll to **Cloud Sync Bindings**.
3. Click **+ Bind Cloud Account**.
4. Select the account, then configure:

| Option | Default | Description |
|--------|---------|-------------|
| Remote path | `/odoo-backups/{instance_slug}/` | Destination folder on the cloud |
| Enabled | on | Toggle to pause syncing to this destination |
| Remote retention: keep last N | — | Delete older remote files, keeping N most recent (leave blank to disable) |

You can bind the same cloud account to multiple instances with different remote paths, or bind multiple cloud accounts to one instance.

## Remote Retention

When **keep last N** is set on a binding, after each successful upload the orchestrator lists the remote files for that instance path, sorts them by upload date, and deletes the oldest ones — keeping only N.

The same safety net that protects local backups applies here: if the deletion would remove all remote files, it is skipped and an audit entry is written.

!!! note
    Remote retention is independent of local retention. You can keep 7 local backups and 30 remote ones, or vice versa.

## Monitoring Sync Status

The **Run History** table shows a **Cloud** column with per-destination icons:

- **✓** — uploaded successfully
- **✗** — upload failed (hover for error)
- **↻** — upload pending or retrying
- **—** — no cloud binding configured

Open a run row to see the full `cloud_sync_status` JSON with per-account details.

## Manual Re-upload

If an upload failed, click **Re-upload** on the run detail page. This enqueues a new cloud sync task for that specific run without re-running the backup itself.

## Supported File Types

All archives produced by the orchestrator are uploaded as-is:

- `.zip` — Odoo endpoint backups (includes filestore)
- `.dump` — pg_dump custom-format database dump
- `.tar.gz` — pg_dump with filestore

## Security Considerations

- All provider credentials (API keys, tokens, client secrets) are stored Fernet-encrypted in the database.
- The encryption key at `/data/secret.key` must be backed up independently — losing it means provider credentials cannot be recovered.
- Uploads use HTTPS exclusively; no plain-HTTP cloud endpoints are supported.
- The service account / app registration should be granted the minimum required permissions (Files.ReadWrite, not admin-level Drive/OneDrive access).
