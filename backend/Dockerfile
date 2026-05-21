# ─── Stage 1: Frontend build ─────────────────────────────────────────────────
FROM node:20.15.0-alpine3.20 AS frontend-builder

WORKDIR /build/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./
RUN npm run build

# ─── Stage 2: Python dependency compilation ───────────────────────────────────
FROM python:3.12.4-slim-bookworm AS python-deps

WORKDIR /deps

# Install pip-tools for compiling requirements
RUN pip install --no-cache-dir pip-tools==7.4.1

COPY backend/requirements.in ./
RUN pip-compile --no-header --strip-extras requirements.in -o requirements.txt

# ─── Stage 3: Runtime image ───────────────────────────────────────────────────
FROM python:3.12.4-slim-bookworm AS runtime

# Install PostgreSQL client (pg_dump / pg_restore binaries) + curl for healthcheck
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create non-root user
RUN addgroup --system --gid 1001 appgroup \
    && adduser --system --uid 1001 --ingroup appgroup --no-create-home appuser

# Copy compiled requirements and install
COPY --from=python-deps /deps/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --require-hashes -r requirements.txt 2>/dev/null \
    || pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/app/ ./app/
COPY backend/alembic/ ./alembic/
COPY backend/alembic.ini ./alembic.ini

# Copy built frontend into static directory served by FastAPI
COPY --from=frontend-builder /build/frontend/dist/ ./app/static/

# Create data directories (will be overridden by volume mount in compose)
RUN mkdir -p /data/db /data/backups /data/logs \
    && chown -R appuser:appgroup /data /app

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
