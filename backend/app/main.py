"""FastAPI application entry point."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.core.startup import run_startup

logger = logging.getLogger(__name__)

# ─── Application factory ──────────────────────────────────────────────────────


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    run_startup()

    application = FastAPI(
        title="Odoo Backup Orchestrator",
        description="Self-hosted backup orchestration for one or many Odoo instances.",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # Session middleware — signed cookies with 12h expiry, sliding
    application.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        max_age=43200,  # 12 hours
        same_site="lax",
        https_only=False,  # set True behind TLS in production
    )

    _register_routers(application)
    _mount_static(application)

    return application


def _register_routers(application: FastAPI) -> None:
    """Attach all API routers under the /api prefix."""
    from app.api.account import router as account_router
    from app.api.auth import router as auth_router
    from app.api.backups import router as backups_router
    from app.api.channels import router as channels_router
    from app.api.cloud import router as cloud_router
    from app.api.instances import router as instances_router
    from app.api.jobs import router as jobs_router
    from app.api.notify_bindings import router as notify_bindings_router
    from app.api.settings import router as settings_router

    for router in (
        auth_router,
        account_router,
        instances_router,
        jobs_router,
        backups_router,
        channels_router,
        notify_bindings_router,
        cloud_router,
        settings_router,
    ):
        application.include_router(router, prefix="/api")

    # Health check — no auth required
    @application.get("/api/health", tags=["system"])
    def health() -> dict[str, str]:
        """Liveness probe for Docker healthcheck and load balancers."""
        return {"status": "ok"}


def _mount_static(application: FastAPI) -> None:
    """Serve the built Vue SPA from /app/app/static, falling back to index.html for SPA routing."""
    static_dir = Path(__file__).parent / "static"

    if static_dir.exists():
        # Mount Vite's /assets directory at /assets so JS/CSS paths in index.html resolve correctly
        assets_dir = static_dir / "assets"
        if assets_dir.exists():
            application.mount(
                "/assets",
                StaticFiles(directory=str(assets_dir)),
                name="assets",
            )

        # Serve favicon and any other top-level static files
        application.mount(
            "/static",
            StaticFiles(directory=str(static_dir)),
            name="static",
        )

    # Catch-all: serve index.html for all non-API routes so Vue Router can handle them
    @application.get("/{full_path:path}", response_class=HTMLResponse, include_in_schema=False)
    def spa_fallback(request: Request, full_path: str) -> HTMLResponse:
        """Serve the SPA shell for any non-API, non-asset route."""
        index_path = static_dir / "index.html"
        if index_path.is_file():
            return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
        return HTMLResponse(content="<h1>App not built yet</h1>", status_code=503)


app = create_app()
