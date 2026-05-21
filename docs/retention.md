# Retention Policy

## Why Retention Matters

Backup files accumulate quickly. A single Odoo instance with a 500 MB database, backed up daily, fills 15 GB per month. Without a retention policy, disk usage grows without bound. The orchestrator's retention system automates cleanup while providing a hard safety guarantee: **the last surviving backup is never automatically deleted.**

## Retention Modes

Each job has an independent retention policy. Two modes are available:

### Keep Last N (`keep_last_n`)

Keeps the N most recent successful backups for each database. After a successful run, the orchestrator sorts all existing backups for that database by creation time (newest first) and deletes anything beyond position N.

**Example:** `keep_last_n = 7`

```
run-001  2024-03-08  → kept (position 7)
run-002  2024-03-09  → kept (position 6)
...
run-007  2024-03-14  → kept (position 1, newest)
run-008  2024-03-15  → kept (just created)
run-000  2024-03-07  → deleted (position 9 > 7)
```

Minimum value: 1. Setting `keep_last_n = 0` is rejected at the API layer.

### Older Than N Days (`older_than_days`)

Deletes backups whose creation timestamp is older than N days from the current time. This mode is useful when you want a rolling window regardless of how many runs fired (e.g., if you added extra manual runs).

**Example:** `older_than_days = 30`

At evaluation time (2024-04-15), any backup created before 2024-03-16 is eligible for deletion.

Minimum value: 1. Setting `older_than_days = 0` is rejected at the API layer.

## The Safety Net

!!! danger "Last-backup protection"
    If the computed deletion set would remove **every** backup for a given database, the orchestrator **skips all deletions** for that database and writes a warning to the audit log.

This prevents two dangerous scenarios:

1. **Aggressive policy on a rarely-running job** — e.g., `older_than_days = 7` on a job that fires weekly. If the weekly run fails for 8 days, there may only be one backup remaining. Without the safety net, the policy would delete it.

2. **Migration mistake** — e.g., accidentally setting `keep_last_n = 1` and the most recent run failed. The last successful backup is preserved.

The safety net is silently triggered (no UI error). You will see a log line and an audit entry when it fires. Inspect **Audit Log** (accessible from the sidebar) to review these events.

## Per-Database Scope

Retention is scoped per database name, not per job. If your instance backs up three databases (`odoo`, `demo`, `test`), retention runs independently for each. Losing runs for `demo` does not affect the `odoo` backup count.

## Retention Timing

Retention runs **after** a successful backup, not on a separate schedule. The sequence for each job run is:

1. Download backup → save to disk
2. Verify archive integrity (if enabled)
3. **Apply retention** (delete old files, respecting safety net)
4. Upload to cloud destinations (parallel)
5. Send notifications (parallel)

Retention does not run after a failed backup. If a run fails, existing backups are left untouched.

## Manual Deletion

You can delete individual backups from the Run History table in the UI. Click the trash icon on any run row.

If the backup you're deleting is the **last** remaining backup for that database, the API requires two extra confirmation parameters:

- `force=true`
- `confirmation=DELETE`

The UI presents a confirmation dialog that sets these automatically. This guard exists to prevent accidental permanent data loss.

## Disk Space Planning

Use the following rough formula to estimate disk requirements:

```
disk_GB = avg_backup_GB × databases × keep_last_n × instances
```

For example: 10 instances × 3 databases × 0.5 GB × 7 days = **105 GB**.

Add 20–30% headroom for in-progress backups and temporary files during compression.

Monitor disk usage with the `/api/health` endpoint (which reports `disk_free_gb`) or your host's monitoring system. The orchestrator does not yet enforce a minimum free-space threshold before starting a backup.

## Remote Retention

Cloud sync destinations have their own independent retention setting (**keep last N** on the binding). See [Cloud Sync → Remote Retention](cloud-sync.md#remote-retention) for details. The same safety net applies to remote files.
