"""Federated query endpoint — fan-out to peer nodes and aggregate results."""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends

from provenance_server.config import Settings, get_settings
from provenance_server.models import BeaconMeta, BeaconResponse, ProvenanceQuery

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/federated", tags=["federation"])


async def _query_peer(
    client: httpx.AsyncClient, peer_url: str, query: ProvenanceQuery
) -> dict[str, Any] | None:
    """Send a query to a single peer node and return its response, or None on error."""
    url = f"{peer_url.rstrip('/')}/provenance/query"
    try:
        resp = await client.post(url, json=query.model_dump(mode="json"), timeout=15.0)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as exc:
        logger.warning("Peer %s query failed: %s", peer_url, exc)
        return None


@router.post(
    "/query",
    response_model=BeaconResponse,
    summary="Fan-out provenance query to all configured peer nodes",
    description=(
        "Queries this node plus all configured PROVENANCE_PEER_NODES and aggregates results. "
        "Peer nodes are queried in parallel."
    ),
)
async def federated_query(
    body: ProvenanceQuery,
    settings: Annotated[Settings, Depends(get_settings)],
) -> BeaconResponse:
    peers = settings.get_peer_nodes()
    aggregated: list[dict[str, Any]] = []
    errors: list[str] = []

    if peers:
        async with httpx.AsyncClient() as client:
            tasks = [_query_peer(client, peer, body) for peer in peers]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for peer, result in zip(peers, results):
            if isinstance(result, BaseException):
                errors.append(f"Exception querying {peer}: {result}")
                continue
            if result is None:
                errors.append(f"No response from {peer}")
                continue
            peer_response = result.get("response", {})
            peer_records = peer_response.get("results", [])
            for rec in peer_records:
                rec["_source_node"] = peer
            aggregated.extend(peer_records)

    return BeaconResponse(
        meta=BeaconMeta(beacon_id=settings.service_id),
        response={
            "numTotalResults": len(aggregated),
            "results": aggregated,
            "errors": errors,
            "queriedNodes": peers,
        },
    )


@router.get(
    "/peers",
    response_model=BeaconResponse,
    summary="List configured peer nodes",
)
async def list_peers(
    settings: Annotated[Settings, Depends(get_settings)],
) -> BeaconResponse:
    return BeaconResponse(
        meta=BeaconMeta(beacon_id=settings.service_id),
        response={"peers": settings.get_peer_nodes()},
    )
