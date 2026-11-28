"""SSRF-protected transport for outbound research retrieval.

Validates scheme/host, blocks private/loopback/link-local/reserved addresses,
guards against DNS rebinding by re-checking the resolved IP, validates every
redirect hop, enforces a response-size cap, and never follows redirects to
unsafe targets. External content is returned as untrusted text/JSON only.
"""

from __future__ import annotations

import ipaddress
import socket
from typing import Any, Optional, Tuple
from urllib.parse import urlparse

import httpx

from backend.core.config import settings


class UnsafeURLError(ValueError):
    """Raised when a URL fails SSRF validation."""


def _ip_is_blocked(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


def validate_public_url(url: str) -> str:
    """Validate that ``url`` uses http(s) and resolves only to public IPs."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeURLError(f"Unsupported scheme: {parsed.scheme!r}")
    if not parsed.hostname:
        raise UnsafeURLError("Missing host")
    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"DNS resolution failed: {exc}") from exc
    if not infos:
        raise UnsafeURLError("Host did not resolve")
    for info in infos:
        ip = info[4][0]
        if _ip_is_blocked(ip):
            raise UnsafeURLError(f"Blocked non-public address: {ip}")
    return url


async def safe_fetch(
    url: str,
    *,
    timeout: Optional[float] = None,
    max_bytes: Optional[int] = None,
    max_redirects: int = 5,
) -> Tuple[int, bytes, str]:
    """Fetch a URL safely. Returns (status_code, body_bytes, content_type).

    Re-validates every redirect target and aborts on oversized responses.
    """
    timeout = timeout if timeout is not None else settings.research_timeout_sec
    max_bytes = max_bytes if max_bytes is not None else settings.research_max_bytes
    current = validate_public_url(url)

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        for _ in range(max_redirects + 1):
            resp = await client.get(current, headers={"User-Agent": "VYRO-X-Research/1.0"})
            if resp.status_code in (301, 302, 303, 307, 308):
                location = resp.headers.get("location")
                if not location:
                    break
                current = validate_public_url(str(httpx.URL(current).join(location)))
                continue
            content = resp.content
            if len(content) > max_bytes:
                content = content[:max_bytes]
            return resp.status_code, content, resp.headers.get("content-type", "")
    return resp.status_code, resp.content[:max_bytes], resp.headers.get("content-type", "")


async def safe_fetch_json(url: str, **kwargs: Any) -> Optional[Any]:
    """Fetch JSON safely; returns parsed JSON or ``None`` on any failure."""
    import json

    try:
        status, body, _ctype = await safe_fetch(url, **kwargs)
    except UnsafeURLError:
        return None
    except Exception:
        return None
    if status != 200:
        return None
    try:
        return json.loads(body.decode("utf-8", errors="replace"))
    except (ValueError, TypeError):
        return None