"""Workflow registration and lookup endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from provenance_server.config import Settings, get_settings
from provenance_server.database import get_session
from provenance_server.models import (
    BeaconMeta,
    BeaconResponse,
    WorkflowCreate,
    WorkflowORM,
    WorkflowRead,
)
from provenance_server.trs_client import extract_workflow_metadata, resolve_workflow

router = APIRouter(prefix="/provenance/workflows", tags=["workflows"])


@router.post(
    "",
    response_model=BeaconResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a workflow (optionally auto-resolved from TRS)",
)
async def create_workflow(
    body: WorkflowCreate,
    db: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> BeaconResponse:
    existing = await db.get(WorkflowORM, body.id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Workflow {body.id!r} already registered. Use PUT to update.",
        )

    # Attempt to auto-resolve from TRS if no name is provided
    resolved_meta: dict = {}
    if body.id.startswith("trs://") and body.name is None:
        trs_data = await resolve_workflow(body.id)
        if trs_data:
            resolved_meta = extract_workflow_metadata(trs_data)

    wf = WorkflowORM(
        id=body.id,
        name=body.name or resolved_meta.get("name"),
        version=body.version,
        descriptor_type=body.descriptor_type or resolved_meta.get("descriptor_type"),
        description=body.description or resolved_meta.get("description"),
        trs_url=body.trs_url,
        extra_metadata=body.extra_metadata or resolved_meta.get("extra_metadata"),
    )
    db.add(wf)
    await db.commit()
    await db.refresh(wf)

    return BeaconResponse(
        meta=BeaconMeta(beacon_id=settings.service_id),
        response=WorkflowRead.model_validate(wf),
    )


@router.get(
    "",
    response_model=BeaconResponse,
    summary="List registered workflows",
)
async def list_workflows(
    db: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    limit: int = 100,
    offset: int = 0,
) -> BeaconResponse:
    stmt = select(WorkflowORM).limit(limit).offset(offset)
    result = await db.execute(stmt)
    workflows = [WorkflowRead.model_validate(w) for w in result.scalars()]
    return BeaconResponse(
        meta=BeaconMeta(beacon_id=settings.service_id),
        response=workflows,
    )


@router.get(
    "/{workflow_id:path}",
    response_model=BeaconResponse,
    summary="Get details of a specific workflow",
)
async def get_workflow(
    workflow_id: str,
    db: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> BeaconResponse:
    wf = await db.get(WorkflowORM, workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id!r} not found")
    return BeaconResponse(
        meta=BeaconMeta(beacon_id=settings.service_id),
        response=WorkflowRead.model_validate(wf),
    )


@router.put(
    "/{workflow_id:path}",
    response_model=BeaconResponse,
    summary="Update a registered workflow",
)
async def update_workflow(
    workflow_id: str,
    body: WorkflowCreate,
    db: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> BeaconResponse:
    wf = await db.get(WorkflowORM, workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id!r} not found")

    for field in ("name", "version", "descriptor_type", "description", "trs_url", "extra_metadata"):
        value = getattr(body, field)
        if value is not None:
            setattr(wf, field, value)

    await db.commit()
    await db.refresh(wf)
    return BeaconResponse(
        meta=BeaconMeta(beacon_id=settings.service_id),
        response=WorkflowRead.model_validate(wf),
    )
