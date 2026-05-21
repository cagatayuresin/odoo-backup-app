"""Application configuration loaded from environment variables via pydantic-settings."""

from __future__ import annotations

import logging
import secrets
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime settings, resolved from environment variables with sensible defaults."""

    model_config = SettingsConfigDict(
        env_prefix="OB_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Paths
    data_dir: Path = Path("/data")

    # Security — auto-generate if not provided, but log a warning
    secret_key: str = secrets.token_hex(32)
    session_secret: str = secrets.token_hex(32)

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Logging
    log_level: str = "INFO"

    # Role hint (web | worker | beat) — informational only
    role: str = "web"

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure the log level is a valid Python logging level name."""
        upper = v.upper()
        if upper not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            msg = f"Invalid log level: {v}"
            raise ValueError(msg)
        return upper

    @property
    def db_dir(self) -> Path:
        """Directory containing the SQLite database file."""
        return self.data_dir / "db"

    @property
    def db_url(self) -> str:
        """SQLAlchemy database URL."""
        return f"sqlite:///{self.db_dir / 'app.sqlite'}"

    @property
    def backups_dir(self) -> Path:
        """Root directory for all backup files."""
        return self.data_dir / "backups"

    @property
    def logs_dir(self) -> Path:
        """Application log directory."""
        return self.data_dir / "logs"

    @property
    def secret_key_path(self) -> Path:
        """Path to the persistent Fernet key file."""
        return self.data_dir / "secret.key"


settings = Settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
