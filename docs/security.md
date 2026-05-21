# Security

## Threat Model

The orchestrator is a self-hosted, single-tenant application. It runs inside your infrastructure, not as a SaaS. The primary threats it defends against are:

- **Credential theft** — if an attacker gains read access to the database file, they should not be able to recover secrets in plaintext.
- **Session hijacking** — stolen session cookies should not be replayable indefinitely.
- **Password brute-force** — the password hashing scheme must be slow enough to make offline cracking infeasible.
- **SSRF / path traversal** — user-supplied URLs and file paths must be validated to prevent server-side request forgery or directory escapes.

The orchestrator does **not** attempt to defend against:
- An attacker with root access to the host (they can read `/data/secret.key` directly).
- Bugs in underlying OS, Python runtime, or the databases being backed up.

## Authentication

### Session Cookies

Sessions use **Starlette SessionMiddleware** backed by `itsdangerous` signed cookies:

- The signing key is derived from `OB_SECRET_KEY` (randomly generated on first boot, stored in `/data/secret.key`).
- Sessions expire after **12 hours** of inactivity (sliding window).
- `SameSite=Lax` and `HttpOnly` flags are set; set `OB_SESSION_COOKIE_SECURE=true` (default in production mode) to also add `Secure`.

### Password Hashing

Passwords are hashed with **Argon2id** using OWASP-recommended parameters:

| Parameter | Value |
|-----------|-------|
| `time_cost` | 3 |
| `memory_cost` | 65536 KiB (64 MiB) |
| `parallelism` | 2 |
| Hash length | 32 bytes |

These parameters make offline brute-force attacks against a leaked database computationally expensive (tens of milliseconds per attempt on modern hardware).

### First-Login Password Change

The default `admin`/`admin` credentials are flagged with `must_change_password=True`. Every API endpoint (except auth routes) returns **403 Forbidden** while this flag is set. The frontend router enforces a redirect to the Change Password page. The flag is cleared once the password is successfully updated.

### Password Reset

Password reset tokens are generated as:

1. A 32-byte cryptographically random value (plaintext) — sent in the email link.
2. A SHA-256 hash of the plaintext — stored in the database.

When a reset link is visited, the token is hashed and compared against the stored hash. This means a compromise of the database alone does not yield usable reset tokens.

Tokens expire after **1 hour**. The `/auth/request-reset` endpoint always returns `200 OK` regardless of whether the email is registered, to prevent user enumeration.

## Encryption at Rest

All credentials stored in the database are encrypted with **Fernet** symmetric encryption (AES-128-CBC + HMAC-SHA256):

- SMTP passwords
- Telegram bot tokens
- Cloud account credentials (service account JSON, API tokens, client secrets)
- Odoo master passwords
- PostgreSQL passwords

The encryption key is generated on first boot and written to `/data/secret.key`. This file must be:

- **Backed up independently** from the database. Losing the key means all stored credentials are unrecoverable.
- **Kept secret**. Anyone who has both the database file and the key file has full access to all credentials.
- **Not committed to version control**. The `.gitignore` excludes the `data/` directory.

### Key Rotation

Key rotation is not yet automated. To rotate manually:

1. Stop all services.
2. Write a migration script that decrypts each `*_enc` column with the old key and re-encrypts with the new key.
3. Replace `/data/secret.key`.
4. Restart services.

## Audit Log

Every significant action is recorded in the `audit_log` table:

| Event type | Examples |
|------------|---------|
| `auth` | Login, logout, password change, reset |
| `instance` | Create, update, delete |
| `job` | Create, update, delete, enable/disable |
| `backup` | Run started, completed, failed, manually deleted |
| `retention` | Files deleted, safety net triggered |
| `cloud` | Upload completed, upload failed |
| `settings` | Timezone, SMTP config changed |

Audit log entries include the timestamp, user ID, action, target entity ID, and a JSON payload with relevant details. Entries are **append-only** — the application has no endpoint to delete audit log records.

## Input Validation

### URL Parsing

Instance URLs are parsed and normalized server-side:

- Raw IP with non-443 port → `http://` scheme
- Hostname without scheme → `https://`
- Paths and query strings are stripped
- Non-ASCII hostnames are rejected

### Path Traversal

All user-supplied file names (backup file paths) are validated against path traversal sequences (`../`, absolute paths). The backup directory is resolved to an absolute path before any file operations.

### SQL Injection

All database queries use SQLAlchemy ORM or parameterized Core queries. String concatenation into SQL is never used.

## Forbidden Patterns

The codebase enforces the following constraints via static analysis (Ruff `S` rules + Bandit):

| Pattern | Reason |
|---------|--------|
| `pickle.load` | Arbitrary code execution on deserialization |
| `yaml.load` without SafeLoader | Arbitrary code execution |
| `eval` / `exec` | Arbitrary code execution |
| `subprocess.*(shell=True)` | Shell injection via user-controlled input |
| `verify=False` in HTTP clients | Disables TLS certificate validation |
| `tempfile.mktemp` | Race condition (TOCTOU); use `NamedTemporaryFile` |
| MD5/SHA1 for security | Collision-vulnerable; use SHA-256+ |
| Hardcoded secrets | Rotate secrets via env vars, not source changes |
| HTTP timeout omitted | Allows indefinite hang on network calls |

## Dependency Security

- **pip-audit** scans `requirements.txt` for known CVEs on every CI run.
- **Trivy** scans the Docker image for OS-level vulnerabilities.
- Dependencies are pinned via `pip-tools` (`requirements.txt` is compiled from `requirements.in`).

Run a manual audit:

```bash
make audit          # pip-audit only
make docker-check   # Hadolint (Dockerfile lint) + Trivy
```

## Network Exposure

The application listens on port **8080** inside the container (or whatever `OB_PORT` is set to). It is not intended to be exposed directly to the Internet. Use a reverse proxy (nginx, Caddy, Traefik) that:

- Terminates TLS with a valid certificate
- Sets `X-Forwarded-For` and `X-Forwarded-Proto` headers
- Enforces HTTPS-only access

Example nginx snippet is in the [Installation guide](installation.md#reverse-proxy-nginx).

When running behind a proxy, set `OB_TRUSTED_PROXIES=1` (or the proxy's IP) so that the session cookie's `Secure` flag is set correctly and IP logging uses the forwarded address.
