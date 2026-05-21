# Jobs & Scheduling

## What Is a Job?

A **Job** is a cron-based schedule attached to an Odoo instance. Each job runs at the configured interval, backs up the databases you selected, and optionally verifies the resulting archive. Multiple jobs can be attached to the same instance — for example, a daily full backup and a more frequent lightweight backup of a subset of databases.

## Creating a Job

1. Open an instance from **Instances**
2. Click **+ Add Job** on the Instance Detail page
3. Fill in the form:

| Field | Description |
|-------|-------------|
| Name | Human-readable label (e.g., "Daily at 2am") |
| Cron Expression | Schedule in standard cron format |
| Enabled | Toggle to activate/pause the job |
| Retention Mode | `keep_last_n` or `older_than_days` |
| Retention Value | N backups to keep, or age in days |
| Verify after backup | Run integrity check on the resulting archive |

4. Click **Save**. The scheduler picks up the new job within 30 seconds.

## Cron Expression Builder

The UI provides a visual builder with four preset modes:

=== "Hourly"
    Runs every N hours at minute 0. Set the interval with the slider.

=== "Daily"
    Runs once per day at a specified hour and minute.

=== "Weekly"
    Runs on selected days of the week at a specified time.

=== "Monthly"
    Runs on a specific day of the month at a specified time.

=== "Custom"
    Type a raw cron expression directly (5 fields: `minute hour day month weekday`).

Beneath the builder, the **Next 5 runs** preview shows exact timestamps in your configured timezone. This preview is computed server-side via `/api/settings/cron/preview`.

### Common Expressions

| Expression | Meaning |
|------------|---------|
| `0 2 * * *` | Every day at 02:00 |
| `0 */6 * * *` | Every 6 hours |
| `0 3 * * 1` | Every Monday at 03:00 |
| `30 1 1 * *` | First day of month at 01:30 |
| `0 4 * * 1,4` | Monday and Thursday at 04:00 |

!!! note "Timezone"
    All cron expressions are evaluated in the timezone set in **Settings**. The default is UTC until you change it.

## Running a Job Manually

Click **Run now** on the Instance Detail page next to any job. The backup starts immediately in the background and the run appears in the history list within seconds.

## Job Status and History

The **Run History** table on the Instance Detail page shows the last 50 runs for the instance, across all jobs. Each row shows:

- **Status** — `running` / `success` / `failed` / `verified` / `verify_failed`
- **Database** — the database name backed up
- **Started** — timestamp in your local timezone
- **Duration** — how long the backup took
- **Size** — compressed file size on disk
- **Error** — first 160 characters of the error message (if any)

Click a row to open the full run detail, including the complete error traceback and cloud sync status per destination.

## Pausing and Resuming

Toggle the **Enabled** switch on any job to pause it. The scheduler removes the entry from its queue within 30 seconds. Re-enabling re-adds it with the next computed fire time based on the current wall-clock time.

Pausing a job does not delete its run history or backups.

## Deleting a Job

Click the trash icon on the job row. This removes the schedule but does **not** delete existing backup files. Backup files are only removed by the retention policy or manual deletion.

## How Scheduling Works Internally

The scheduler is **celery-redbeat** — a Redis-backed dynamic Beat scheduler. On startup and every 30 seconds thereafter, a `refresh_schedules` task reconciles the jobs in the database with the running redbeat schedule:

- New enabled jobs → `RedBeatSchedulerEntry` added
- Disabled or deleted jobs → entry removed
- Changed cron expression → entry replaced

This means you can add, edit, or delete jobs at any time without restarting any service.

## Concurrency and Overlap

Each job fires as an independent Celery task on the `backups` queue. If a previous run is still executing when the next fire time arrives, both runs execute in parallel. If you want to prevent overlap for a resource-constrained instance, set a generous cron interval, or use a single worker with `--concurrency=1`.
