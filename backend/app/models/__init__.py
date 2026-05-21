"""ORM model package — imports all models so Alembic can discover them."""

from app.models.audit import AuditLog
from app.models.backup import BackupRun
from app.models.cloud import CloudAccount, InstanceCloudBinding
from app.models.instance import Instance
from app.models.job import Job
from app.models.notify import InstanceNotificationBinding, SmtpChannel, TelegramChannel
from app.models.user import User

__all__ = [
    "AuditLog",
    "BackupRun",
    "CloudAccount",
    "Instance",
    "InstanceCloudBinding",
    "InstanceNotificationBinding",
    "Job",
    "SmtpChannel",
    "TelegramChannel",
    "User",
]
