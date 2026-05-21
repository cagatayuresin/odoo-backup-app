# Installation

## Requirements

- Docker Engine 24+ and Docker Compose v2
- 512 MB RAM minimum (1 GB recommended for workers)
- Persistent storage at `./data/` (created automatically on first start)

## One-Command Install

```bash
git clone https://github.com/cagatayuresin/odoo-backup-app.git
cd odoo-backup-app
docker compose up -d
```

Open **http://localhost:8080** and log in as `admin` / `admin`.

## Configuration

Create a `.env` file in the repo root to override defaults:

```dotenv
# Strong random values — generate with: openssl rand -hex 32
OB_SECRET_KEY=your-very-long-random-secret-here
OB_SESSION_SECRET=another-very-long-random-secret

# Expose on a different port
OB_PORT=8080

# Logging
OB_LOG_LEVEL=INFO
```

| Variable | Default | Description |
|---|---|---|
| `OB_DATA_DIR` | `/data` | Path inside the container for all persistent data |
| `OB_SECRET_KEY` | auto-generated | Seeds the Fernet encryption key for at-rest secrets |
| `OB_SESSION_SECRET` | auto-generated | HMAC key for signed session cookies |
| `REDIS_URL` | `redis://redis:6379/0` | Celery broker and result backend |
| `OB_LOG_LEVEL` | `INFO` | Python logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `OB_PORT` | `8080` | Host port to expose the web UI on |

!!! warning "Production secret keys"
    The auto-generated keys are new on every container restart if you do not set them explicitly. This means all active sessions are invalidated and all stored secrets become unreadable. **Always set `OB_SECRET_KEY` and `OB_SESSION_SECRET` explicitly in production.**

## Persistent Data Layout

```
./data/
├── db/
│   └── app.sqlite          # Application database
├── backups/
│   └── <instance-slug>/    # Backup files per instance
│       └── 20260521-020000_mydb.zip
├── logs/                   # Reserved for future log rotation
└── secret.key              # Fernet encryption key (auto-generated)
```

!!! danger "Back up `secret.key`"
    The `secret.key` file encrypts all stored secrets (database passwords, API tokens, etc.). If it is lost, those secrets cannot be recovered. Include it in your infrastructure backups.

## Behind a Reverse Proxy (HTTPS)

Place `nginx` or `traefik` in front of the app. The web service listens on port 8080. For HTTPS, set `https_only=True` in the session middleware by passing `OB_SESSION_SECRET` and ensuring your proxy terminates TLS.

Example nginx snippet:

```nginx
server {
    listen 443 ssl;
    server_name backup.mycompany.com;

    ssl_certificate     /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    location / {
        proxy_pass         http://localhost:8080;
        proxy_set_header   Host $host;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
}
```

## Upgrading

```bash
git pull
docker compose build --no-cache
docker compose up -d
```

Alembic migrations run automatically on startup.
