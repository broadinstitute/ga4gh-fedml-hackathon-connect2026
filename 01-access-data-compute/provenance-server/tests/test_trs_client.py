"""Tests for the TRS client."""

from __future__ import annotations

import pytest
import httpx

from provenance_server import trs_client


def test_trs_uri_to_http():
    uri = "trs://dockstore.org/workflow/github.com/broadinstitute/gatk-workflows/broad-prod-wgs"
    url = trs_client._trs_uri_to_http(uri)
    assert url is not None
    assert url.startswith("https://dockstore.org/api/ga4gh/trs/v2/tools/")
    assert "%23workflow" in url  # # is percent-encoded in the URL path


def test_trs_uri_untrusted_host():
    # Hosts not in the allowlist must not be resolved (SSRF prevention)
    assert trs_client._trs_uri_to_http("trs://evil.example.com/workflow/github.com/x/y") is None


def test_trs_uri_non_trs_scheme():
    assert trs_client._trs_uri_to_http("https://dockstore.org/workflow/foo") is None


def test_extract_workflow_metadata():
    raw = {
        "name": "GATK Best Practices",
        "description": "Germline SNP pipeline",
        "toolclass": {"name": "Workflow", "id": "workflow", "description": ""},
        "organization": "Broad Institute",
        "meta_version": "1",
        "aliases": ["gatk"],
    }
    meta = trs_client.extract_workflow_metadata(raw)
    assert meta["name"] == "GATK Best Practices"
    assert meta["description"] == "Germline SNP pipeline"
    assert meta["extra_metadata"]["organization"] == "Broad Institute"


@pytest.mark.asyncio
async def test_resolve_workflow_unreachable():
    """When the TRS host is unreachable the resolver should return None gracefully."""
    trs_client.clear_cache()
    result = await trs_client.resolve_workflow(
        "trs://nonexistent.example.invalid/workflow/github.com/test/wf",
        timeout=1.0,
    )
    assert result is None


@pytest.mark.asyncio
async def test_resolve_workflow_cached(monkeypatch):
    """Second call should return cached value without making a network request."""
    trs_client.clear_cache()
    fake_data = {"name": "cached-wf", "description": "demo"}
    trs_client._cache["trs://dockstore.org/workflow/github.com/cached/wf"] = fake_data

    result = await trs_client.resolve_workflow(
        "trs://dockstore.org/workflow/github.com/cached/wf"
    )
    assert result == fake_data
