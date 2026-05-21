"""Per-instance notification binding CRUD."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_password_changed
from app.models.instance import Instance
from app.models.notify import InstanceNotificationBinding
from app.models.user import User
from app.schemas.notify import NotificationBindingCreate, NotificationBindingRead

router = APIRouter(
    prefix="/instances/{instance_id}/notification-bindings",
    tags=["notifications"],
)


def _get_instance_or_404(instance_id: int, db: Session) -> Instance:
    inst = db.get(Instance, instance_id)
    if inst is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found")
    return inst


@router.get("/", response_model=list[NotificationBindingRead])
def list_bindings(
    instance_id: int,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> list[InstanceNotificationBinding]:
    """List notification bindings for an instance."""
    _get_instance_or_404(instance_id, db)
    return (
        db.query(InstanceNotificationBinding)
        .filter(InstanceNotificationBinding.instance_id == instance_id)
        .all()
    )


@router.post("/", response_model=NotificationBindingRead, status_code=status.HTTP_201_CREATED)
def create_binding(
    instance_id: int,
    body: NotificationBindingCreate,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> InstanceNotificationBinding:
    """Add a notification channel binding to an instance."""
    _get_instance_or_404(instance_id, db)
    binding = InstanceNotificationBinding(
        instance_id=instance_id,
        channel_type=body.channel_type,
        channel_id=body.channel_id,
        on_success=body.on_success,
        on_failure=body.on_failure,
    )
    db.add(binding)
    db.commit()
    db.refresh(binding)
    return binding


@router.delete("/{binding_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_binding(
    instance_id: int,
    binding_id: int,
    _: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
) -> None:
    """Remove a notification binding."""
    binding = db.get(InstanceNotificationBinding, binding_id)
    if binding is None or binding.instance_id != instance_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Binding not found")
    db.delete(binding)
    db.commit()
