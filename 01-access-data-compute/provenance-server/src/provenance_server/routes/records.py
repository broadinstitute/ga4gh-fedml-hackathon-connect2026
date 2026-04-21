"""Provenance record CRUD endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from provenance_server.config import Settings, get_settings
from provenance_server.database import get_session
from provenance_server.models import (
    BeaconMeta,
    BeaconResponse,
    ProvenanceRecordCreate,
    ProvenanceRecordORM,
    ProvenanceRecordRead,
    WorkflowORM,
)

router = APIRouter(prefix="/provenance/records", tags=["records"])


@router.post(
    "",
    response_model=BeaconResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new provenance record",
)
async def create_record(
    body: ProvenanceRecordCreate,
    db: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> BeaconResponse:
    # Ensure workflow exists; create a stub if not
    wf = await db.get(WorkflowORM, body.workflow_id)
    if wf is None:
        wf = WorkflowORM(id=body.workflow_id)
        db.add(wf)

    record = ProvenanceRecordORM(
        id=str(uuid.uuid4()),
        data_element_id=body.data_element_id,
        workflow_id=body.workflow_id,
        workflow_version=body.workflow_version,
        execution_id=body.execution_id,
        site=body.site or settings.site,
        parameters=body.parameters,
        execution_timestamp=body.execution_timestamp,
        extra_metadata=body.extra_metadata,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return BeaconResponse(
        meta=BeaconMeta(beacon_id=settings.service_id),
        response=ProvenanceRecordRead.model_validate(record),
    )


@router.get(
    "/{record_id}",
    response_model=BeaconResponse,
    summary="Fetch a specific provenance record",
)
async def get_record(
    record_id: str,
    db: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> BeaconResponse:
    record = await db.get(ProvenanceRecordORM, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Record {record_id!r} not found")
    return BeaconResponse(
        meta=BeaconMeta(beacon_id=settings.service_id),
        response=ProvenanceRecordRead.model_validate(record),
    )


@router.delete(
    "/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a provenance record",
)
async def delete_record(
    record_id: str,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    record = await db.get(ProvenanceRecordORM, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Record {record_id!r} not found")
    await db.delete(record)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "",
    response_model=BeaconResponse,
    summary="List provenance records (paginated)",
)
async def list_records(
    db: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    limit: int = 100,
    offset: int = 0,
) -> BeaconResponse:
    stmt = select(ProvenanceRecordORM).limit(limit).offset(offset)
    result = await db.execute(stmt)
    records = [ProvenanceRecordRead.model_validate(r) for r in result.scalars()]
    return BeaconResponse(
        meta=BeaconMeta(beacon_id=settings.service_id),
        response=records,
    )
