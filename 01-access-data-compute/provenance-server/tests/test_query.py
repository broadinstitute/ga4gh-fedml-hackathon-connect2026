"""Tests for the provenance query endpoint."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _seed(client: AsyncClient):
    """Register two workflows and four records across two sites."""
    for wf_id, name in [
        ("trs://dockstore.org/workflow/github.com/broad/gatk", "GATK"),
        ("trs://dockstore.org/workflow/github.com/encode/atac", "ATAC"),
    ]:
        await client.post("/provenance/workflows", json={"id": wf_id, "name": name})

    records = [
        {
            "data_element_id": "drs://drs.example.org/a1",
            "workflow_id": "trs://dockstore.org/workflow/github.com/broad/gatk",
            "workflow_version": "4.3.0",
            "site": "site-a",
        },
        {
            "data_element_id": "drs://drs.example.org/a2",
            "workflow_id": "trs://dockstore.org/workflow/github.com/broad/gatk",
            "workflow_version": "4.3.0",
            "site": "site-a",
            "parameters": {"ref": "hg38"},
        },
        {
            "data_element_id": "drs://drs.example.org/b1",
            "workflow_id": "trs://dockstore.org/workflow/github.com/broad/gatk",
            "workflow_version": "4.2.0",
            "site": "site-b",
        },
        {
            "data_element_id": "drs://drs.example.org/atac1",
            "workflow_id": "trs://dockstore.org/workflow/github.com/encode/atac",
            "workflow_version": "2.0.0",
            "site": "site-a",
        },
    ]
    for r in records:
        await client.post("/provenance/records", json=r)


@pytest.mark.asyncio
async def test_query_by_workflow_id(client: AsyncClient):
    await _seed(client)
    resp = await client.post(
        "/provenance/query",
        json={"workflow_id": "trs://dockstore.org/workflow/github.com/broad/gatk"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["response"]["numTotalResults"] == 3


@pytest.mark.asyncio
async def test_query_by_workflow_version(client: AsyncClient):
    await _seed(client)
    resp = await client.post(
        "/provenance/query",
        json={
            "workflow_id": "trs://dockstore.org/workflow/github.com/broad/gatk",
            "workflow_version": "4.3.0",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["response"]["numTotalResults"] == 2


@pytest.mark.asyncio
async def test_query_by_site(client: AsyncClient):
    await _seed(client)
    resp = await client.post("/provenance/query", json={"site": "site-b"})
    assert resp.status_code == 200
    assert resp.json()["response"]["numTotalResults"] == 1


@pytest.mark.asyncio
async def test_query_parameters_hidden_by_default(client: AsyncClient):
    await _seed(client)
    resp = await client.post(
        "/provenance/query",
        json={"workflow_id": "trs://dockstore.org/workflow/github.com/broad/gatk"},
    )
    results = resp.json()["response"]["results"]
    for r in results:
        assert r["parameters"] is None


@pytest.mark.asyncio
async def test_query_parameters_included_when_requested(client: AsyncClient):
    await _seed(client)
    resp = await client.post(
        "/provenance/query",
        json={
            "workflow_id": "trs://dockstore.org/workflow/github.com/broad/gatk",
            "workflow_version": "4.3.0",
            "include_parameters": True,
        },
    )
    results = resp.json()["response"]["results"]
    params = [r["parameters"] for r in results]
    assert {"ref": "hg38"} in params


@pytest.mark.asyncio
async def test_query_export_returns_zip(client: AsyncClient):
    await _seed(client)
    resp = await client.post(
        "/provenance/query/export",
        json={"workflow_id": "trs://dockstore.org/workflow/github.com/broad/gatk"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    # Verify it's a valid ZIP file
    import io
    import zipfile

    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    assert "ro-crate-metadata.json" in zf.namelist()
