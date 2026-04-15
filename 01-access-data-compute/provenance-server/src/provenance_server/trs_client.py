"""TRS / Dockstore workflow resolver with a simple in-memory cache."""

from __future__ import annotations

import logging
import urllib.parse
from typing import Any
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

# Simple in-process cache: trs_uri -> metadata dict
_cache: dict[str, dict[str, Any]] = {}

# Allowlist of trusted TRS registry hosts.  Only URIs whose host matches one
# of these entries will trigger an outbound HTTP request, preventing SSRF.
TRUSTED_TRS_HOSTS: frozenset[str] = frozenset(
    {
        "dockstore.org",
        "workflowhub.eu",
        "bio.tools",
    }
)


def _trs_uri_to_http(trs_uri: str) -> str | None:
    """Convert a trs:// URI to an HTTP TRS API URL.

    trs://dockstore.org/workflow/github.com/org/repo  ->
    https://dockstore.org/api/ga4gh/trs/v2/tools/%23workflow%2Fgithub.com%2Forg%2Frepo

    Returns None if the URI scheme is not ``trs`` or the host is not in
    ``TRUSTED_TRS_HOSTS``.
    """
    parsed = urlparse(trs_uri)
    if parsed.scheme != "trs":
        return None
    host = parsed.netloc.lower()
    if host not in TRUSTED_TRS_HOSTS:
        logger.warning(
            "TRS host %r is not in the trusted allowlist (%s) — skipping resolution",
            host,
            ", ".join(sorted(TRUSTED_TRS_HOSTS)),
        )
        return None
    # path is like /workflow/github.com/org/repo  -> strip leading /
    raw_path = parsed.path.lstrip("/")
    # The TRS v2 tool ID for Dockstore workflows uses #workflow/ prefix
    tool_id = f"#workflow/{'/'.join(raw_path.split('/')[1:])}"
    encoded_id = urllib.parse.quote(tool_id, safe="")
    return f"https://{host}/api/ga4gh/trs/v2/tools/{encoded_id}"


async def resolve_workflow(trs_uri: str, timeout: float = 10.0) -> dict[str, Any] | None:
    """Fetch workflow metadata from a TRS registry.

    Returns a metadata dict on success, or None if unreachable / not found.
    Results are cached for the lifetime of the process.
    Only resolves URIs whose host is in ``TRUSTED_TRS_HOSTS``.
    """
    if trs_uri in _cache:
        return _cache[trs_uri]

    url = _trs_uri_to_http(trs_uri)
    if url is None:
        logger.debug("Cannot convert %s to HTTP TRS URL — skipping resolution", trs_uri)
        return None

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, headers={"Accept": "application/json"})
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            _cache[trs_uri] = data
            logger.info("Resolved TRS workflow %s", trs_uri)
            return data
    except httpx.HTTPError as exc:
        logger.warning("TRS resolution failed for %s: %s", trs_uri, exc)
        return None


def extract_workflow_metadata(trs_data: dict[str, Any]) -> dict[str, Any]:
    """Normalise a raw TRS /tools/{id} response into our internal schema."""
    return {
        "name": trs_data.get("name") or trs_data.get("toolname"),
        "description": trs_data.get("description"),
        "descriptor_type": (
            trs_data.get("toolclass", {}).get("name")
            if isinstance(trs_data.get("toolclass"), dict)
            else None
        ),
        "extra_metadata": {
            "organization": trs_data.get("organization"),
            "meta_version": trs_data.get("meta_version"),
            "aliases": trs_data.get("aliases", []),
        },
    }


def clear_cache() -> None:
    """Clear the in-memory TRS cache (useful for testing)."""
    _cache.clear()
