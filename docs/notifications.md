# Notifications

## Overview

The orchestrator can send alerts when backups succeed or fail. Notifications are delivered through **channels** — reusable connection configurations that can be bound to any number of instances. Two channel types are supported:

- **SMTP** — email via any standard SMTP server (Gmail, Outlook, Mailgun, your own Postfix, etc.)
- **Telegram** — instant message to a bot chat or group

## Creating a Channel

Navigate to **Channels** and click **+ Add Channel**. Choose the type, fill in the connection details, and click **Test** to send a verification message before saving.

### SMTP Channel

| Field | Example | Notes |
|-------|---------|-------|
| Name | `Mailgun Production` | Display name |
| Host | `smtp.mailgun.org` | Hostname or IP |
| Port | `587` | Standard: 587 (STARTTLS) or 465 (SSL) |
| Username | `postmaster@mg.example.com` | SMTP auth user |
| Password | — | Stored encrypted at rest |
| Use TLS | ✓ | Enables STARTTLS on port 587 |
| From address | `backup@example.com` | Envelope and display From |

!!! warning "Password storage"
    SMTP passwords are stored in the database Fernet-encrypted. The encryption key lives at `/data/secret.key`. Back this file up — without it, stored credentials cannot be decrypted.

### Telegram Channel

| Field | Example | Notes |
|-------|---------|-------|
| Name | `Ops Alerts` | Display name |
| Bot Token | `7123456789:AAF…` | From @BotFather |
| Chat ID | `-1001234567890` | Group or user ID |

To get a chat ID: add your bot to the group, send any message, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates` and look for `"chat":{"id":…}`.

## Binding a Channel to an Instance

Channels must be explicitly bound to instances. This lets you, for example, send Gmail alerts for one customer's instance but Telegram alerts for another.

1. Open the Instance Detail page
2. Scroll to **Notification Bindings**
3. Click **+ Bind Channel**
4. Select the channel and configure:

| Option | Default | Description |
|--------|---------|-------------|
| On success | off | Send when a run completes with status `success` or `verified` |
| On failure | on | Send when a run completes with status `failed` or `verify_failed` |

You can bind the same channel multiple times to the same instance with different event toggles — though in practice one binding is usually sufficient.

## Notification Content

### Email (SMTP)

Each email is sent as HTML with a responsive layout styled in the Odoo color palette. The subject line follows this pattern:

```
[Odoo Backup] ✓ mycompany — production — 2024-03-15 02:00
[Odoo Backup] ✗ mycompany — production — 2024-03-15 02:00
```

The body includes:

- Instance name and URL
- Database name
- Backup file size and path
- Duration
- Error message and traceback (failure only)
- Link to the run in the UI

### Telegram

Messages are formatted with Markdown and emojis for quick scanning:

```
✅ Backup succeeded
Instance: mycompany (https://erp.mycompany.com)
DB: production
Size: 142 MB  Duration: 47s
```

```
❌ Backup failed
Instance: mycompany
DB: production
Error: Connection refused (host=db, port=5432)
```

## Password Reset Emails

The SMTP channel configured in **Settings → Password recovery** is also used to send password reset tokens. This is a separate use from the backup notification bindings — you don't need to bind it to any instance for password reset to work.

## Disabling All Notifications for an Instance

On the Instance Detail page, toggle **Notifications enabled** off. This suppresses all delivery for that instance regardless of individual binding settings. Use this during maintenance windows to avoid alert storms.

## Troubleshooting

**Test email not arriving**

1. Check the channel's test result — it shows the SMTP response code.
2. Verify your SMTP credentials by logging in with a mail client.
3. Check your spam folder; some providers flag automated senders.
4. For Gmail, you must use an App Password (not your account password) and enable "Less secure app access" or OAuth2.

**Telegram messages not delivered**

1. Confirm the bot is a member of the group (for group chat IDs).
2. Send `/start` to the bot in a private chat before the first message.
3. Verify the chat ID with the `getUpdates` API — the sign matters (`-100…` for supergroups).

**Notifications delayed**

Notifications run on the `notifications` Celery queue. If the worker is overwhelmed by backup tasks, notifications queue up. Scale the worker or dedicate a separate worker to the `notifications` queue:

```bash
celery -A app.tasks.celery_app worker -Q notifications --concurrency=2
```
