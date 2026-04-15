"""Tests for the service-info and workflow endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_service_info(client: AsyncClient):
    resp = await client.get("/provenance/info")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "test-node"
    assert body["type"]["artifact"] == "provenance-server"


@pytest.mark.asyncio
async def test_register_workflow(client: AsyncClient):
    resp = await client.post(
        "/provenance/workflows",
        json={
            "id": "trs://dockstore.org/workflow/github.com/test/wf",
            "name": "My Workflow",
            "version": "2.0.0",
            "descriptor_type": "WDL",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["response"]["id"] == "trs://dockstore.org/workflow/github.com/test/wf"
    assert body["response"]["version"] == "2.0.0"


@pytest.mark.asyncio
async def test_register_workflow_duplicate(client: AsyncClient):
    payload = {"id": "trs://dockstore.org/workflow/github.com/test/dup", "name": "DupWF"}
    await client.post("/provenance/workflows", json=payload)
    resp = await client.post("/provenance/workflows", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_workflow_not_found(client: AsyncClient):
    resp = await client.get(
        "/provenance/workflows/trs://dockstore.org/workflow/github.com/does/not/exist"
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_workflows(client: AsyncClient):
    for i in range(3):
        await client.post(
            "/provenance/workflows",
            json={"id": f"trs://dockstore.org/workflow/github.com/test/wf{i}", "name": f"WF{i}"},
        )
    resp = await client.get("/provenance/workflows")
    assert resp.status_code == 200
    assert len(resp.json()["response"]) == 3


@pytest.mark.asyncio
async def test_update_workflow(client: AsyncClient):
    await client.post(
        "/provenance/workflows",
        json={"id": "trs://dockstore.org/workflow/github.com/test/upd", "name": "Old Name"},
    )
    resp = await client.put(
        "/provenance/workflows/trs://dockstore.org/workflow/github.com/test/upd",
        json={"id": "trs://dockstore.org/workflow/github.com/test/upd", "name": "New Name"},
    )
    assert resp.status_code == 200
    assert resp.json()["response"]["name"] == "New Name"
