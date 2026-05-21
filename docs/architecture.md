# Architecture

## Component Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Docker Host                                 │
│                                                                      │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐            │
│  │   web        │   │   worker     │   │   beat       │            │
│  │  (uvicorn)   │   │  (celery)    │   │  (redbeat)   │            │
│  │              │   │              │   │              │            │
│  │  FastAPI app │   │  Tasks:      │   │  Dynamic     │            │
│  │  Vue SPA     │   │  - backups   │   │  cron based  │            │
│  │  REST API    │   │  - notify    │   │  on DB jobs  │            │
│  │  Sessions    │   │  - cloud     │   │              │            │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘            │
│         │                  │                  │                     │
│         └──────────────────┴──────────────────┘                     │
│                            │                                        │
│                    ┌───────┴────────┐                               │
│                    │    redis:6379  │                               │
│                    │  (task queue + │                               │
│                    │  beat schedule)│                               │
│                    └───────┬────────┘                               │
│                            │                                        │
│         ┌──────────────────┤                                        │
│         │                  │                                        │
│  ┌──────┴───────┐  ┌───────┴────────┐                              │
│  │  /data/      │  │ Odoo instances │                              │
│  │  app.db      │  │ (external)     │                              │
│  │  secret.key  │  │                │                              │
│  │  backups/    │  │ /web/database/ │                              │
│  │  logs/       │  │  or pg_dump    │                              │
│  └──────────────┘  └────────────────┘                              │
└─────────────────────────────────────────────────────────────────────┘
```

## Service Roles

### `web` — FastAPI Application Server

Runs `uvicorn app.main:app`. Handles:

- REST API requests from the Vue frontend
- Session authentication (itsdangerous signed cookies)
- Static file serving of the compiled Vue bundle
- SPA fallback routing (all non-API paths return `index.html`)
- Startup tasks: Alembic migrations, admin user seed, Beat bootstrap

### `worker` — Celery Worker

Processes background tasks from four queues:

| Queue | Tasks |
|-------|-------|
| `default` | Miscellaneous, cron refresh, test-connection |
| `backups` | `run_backup_job`, `_execute_single_backup`, `verify_backup_run` |
| `notifications` | `dispatch_notification` |
| `cloud` | `sync_backup_to_cloud`, `apply_remote_retention` |

Default concurrency: 4 (set by `OB_WORKER_CONCURRENCY`). Tasks within the `backups` queue serialize per-job via a Celery `chain`, but different jobs run concurrently.

### `beat` — celery-redbeat Scheduler

Runs the Beat process with the **RedBeatScheduler** backend. Reads schedules from Redis rather than a static config file. The `refresh_schedules` task runs every 60 seconds to reconcile the Redis schedule with the `jobs` table in the database. This is how cron expression changes made in the UI propagate to the scheduler without restarts.

### `redis` — Message Broker + Schedule Store

Redis 7.2 serves two roles:

1. **Celery broker**: tasks are pushed to Redis queues and consumed by `worker`.
2. **Beat schedule store**: `beat` writes and reads `RedBeatSchedulerEntry` objects from Redis hashes.

Redis data is persisted in a named volume (`redis_data`). If Redis loses its data (e.g., container restart without persistence), the Beat scheduler rebuilds the schedule from the database on the next `refresh_schedules` tick (within 60 seconds).

## Data Model

```
User
  └─ has many AuditLog entries

Instance
  ├─ has many Job
  ├─ has many BackupRun (via Job)
  ├─ has many InstanceNotificationBinding → SmtpChannel / TelegramChannel
  └─ has many InstanceCloudBinding → CloudAccount

Job
  └─ has many BackupRun

BackupRun
  └─ cloud_sync_status: JSON {account_id: {status, error, remote_path}}

SmtpChannel
TelegramChannel
CloudAccount
```

All `*_enc` columns are transparently encrypted/decrypted by service-layer helper functions. The ORM models store the ciphertext; the API schemas expose the plaintext (write-only for passwords and tokens — they are never returned in GET responses).

## Request Lifecycle

A typical backup initiated by the scheduler:

```
[Beat] fire time reached
  → push task to Redis queue "backups"
[Worker] dequeue run_backup_job(job_id)
  → load Job + Instance from SQLite
  → for each database:
      → push _execute_single_backup(job_id, db_name)
        → download archive (Odoo endpoint or pg_dump)
        → save to /data/backups/{slug}/{db}/{filename}
        → create BackupRun row (status=success/failed)
        → if verify: push verify_backup_run
        → push apply_retention
        → push dispatch_notification
        → push sync_backup_to_cloud (per binding)
```

All sub-tasks are chained so that verification runs before retention and notification. Cloud sync runs in parallel with notification.

## Frontend Architecture

The Vue 3 SPA is built with Vite and served as static files from `dist/`. The FastAPI app mounts the `dist/` directory at `/` and serves `index.html` for all non-API paths.

```
frontend/
  src/
    api/          ← typed fetch wrappers (client.ts + index.ts)
    stores/       ← Pinia stores (auth, ui)
    router/       ← Vue Router with auth guards
    components/   ← CronBuilder, SetupBanner, InstanceCard, ClockBadge
    views/        ← one file per page (Dashboard, Instances, Jobs, …)
    assets/       ← SCSS, favicon
```

State management is minimal: only `auth` (current user) and `ui` (dismissed banner state) live in Pinia. All other data is fetched on-mount with `ref` / `onMounted`.

## Database

SQLite 3 with WAL journal mode. WAL enables concurrent readers while a write is in progress, which matters because `web` and `worker` both write to the same database file.

Pragmas applied on every connection:

```sql
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
PRAGMA busy_timeout=5000;
```

The 5-second busy timeout prevents immediate "database locked" errors under brief write contention.

Migrations are managed by Alembic with `render_as_batch=True` to support `ALTER TABLE` operations (not natively supported by SQLite without table recreation).

## Deployment

The application ships as a single Docker image (`cagatayuresin/odoo-backup-app:latest`) that contains both the backend Python code and the compiled Vue frontend. The `docker-compose.yml` starts all four services from this single image with different commands:

```yaml
web:    uvicorn app.main:app ...
worker: celery -A app.tasks.celery_app worker ...
beat:   celery -A app.tasks.celery_app beat ...
redis:  redis:7.2.5-alpine (separate image)
```

All services mount the same `app_data` volume at `/data`.
