"""SQLAlchemy ORM models and Pydantic schemas for the Provenance Server."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ---------------------------------------------------------------------------
# SQLAlchemy ORM
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    pass


class WorkflowORM(Base):
    """A workflow registered in this provenance node."""

    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(String(256), primary_key=True)
    """Canonical TRS URI, e.g. trs://dockstore.org/workflow/github.com/..."""

    name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    descriptor_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    trs_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Resolved TRS endpoint URL (if fetched from a registry)."""
    extra_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    records: Mapped[list[ProvenanceRecordORM]] = relationship(
        "ProvenanceRecordORM", back_populates="workflow", cascade="all, delete-orphan"
    )


class ProvenanceRecordORM(Base):
    """A single provenance record linking a data element to a workflow execution."""

    __tablename__ = "provenance_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    data_element_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    """DRS object ID, file path, or any resolvable identifier."""

    workflow_id: Mapped[str] = mapped_column(
        String(256), ForeignKey("workflows.id"), nullable=False, index=True
    )
    workflow_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    execution_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    """WES run ID or TES task ID that produced this data element."""

    site: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    parameters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    execution_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    extra_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    workflow: Mapped[WorkflowORM] = relationship("WorkflowORM", back_populates="records")


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class WorkflowCreate(BaseModel):
    """Request body for registering a workflow."""

    id: str = Field(
        ...,
        examples=["trs://dockstore.org/workflow/github.com/broadinstitute/gatk-workflows/broad-prod-wgs-germline-snps-indels"],
        description="Canonical TRS URI for the workflow.",
    )
    name: str | None = None
    version: str | None = None
    descriptor_type: str | None = Field(None, examples=["CWL", "WDL", "Nextflow"])
    description: str | None = None
    trs_url: str | None = None
    extra_metadata: dict[str, Any] | None = None


class WorkflowRead(WorkflowCreate):
    model_config = ConfigDict(from_attributes=True)

    created_at: datetime


class ProvenanceRecordCreate(BaseModel):
    """Request body for registering a provenance record."""

    data_element_id: str = Field(
        ...,
        examples=["drs://drs.example.org/abc123"],
        description="DRS object ID or other resolvable data element identifier.",
    )
    workflow_id: str = Field(
        ...,
        description="TRS URI of the workflow that produced this data element.",
    )
    workflow_version: str | None = None
    execution_id: str | None = Field(
        None,
        description="WES run ID or TES task ID associated with this execution.",
    )
    site: str | None = Field(None, description="Site/node identifier within the federation.")
    parameters: dict[str, Any] | None = None
    execution_timestamp: datetime | None = None
    extra_metadata: dict[str, Any] | None = None


class ProvenanceRecordRead(ProvenanceRecordCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime


class ProvenanceQuery(BaseModel):
    """Query parameters for the /provenance/query endpoint."""

    workflow_id: str | None = Field(None, description="Filter by workflow TRS URI.")
    workflow_version: str | None = Field(None, description="Filter by workflow version.")
    site: str | None = Field(None, description="Filter by site/node identifier.")
    data_element_id: str | None = Field(None, description="Filter by data element identifier.")
    include_parameters: bool = Field(
        False, description="Whether to include execution parameters in response."
    )
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)


# ---------------------------------------------------------------------------
# Beacon-style response envelopes
# ---------------------------------------------------------------------------


class BeaconMeta(BaseModel):
    """GA4GH / Beacon v2 compatible response metadata."""

    beacon_id: str
    api_version: str = "v0.1.0"
    returned_granularity: str = "record"


class BeaconResponse(BaseModel):
    """Generic Beacon-style response envelope."""

    meta: BeaconMeta
    response: Any
