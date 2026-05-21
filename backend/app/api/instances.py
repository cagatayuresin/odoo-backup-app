"""Instance CRUD + test-connection endpoints."""

from __future__ import annotations

import json
import logging
import re

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_password_changed
from app.core.security import decrypt_secret, encrypt_secret
from app.core.url_parser import parse_instance_url
from app.models.instance import Instance
from app.models.user import User
from app.schemas.instance import InstanceCreate, InstanceRead, InstanceUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/instances", tags=["instances"])

_SLUG_RE = re.compile(r"[^a-z0-9-]")


def _slugify(name: str) -> str:
    """Convert *name* to a URL-safe slug."""
    slug = name.lower().strip()
    slug = _SLUG_RE.sub("-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:64] or "instance"


def _ensure_unique_slug(slug: str, db: Session, exclude_id: int | None = None) -> str:
    """Append a counter suffix until the slug is unique."""
    base = slug
    counter = 1
    while True:
        existing = db.query(Instance).filter(Instance.slug == slug).first()
        if existing is None or (exclude_id is not None and existing.id == exclude_id):
            return slug
        slug = f"{base}-{counter}"
        counter += 1


def _apply_instance_from_schema(inst: Instance, data: InstanceCreate | InstanceUpdate) -> None:
    """Write schema fields onto the ORM object (handles encryption)."""
    update = data.model_dump(exclude_unset=True)

    if "raw_url" in update and update["raw_url"]:
        parsed = parse_instance_url(update["raw_url"])
        inst.raw_url = update["raw_url"]
        inst.parsed_scheme = parsed.scheme
        inst.parsed_host = parsed.host
        inst.parsed_port = parsed.port

    scalar_fields = [
        "name", "backup_method", "db_host", "db_port", "db_user",
        "filestore_path", "db_selection_mode", "include_filestore",
        "retention_mode", "retention_value", "notifications_enabled",
    ]
    for field in scalar_fields:
        if field in update:
            setattr(inst, field, update[field])

    if "db_names" in update and update["db_names"] is not None:
        inst.db_names = json.dumps(update["db_names"])
    elif "db_names" in update:
        inst.db_names = None

    if "master_password" in update:
        if update["master_password"]:
            inst.master_password_enc = encrypt_secret(update["master_password"])
        else:
            inst.master_password_enc = None

    if "db_password" in update:
        if update["db_password"]:
            inst.db_password_enc = encrypt_secret(update["db_password"])
        else:
            inst.db_password_enc = None


@router.get("/", response_model=list[InstanceRead])
def list_instances(
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> list[Instance]:
    """Return all configured instances."""
    return db.query(Instance).order_by(Instance.name).all()


@router.post("/", response_model=InstanceRead, status_code=status.HTTP_201_CREATED)
def create_instance(
    body: InstanceCreate,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> Instance:
    """Create a new Odoo instance configuration."""
    try:
        parsed = parse_instance_url(body.raw_url)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    slug = _ensure_unique_slug(_slugify(body.name), db)
    inst = Instance(
        name=body.name,
        slug=slug,
        raw_url=body.raw_url,
        parsed_scheme=parsed.scheme,
        parsed_host=parsed.host,
        parsed_port=parsed.port,
    )
    _apply_instance_from_schema(inst, body)
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst


@router.get("/{instance_id}", response_model=InstanceRead)
def get_instance(
    instance_id: int,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> Instance:
    """Return a single instance by ID."""
    inst = db.get(Instance, instance_id)
    if inst is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found")
    return inst


@router.patch("/{instance_id}", response_model=InstanceRead)
def update_instance(
    instance_id: int,
    body: InstanceUpdate,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> Instance:
    """Partially update an instance configuration."""
    inst = db.get(Instance, instance_id)
    if inst is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found")

    _apply_instance_from_schema(inst, body)
    db.commit()
    db.refresh(inst)
    return inst


@router.delete("/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_instance(
    instance_id: int,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> None:
    """Delete an instance and all associated data."""
    inst = db.get(Instance, instance_id)
    if inst is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found")
    db.delete(inst)
    db.commit()


@router.post("/{instance_id}/test-connection")
def test_connection(
    instance_id: int,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Test connectivity to the instance's Odoo server.

    For odoo_endpoint instances: attempts to reach /web/database/list.
    For pg_dump instances: attempts a TCP connection to the DB host/port.
    """
    from app.models.instance import BackupMethod

    inst = db.get(Instance, instance_id)
    if inst is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found")

    if inst.backup_method == BackupMethod.odoo_endpoint:
        url = f"{inst.parsed_scheme}://{inst.parsed_host}:{inst.parsed_port}/web/database/list"
        try:
            with httpx.Client(timeout=10.0, verify=True) as client:
                resp = client.get(url)
            return {"status": "ok", "http_status": str(resp.status_code)}
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Cannot reach instance: {exc}",
            ) from exc
    else:
        import socket

        host = inst.db_host or "localhost"
        port = inst.db_port or 5432
        try:
            with socket.create_connection((host, port), timeout=5.0):
                pass
            return {"status": "ok", "detail": f"TCP connection to {host}:{port} succeeded"}
        except OSError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Cannot reach database: {exc}",
            ) from exc
