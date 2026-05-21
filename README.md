# Odoo Backup Orchestrator

> **Self-hosted backup orchestration for one or many Odoo instances — scheduled, audited, notified, and cloud-synced.**

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/cagatayuresin/odoo-backup-app/actions/workflows/ci.yml/badge.svg)](https://github.com/cagatayuresin/odoo-backup-app/actions/workflows/ci.yml)
[![Docker Image](https://img.shields.io/badge/docker-ghcr.io%2Fcagatayuresin%2Fodoo--backup--app-blue?logo=docker)](https://github.com/cagatayuresin/odoo-backup-app/pkgs/container/odoo-backup-app)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-green)](https://cagatayuresin.github.io/odoo-backup-app/)
[![GitHub Stars](https://img.shields.io/github/stars/cagatayuresin/odoo-backup-app)](https://github.com/cagatayuresin/odoo-backup-app/stargazers)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Made with Vue 3](https://img.shields.io/badge/Vue-3-42b883.svg?logo=vue.js)](https://vuejs.org/)

---

## What it does

Odoo Backup Orchestrator is a lightweight, self-hostable service that:

- **Schedules backups** for one or many Odoo instances using flexible cron expressions
- **Supports two backup strategies**: Odoo's built-in `/web/database/backup` endpoint or direct `pg_dump` (with optional filestore archive)
- **Verifies** every backup for integrity immediately after creation
- **Enforces retention policies** automatically — with a safety net that prevents deleting the last copy
- **Delivers notifications** via SMTP email and Telegram when jobs succeed or fail
- **Syncs backups to the cloud** (Google Drive, Dropbox, OneDrive) with optional remote retention
- **Audits** every action to an immutable log

All configuration is done through a clean, responsive web UI. No YAML editing, no crontab wrangling.

---

## Screenshots

| Dashboard | Instance Detail | Job Editor |
|---|---|---|
| ![Dashboard](docs/assets/screenshots/dashboard.png) | ![Instance](docs/assets/screenshots/instance-detail.png) | ![Job](docs/assets/screenshots/job-editor.png) |

---

## Features

- **Multi-instance management** — manage backups for any number of Odoo installations from a single pane
- **Two backup methods** — Odoo endpoint (zero-dependency) or pg_dump (faster, no master password needed)
- **Flexible DB selection** — single database, hand-picked list, or auto-discover all
- **Filestore archiving** — optionally bundle the Odoo filestore alongside the database dump
- **Visual cron builder** — build schedules in plain English or write raw cron; live next-run preview
- **Timezone-aware UI** — all schedules stored in UTC, displayed in your configured timezone
- **Integrity verification** — every backup is verified after creation (ZIP integrity or pg_restore --list)
- **Retention enforcement** — keep-last-N or delete-older-than-N-days, with an inviolable safety net
- **SMTP + Telegram notifications** — multiple channels, per-instance bindings, per-event toggles
- **Cloud sync** — Google Drive, Dropbox, OneDrive; per-instance, per-provider configuration
- **Password recovery** — configurable email-based reset flow
- **Audit log** — immutable record of every action taken by the app or the admin
- **Single-image Docker deploy** — one `docker compose up -d` and you're running

---

## Quickstart

```bash
git clone https://github.com/cagatayuresin/odoo-backup-app.git
cd odoo-backup-app
docker compose up -d
# Visit http://localhost:8080 — login: admin / admin
```

On first login you will be prompted to change the default password. Do not skip password recovery setup — losing the password without it means losing access to your data.

---

## Configuration

All runtime configuration is done via environment variables passed to the Docker services:

| Variable | Default | Description |
|---|---|---|
| `OB_DATA_DIR` | `/data` | Path to persistent storage volume |
| `OB_SECRET_KEY` | auto-generated | Seed for deriving the Fernet encryption key |
| `OB_SESSION_SECRET` | auto-generated | HMAC key for signed session cookies |
| `REDIS_URL` | `redis://redis:6379/0` | Celery broker + result backend |
| `OB_LOG_LEVEL` | `INFO` | Python logging level |

Full configuration reference → [docs/installation.md](https://cagatayuresin.github.io/odoo-backup-app/installation/)

---

## Architecture

```
┌─────────────────────────────────────────────┐
│  Browser (Vue 3 SPA + Bulma)                │
└──────────────────┬──────────────────────────┘
                   │ HTTP/JSON
┌──────────────────▼──────────────────────────┐
│  web  ─  FastAPI (uvicorn)                  │
│          • REST API (auth, instances, jobs,  │
│            backups, channels, cloud)        │
│          • Serves built Vue SPA             │
└──────┬───────────────────────┬──────────────┘
       │ Celery tasks          │ SQLAlchemy
┌──────▼──────┐  ┌─────────┐  ┌▼────────────┐
│  worker     │  │  beat   │  │ SQLite DB   │
│  (Celery)   │  │ (Beat+  │  │ /data/db/   │
│             │  │ redbeat)│  │ app.sqlite  │
└──────┬──────┘  └────┬────┘  └─────────────┘
       │              │
┌──────▼──────────────▼──────────────────────┐
│  redis:7-alpine (broker + result backend)  │
└────────────────────────────────────────────┘
```

Detailed architecture → [docs/architecture.md](https://cagatayuresin.github.io/odoo-backup-app/architecture/)

---

## Development

```bash
# Clone and enter the repo
git clone https://github.com/cagatayuresin/odoo-backup-app.git
cd odoo-backup-app

# Install pre-commit hooks
pip install pre-commit && pre-commit install

# Start the full dev stack (hot-reload on backend + Vite HMR on frontend)
make dev-up

# Backend tests
make test

# All quality checks
make audit
```

See [docs/architecture.md](https://cagatayuresin.github.io/odoo-backup-app/architecture/) for the full developer guide.

---

## Roadmap

- **Restore from UI** — trigger a pg_restore or Odoo database restore directly from the Backups page
- **Multi-user support** — role-based access (admin / viewer) with per-instance permissions
- **S3 / MinIO cloud backend** — in addition to Drive, Dropbox, and OneDrive
- **Slack / webhook notifications** — generic outbound webhook for custom integrations
- **Backup diff reporting** — size trend charts on the Dashboard

---

## License

MIT — see [LICENSE](LICENSE).

Copyright © 2026 [Çağatay Üresin](https://github.com/cagatayuresin)
