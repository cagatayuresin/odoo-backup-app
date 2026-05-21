"""Security utilities: Argon2 password hashing, Fernet encryption, session helpers."""

from __future__ import annotations

import base64
import logging
import os
import secrets
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

logger = logging.getLogger(__name__)

# Argon2id hasher — OWASP-recommended parameters
_ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MiB
    parallelism=1,
    hash_len=32,
    salt_len=16,
)


def hash_password(plain: str) -> str:
    """Return an Argon2id hash of *plain*."""
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*, False otherwise."""
    try:
        return _ph.verify(hashed, plain)
    except VerifyMismatchError:
        return False


def needs_rehash(hashed: str) -> bool:
    """Return True if *hashed* was created with outdated Argon2 parameters."""
    return _ph.check_needs_rehash(hashed)


# ---------------------------------------------------------------------------
# Fernet symmetric encryption for at-rest secrets
# ---------------------------------------------------------------------------

_fernet: Fernet | None = None


def _load_or_create_fernet_key(path: Path, app_secret: str) -> Fernet:
    """Load the Fernet key from *path*, generating and persisting it if absent."""
    if path.exists():
        key_bytes = path.read_bytes().strip()
        return Fernet(key_bytes)

    # Derive a key from the configured secret (fall back to random if secret is default)
    if app_secret and app_secret != "change-me-in-production-32chars!!":
        seed = app_secret.encode()[:32].ljust(32, b"\x00")
        key_bytes = base64.urlsafe_b64encode(seed)
    else:
        key_bytes = Fernet.generate_key()

    path.parent.mkdir(parents=True, exist_ok=True)
    # Write with restricted permissions (owner read-only)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(path, flags, 0o600)
    try:
        os.write(fd, key_bytes + b"\n")
    finally:
        os.close(fd)

    logger.info("Generated new Fernet key at %s", path)
    return Fernet(key_bytes)


def get_fernet() -> Fernet:
    """Return the application-wide Fernet instance (lazy initialisation)."""
    global _fernet  # noqa: PLW0603
    if _fernet is None:
        _fernet = _load_or_create_fernet_key(settings.secret_key_path, settings.secret_key)
    return _fernet


def encrypt_secret(plain: str) -> str:
    """Fernet-encrypt *plain* and return a URL-safe base64 token."""
    return get_fernet().encrypt(plain.encode()).decode()


def decrypt_secret(token: str) -> str:
    """Fernet-decrypt *token* and return the original plaintext."""
    try:
        return get_fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        msg = "Failed to decrypt secret — key may have changed"
        raise ValueError(msg) from exc


def generate_reset_token() -> tuple[str, str]:
    """Generate a one-time reset token.

    Returns:
        (plaintext_token, sha256_hex_hash) — store only the hash in the DB.
    """
    import hashlib

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return token, token_hash


def hash_token(token: str) -> str:
    """Return the SHA-256 hex digest of *token*."""
    import hashlib

    return hashlib.sha256(token.encode()).hexdigest()
