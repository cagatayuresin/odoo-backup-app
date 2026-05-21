"""Tests for core/security.py."""

from __future__ import annotations

import pytest

from app.core.security import (
    decrypt_secret,
    encrypt_secret,
    generate_reset_token,
    hash_password,
    hash_token,
    needs_rehash,
    verify_password,
)


def test_password_hash_and_verify() -> None:
    """Hashing then verifying the same password should succeed."""
    hashed = hash_password("correct-horse-battery-staple")
    assert verify_password("correct-horse-battery-staple", hashed)


def test_wrong_password_fails() -> None:
    """Verifying a different password should return False."""
    hashed = hash_password("secret123")
    assert not verify_password("wrong", hashed)


def test_needs_rehash_fresh_hash() -> None:
    """A freshly generated hash should not need rehashing."""
    hashed = hash_password("test")
    assert not needs_rehash(hashed)


def test_encrypt_decrypt_roundtrip() -> None:
    """Encrypting and then decrypting should recover the original plaintext."""
    plaintext = "super-secret-api-key"
    token = encrypt_secret(plaintext)
    assert decrypt_secret(token) == plaintext


def test_decrypt_invalid_token_raises() -> None:
    """Decrypting garbage should raise ValueError."""
    with pytest.raises(ValueError):
        decrypt_secret("not-a-valid-fernet-token")


def test_generate_reset_token_returns_pair() -> None:
    """generate_reset_token returns a (token, hash) tuple."""
    token, token_hash = generate_reset_token()
    assert len(token) > 20
    assert len(token_hash) == 64  # SHA-256 hex


def test_hash_token_deterministic() -> None:
    """hash_token should produce the same output for the same input."""
    assert hash_token("abc") == hash_token("abc")


def test_hash_token_different_inputs() -> None:
    """Different inputs should produce different hashes."""
    assert hash_token("abc") != hash_token("def")
