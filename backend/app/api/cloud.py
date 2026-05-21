"""Cloud account CRUD + per-instance cloud binding endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_password_changed
from app.core.security import encrypt_secret
from app.models.cloud import CloudAccount, InstanceCloudBinding
from app.models.instance import Instance
from app.models.user import User
from app.schemas.cloud import (
    CloudAccountCreate,
    CloudAccountRead,
    CloudAccountUpdate,
    CloudBindingCreate,
    CloudBindingRead,
    CloudBindingUpdate,
)

router = APIRouter(prefix="/cloud", tags=["cloud"])


# ─── Cloud Accounts ───────────────────────────────────────────────────────────


@router.get("/accounts", response_model=list[CloudAccountRead])
def list_accounts(
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> list[CloudAccount]:
    """List all cloud accounts."""
    return db.query(CloudAccount).all()


@router.post("/accounts", response_model=CloudAccountRead, status_code=status.HTTP_201_CREATED)
def create_account(
    body: CloudAccountCreate,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> CloudAccount:
    """Register a cloud account with encrypted credentials."""
    account = CloudAccount(
        provider=body.provider,
        name=body.name,
        credentials_enc=encrypt_secret(json.dumps(body.credentials)),
        enabled=body.enabled,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/accounts/{account_id}", response_model=CloudAccountRead)
def get_account(
    account_id: int,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> CloudAccount:
    """Return a single cloud account."""
    account = db.get(CloudAccount, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cloud account not found")
    return account


@router.patch("/accounts/{account_id}", response_model=CloudAccountRead)
def update_account(
    account_id: int,
    body: CloudAccountUpdate,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> CloudAccount:
    """Partially update a cloud account."""
    account = db.get(CloudAccount, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cloud account not found")

    update_data = body.model_dump(exclude_unset=True)
    if "credentials" in update_data:
        account.credentials_enc = encrypt_secret(json.dumps(update_data.pop("credentials")))
    for field, value in update_data.items():
        setattr(account, field, value)
    db.commit()
    db.refresh(account)
    return account


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: int,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> None:
    """Delete a cloud account."""
    account = db.get(CloudAccount, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cloud account not found")
    db.delete(account)
    db.commit()


# ─── Instance Cloud Bindings ──────────────────────────────────────────────────


@router.get("/instances/{instance_id}/bindings", response_model=list[CloudBindingRead])
def list_bindings(
    instance_id: int,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> list[InstanceCloudBinding]:
    """List cloud bindings for an instance."""
    inst = db.get(Instance, instance_id)
    if inst is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found")
    return (
        db.query(InstanceCloudBinding).filter(InstanceCloudBinding.instance_id == instance_id).all()
    )


@router.post(
    "/instances/{instance_id}/bindings",
    response_model=CloudBindingRead,
    status_code=status.HTTP_201_CREATED,
)
def create_binding(
    instance_id: int,
    body: CloudBindingCreate,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> InstanceCloudBinding:
    """Bind a cloud account to an instance."""
    inst = db.get(Instance, instance_id)
    if inst is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found")

    binding = InstanceCloudBinding(
        instance_id=instance_id,
        cloud_account_id=body.cloud_account_id,
        remote_folder=body.remote_folder,
        enabled=body.enabled,
        apply_retention_remotely=body.apply_retention_remotely,
    )
    db.add(binding)
    db.commit()
    db.refresh(binding)
    return binding


@router.patch("/instances/{instance_id}/bindings/{binding_id}", response_model=CloudBindingRead)
def update_binding(
    instance_id: int,
    binding_id: int,
    body: CloudBindingUpdate,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> InstanceCloudBinding:
    """Update a cloud binding."""
    binding = db.get(InstanceCloudBinding, binding_id)
    if binding is None or binding.instance_id != instance_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Binding not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(binding, field, value)
    db.commit()
    db.refresh(binding)
    return binding


@router.delete(
    "/instances/{instance_id}/bindings/{binding_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_binding(
    instance_id: int,
    binding_id: int,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> None:
    """Remove a cloud binding."""
    binding = db.get(InstanceCloudBinding, binding_id)
    if binding is None or binding.instance_id != instance_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Binding not found")
    db.delete(binding)
    db.commit()
