"""URL normalisation for Odoo instance addresses.

Accepts any of:
  mycompany.com
  http://mycompany.com
  https://mycompany.com:8443
  192.168.1.10
  192.168.1.10:8069
  http://192.168.1.10:8069

Normalisation rules (per spec §6.1):
  - Missing scheme: https for hostnames, http for raw IPs with non-443 port,
    https for bare IPs without a port (assumes reverse proxy).
  - Missing port: 443 for https, 80 for http.
  - Path / query / fragment stripped.
  - Rejects anything that doesn't resolve to a valid host:port after parsing.
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class ParsedInstance:
    """The normalised, validated components of an Odoo instance URL."""

    scheme: str
    host: str
    port: int

    @property
    def base_url(self) -> str:
        """Reconstruct the canonical base URL (no trailing slash)."""
        if (self.scheme == "https" and self.port == 443) or (
            self.scheme == "http" and self.port == 80
        ):
            return f"{self.scheme}://{self.host}"
        return f"{self.scheme}://{self.host}:{self.port}"


# Characters allowed in a hostname label
_HOSTNAME_RE = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$"
)


def _is_ip(host: str) -> bool:
    """Return True if *host* is a valid IPv4 or IPv6 address."""
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _is_valid_host(host: str) -> bool:
    """Return True if *host* is a valid hostname or IP address."""
    if not host:
        return False
    if _is_ip(host):
        return True
    return bool(_HOSTNAME_RE.match(host))


def parse_instance_url(raw: str) -> ParsedInstance:
    """Parse and normalise *raw* into a :class:`ParsedInstance`.

    Args:
        raw: User-supplied URL string (with or without scheme / port / path).

    Returns:
        A :class:`ParsedInstance` with normalised scheme, host, and port.

    Raises:
        ValueError: If *raw* cannot be resolved to a valid host:port pair.
    """
    raw = raw.strip().rstrip("/")

    # Inject a scheme so urllib can parse the netloc
    raw_with_scheme = raw if "://" in raw else "placeholder://" + raw

    parsed = urlparse(raw_with_scheme)
    host = parsed.hostname or ""
    explicit_port: int | None = parsed.port
    explicit_scheme: str | None = parsed.scheme if "://" in (raw if "://" in raw else "") else None

    if not _is_valid_host(host):
        msg = f"Cannot parse a valid host from: {raw!r}"
        raise ValueError(msg)

    # Reject any scheme that is not http or https
    if explicit_scheme is not None and explicit_scheme not in {"http", "https"}:
        msg = f"Unsupported URL scheme {explicit_scheme!r} — only http and https are accepted"
        raise ValueError(msg)

    # Determine scheme
    if explicit_scheme in {"http", "https"}:
        scheme = explicit_scheme
    elif _is_ip(host):
        # Raw IP: use http if a non-443 explicit port given, otherwise https
        scheme = "http" if explicit_port is not None and explicit_port != 443 else "https"
    else:
        # Hostname without scheme → assume https (reverse proxy)
        scheme = "https"

    # Determine port
    if explicit_port is not None:
        port = explicit_port
    elif scheme == "https":
        port = 443
    else:
        port = 80

    if not (1 <= port <= 65535):
        msg = f"Port {port} is out of valid range (1-65535)"
        raise ValueError(msg)

    return ParsedInstance(scheme=scheme, host=host, port=port)
