# FAQ

## General

**Q: Does this work with Odoo Community Edition?**

Yes. Both backup methods work with CE and EE. The Odoo Endpoint method uses `/web/database/backup`, which is available in all editions. The pg_dump method bypasses Odoo entirely and connects directly to PostgreSQL.

---

**Q: What versions of Odoo are supported?**

The Odoo Endpoint method has been tested with Odoo 14 through 17. The pg_dump method supports any PostgreSQL-backed Odoo version (practically all modern versions) and does not depend on the Odoo application at all.

---

**Q: Can I back up multiple Odoo instances from one orchestrator?**

Yes. There is no hard limit on the number of instances. Each instance has its own jobs, schedules, and notification bindings. All backups land in separate subdirectories under `/data/backups/`.

---

**Q: Does the backup include the filestore (attachments)?**

- **Odoo Endpoint**: Yes, always. The `/web/database/backup` endpoint returns a ZIP that includes both the database dump and the filestore.
- **pg_dump**: Only the database. Filestore sync is on the roadmap but not yet implemented.

---

**Q: My Odoo instance is behind a self-signed certificate. Will this work?**

No — the orchestrator enforces TLS certificate validation and does not support `verify=False`. Use a certificate signed by a recognized CA (including Let's Encrypt), or add your CA certificate to the orchestrator's trust store via the `SSL_CERT_FILE` environment variable.

---

## Backup Methods

**Q: Which backup method should I use?**

Use **Odoo Endpoint** if:
- You don't have direct database access
- You want the simplest setup (just the master password)
- You need the filestore included automatically

Use **pg_dump** if:
- The Odoo master password isn't available
- You have very large databases (pg_dump is faster for large DBs)
- You need fine-grained control (pg_dump custom format is more portable)

---

**Q: What's the Odoo master password?**

It's the `admin_passwd` in your Odoo `odoo.conf`. It's required to authenticate to the database manager endpoints. Find it with:

```bash
grep admin_passwd /etc/odoo/odoo.conf
```

---

**Q: The test connection fails for pg_dump. What should I check?**

1. Is the PostgreSQL host reachable from the orchestrator container? Try `ping` or `nc -z <host> 5432`.
2. Does the PostgreSQL user have `CONNECT` and `SELECT` privileges on the target database?
3. Is `pg_hba.conf` configured to allow connections from the orchestrator's IP?
4. Is the port correct? The default is 5432.

---

## Scheduling

**Q: Jobs aren't firing. How do I debug?**

1. Check that the `beat` and `worker` containers are running: `docker compose ps`.
2. Check the `beat` logs for schedule sync messages: `docker compose logs beat`.
3. Check the `worker` logs for task execution: `docker compose logs worker`.
4. Verify the job has **Enabled** toggled on in the UI.
5. Check that Redis is healthy: `docker compose exec redis redis-cli ping` should return `PONG`.

---

**Q: I changed a cron expression but the job still fires on the old schedule. Is there a delay?**

The `refresh_schedules` task runs every 60 seconds. Wait up to 60 seconds after saving a change for the new schedule to take effect. You can also manually trigger a refresh by restarting the `beat` container: `docker compose restart beat`.

---

**Q: Can I run a job more frequently than once per minute?**

No. Standard cron syntax has a 1-minute minimum granularity. For sub-minute intervals, you would need to implement a custom task loop — this is outside the scope of the current feature set.

---

## Notifications

**Q: Emails are going to spam. How do I fix this?**

1. Set up SPF and DKIM records for your sending domain.
2. Use a dedicated transactional email service (Mailgun, SendGrid, AWS SES) rather than your personal Gmail.
3. Configure the `From` address to match the sending domain (not a generic gmail.com address).
4. Avoid spam-trigger words in the subject (the current templates are conservative).

---

**Q: Can I send notifications to a Slack channel?**

Not directly — Slack is not a built-in channel type. You can work around this with a Telegram → Slack bridge, or by creating a Telegram channel pointing to a Slack-integrated Telegram bot. Native Slack support is on the roadmap.

---

## Cloud Sync

**Q: Can I sync to an S3-compatible storage (MinIO, Backblaze B2, etc.)?**

Not yet. S3 support is planned. Currently only Google Drive, Dropbox, and OneDrive are supported.

---

**Q: How large a file can be uploaded to Google Drive?**

Google Drive's API supports uploads up to 5 TB for service accounts. For most Odoo deployments, this is not a practical limit.

---

## Operations

**Q: How do I back up the orchestrator itself?**

Back up the `/data/` directory. It contains:

- `app.db` — the SQLite database (all configuration, job history, audit log)
- `secret.key` — the Fernet encryption key
- `backups/` — the backup archives themselves

A simple approach:

```bash
docker compose stop
tar czf odoo-backup-app-$(date +%Y%m%d).tar.gz /path/to/data/
docker compose start
```

Or use `VACUUM INTO` for a hot copy of the SQLite database without stopping services.

---

**Q: How do I upgrade to a new version?**

```bash
docker compose pull
docker compose up -d
```

Alembic migrations run automatically on startup. The database schema is upgraded before the application accepts requests.

---

**Q: I lost my admin password and didn't set up email recovery. Am I locked out?**

Yes — without password recovery configured, there is no automated way to reset the password. Recovery options:

1. **Direct database edit**: Stop the app, use `sqlite3 /data/app.db`, update the `password_hash` column in the `users` table with a new Argon2 hash. Restart.
2. **Admin CLI** (not yet implemented): A `manage.py reset-password` command is planned.

This is why the setup checklist prominently highlights configuring password recovery.

---

**Q: Can I run the application without Docker?**

Yes. Install the Python dependencies from `requirements.txt`, run Redis separately, and start the three processes manually:

```bash
uvicorn backend.app.main:app --port 8080
celery -A backend.app.tasks.celery_app worker -Q default,backups,notifications,cloud
celery -A backend.app.tasks.celery_app beat
```

Set the `OB_*` environment variables as needed. The frontend must be pre-built (`npm run build` in `frontend/`) or served by a separate dev server.

---

**Q: Is there a REST API I can call from other tools?**

Yes. The full API is available at `/api/`. It uses the same session cookie authentication as the browser. You can log in with a POST to `/api/auth/login` and then use the returned cookie in subsequent requests. API documentation (OpenAPI) is available at `/api/docs` when the app is running.
