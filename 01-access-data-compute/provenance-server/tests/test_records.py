"""Tests for provenance record endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_get_record(client: AsyncClient):
    # First register the workflow
    wf_resp = await client.post(
        "/provenance/workflows",
        json={
            "id": "trs://dockstore.org/workflow/github.com/test/wf",
            "name": "Test Workflow",
            "version": "1.0.0",
        },
    )
    assert wf_resp.status_code == 201

    # Create a record
    resp = await client.post(
        "/provenance/records",
        json={
            "data_element_id": "drs://drs.example.org/file001",
            "workflow_id": "trs://dockstore.org/workflow/github.com/test/wf",
            "workflow_version": "1.0.0",
            "execution_id": "wes-run-abc123",
            "site": "site-a",
            "parameters": {"ref": "hg38"},
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    record_id = body["response"]["id"]
    assert body["response"]["data_element_id"] == "drs://drs.example.org/file001"
    assert body["meta"]["beacon_id"] == "test-node"

    # Fetch the record
    get_resp = await client.get(f"/provenance/records/{record_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["response"]["id"] == record_id


@pytest.mark.asyncio
async def test_get_record_not_found(client: AsyncClient):
    resp = await client.get("/provenance/records/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_records(client: AsyncClient):
    # Register workflow + two records
    await client.post(
        "/provenance/workflows",
        json={"id": "trs://dockstore.org/workflow/github.com/test/wf2", "name": "WF2"},
    )
    for i in range(3):
        await client.post(
            "/provenance/records",
            json={
                "data_element_id": f"drs://drs.example.org/file{i:03d}",
                "workflow_id": "trs://dockstore.org/workflow/github.com/test/wf2",
            },
        )
    resp = await client.get("/provenance/records")
    assert resp.status_code == 200
    assert len(resp.json()["response"]) == 3


@pytest.mark.asyncio
async def test_delete_record(client: AsyncClient):
    await client.post(
        "/provenance/workflows",
        json={"id": "trs://dockstore.org/workflow/github.com/test/wf3"},
    )
    create_resp = await client.post(
        "/provenance/records",
        json={
            "data_element_id": "drs://drs.example.org/todelete",
            "workflow_id": "trs://dockstore.org/workflow/github.com/test/wf3",
        },
    )
    record_id = create_resp.json()["response"]["id"]

    del_resp = await client.delete(f"/provenance/records/{record_id}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/provenance/records/{record_id}")
    assert get_resp.status_code == 404
