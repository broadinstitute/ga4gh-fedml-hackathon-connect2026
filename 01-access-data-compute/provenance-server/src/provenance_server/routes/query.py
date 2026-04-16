"""Provenance query endpoint — Beacon-style query interface."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from provenance_server.config import Settings, get_settings
from provenance_server.crate import build_rocrate_zip
from provenance_server.database import get_session
from provenance_server.models import (
    BeaconMeta,
    BeaconResponse,
    ProvenanceQuery,
    ProvenanceRecordORM,
    ProvenanceRecordRead,
    WorkflowORM,
    WorkflowRead,
)

router = APIRouter(prefix="/provenance/query", tags=["query"])


def _apply_filters(stmt, body: ProvenanceQuery):
    """Apply query filters to a SQLAlchemy select statement."""
    if body.workflow_id is not None:
        stmt = stmt.where(ProvenanceRecordORM.workflow_id == body.workflow_id)
    if body.workflow_version is not None:
        stmt = stmt.where(ProvenanceRecordORM.workflow_version == body.workflow_version)
    if body.site is not None:
        stmt = stmt.where(ProvenanceRecordORM.site == body.site)
    if body.data_element_id is not None:
        stmt = stmt.where(ProvenanceRecordORM.data_element_id == body.data_element_id)
    return stmt


@router.post(
    "",
    response_model=BeaconResponse,
    summary="Query provenance records",
    description=(
        "Query data elements based on workflow provenance. "
        "Mirrors the Beacon v2 query/response pattern."
    ),
)
async def query_records(
    body: ProvenanceQuery,
    db: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> BeaconResponse:
    # Count total matching records (without pagination)
    count_stmt = _apply_filters(
        select(func.count()).select_from(ProvenanceRecordORM), body
    )
    total: int = (await db.execute(count_stmt)).scalar_one()

    # Fetch the requested page
    page_stmt = _apply_filters(select(ProvenanceRecordORM), body).limit(body.limit).offset(body.offset)
    result = await db.execute(page_stmt)
    records = result.scalars().all()

    response_items = []
    for rec in records:
        r = ProvenanceRecordRead.model_validate(rec)
        if not body.include_parameters:
            r = r.model_copy(update={"parameters": None})
        response_items.append(r)

    return BeaconResponse(
        meta=BeaconMeta(beacon_id=settings.service_id),
        response={
            "numTotalResults": total,
            "results": response_items,
        },
    )


@router.post(
    "/export",
    summary="Query provenance records and export as RO-Crate zip",
    response_class=Response,
    responses={
        200: {
            "content": {"application/zip": {}},
            "description": "RO-Crate zip archive",
        }
    },
)
async def export_records(
    body: ProvenanceQuery,
    db: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    """Return matching provenance records as a downloadable RO-Crate zip."""
    stmt = _apply_filters(select(ProvenanceRecordORM), body).limit(body.limit).offset(body.offset)
    result = await db.execute(stmt)
    orm_records = result.scalars().all()

    records = [ProvenanceRecordRead.model_validate(r) for r in orm_records]

    # Fetch all referenced workflows
    workflow_ids = {r.workflow_id for r in records}
    workflows: dict[str, WorkflowRead] = {}
    for wf_id in workflow_ids:
        wf_orm = await db.get(WorkflowORM, wf_id)
        if wf_orm is not None:
            workflows[wf_id] = WorkflowRead.model_validate(wf_orm)

    zip_bytes = build_rocrate_zip(records, workflows, site=settings.site)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=provenance-crate.zip"},
    )
