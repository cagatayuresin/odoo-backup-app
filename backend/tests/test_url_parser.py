"""Exhaustive tests for core/url_parser.py — covers all §6.1 input forms."""

from __future__ import annotations

import pytest

from app.core.url_parser import ParsedInstance, parse_instance_url


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # Bare hostname → https + 443
        ("mycompany.com", ParsedInstance("https", "mycompany.com", 443)),
        # http scheme explicit
        ("http://mycompany.com", ParsedInstance("http", "mycompany.com", 80)),
        # https scheme explicit
        ("https://mycompany.com", ParsedInstance("https", "mycompany.com", 443)),
        # https with non-standard port
        ("https://mycompany.com:8443", ParsedInstance("https", "mycompany.com", 8443)),
        # http with non-standard port
        ("http://mycompany.com:8069", ParsedInstance("http", "mycompany.com", 8069)),
        # Trailing slash stripped
        ("https://mycompany.com/", ParsedInstance("https", "mycompany.com", 443)),
        # Path stripped
        ("https://mycompany.com/web/login", ParsedInstance("https", "mycompany.com", 443)),
        # Raw IP (no port, no scheme) → https + 443
        ("192.168.1.10", ParsedInstance("https", "192.168.1.10", 443)),
        # Raw IP with non-443 port, no scheme → http
        ("192.168.1.10:8069", ParsedInstance("http", "192.168.1.10", 8069)),
        # Raw IP with explicit http scheme
        ("http://192.168.1.10:8069", ParsedInstance("http", "192.168.1.10", 8069)),
        # Raw IP with 443 port → https
        ("192.168.1.10:443", ParsedInstance("https", "192.168.1.10", 443)),
        # Subdomain
        ("erp.mycompany.com", ParsedInstance("https", "erp.mycompany.com", 443)),
        # Deep subdomain
        ("demo.erp.mycompany.com", ParsedInstance("https", "demo.erp.mycompany.com", 443)),
        # localhost with port
        ("http://localhost:8069", ParsedInstance("http", "localhost", 8069)),
        # Explicit port 80 on http
        ("http://mycompany.com:80", ParsedInstance("http", "mycompany.com", 80)),
        # Explicit port 443 on https
        ("https://mycompany.com:443", ParsedInstance("https", "mycompany.com", 443)),
    ],
)
def test_parse_instance_url(raw: str, expected: ParsedInstance) -> None:
    """Each raw URL should normalise to the expected ParsedInstance."""
    result = parse_instance_url(raw)
    assert result == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "not a url at all !!",
        "ftp://invalid-scheme.com",
        "://missing-host",
    ],
)
def test_parse_invalid_raises(raw: str) -> None:
    """Invalid inputs should raise ValueError."""
    with pytest.raises(ValueError):
        parse_instance_url(raw)


def test_base_url_no_default_port() -> None:
    """base_url should omit the port when it is the scheme default."""
    parsed = parse_instance_url("https://mycompany.com")
    assert parsed.base_url == "https://mycompany.com"


def test_base_url_non_default_port() -> None:
    """base_url should include the port when it is not the scheme default."""
    parsed = parse_instance_url("https://mycompany.com:8443")
    assert parsed.base_url == "https://mycompany.com:8443"


def test_base_url_http_non_default_port() -> None:
    """base_url http non-standard port is included."""
    parsed = parse_instance_url("http://192.168.1.10:8069")
    assert parsed.base_url == "http://192.168.1.10:8069"
