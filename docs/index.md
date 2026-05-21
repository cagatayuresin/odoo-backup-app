# Odoo Backup Orchestrator

> **Self-hosted backup orchestration for one or many Odoo instances — scheduled, audited, notified, and cloud-synced.**

Odoo Backup Orchestrator is a lightweight, self-hostable service that automates the backup lifecycle for your Odoo installations. It runs entirely on your own infrastructure — no data leaves your servers unless you explicitly configure cloud sync.

## Key Features

| Feature | Description |
|---|---|
| **Multi-instance** | Manage backups for any number of Odoo installations from a single UI |
| **Two backup methods** | Odoo built-in endpoint or direct `pg_dump` (with optional filestore) |
| **Flexible scheduling** | Cron expressions with visual builder and live next-run preview |
| **Integrity verification** | Every backup is automatically verified after creation |
| **Smart retention** | Keep-last-N or delete-older-than-N-days, with an inviolable safety net |
| **Notifications** | SMTP email and Telegram, with per-instance, per-event bindings |
| **Cloud sync** | Google Drive, Dropbox, OneDrive — per-instance, optional remote retention |
| **Audit log** | Immutable record of every action taken by the app or admin |
| **Single-image deploy** | One `docker compose up -d` and you're running |

## Quick Start

```bash
git clone https://github.com/cagatayuresin/odoo-backup-app.git
cd odoo-backup-app
docker compose up -d
# Visit http://localhost:8080  —  login: admin / admin
```

On first login you will be prompted to change the default password. Configure password recovery immediately — without it, losing your password means losing access.

## How It Works

```
Browser (Vue 3 SPA)
       │
       ▼
FastAPI REST API  ◄──────────────────────────────┐
       │                                          │
       ▼                                          │
Celery Worker ──► Backup ──► Verify ──► Retain   │
                                  │               │
                                  ▼               │
                             Cloud Sync ──────────┘
                             Notifications
```

Backups run on a Celery worker queue, scheduled by Celery Beat with `celery-redbeat` for dynamic (DB-driven) schedules. All metadata is stored in a SQLite database. Backup files land on the local filesystem (bind-mounted to `./data/backups`).

## Next Steps

- [Installation →](installation.md) — deploy with Docker or bare-metal
- [First Run →](first-run.md) — initial setup walkthrough
- [Jobs & Scheduling →](jobs.md) — configure backup schedules
