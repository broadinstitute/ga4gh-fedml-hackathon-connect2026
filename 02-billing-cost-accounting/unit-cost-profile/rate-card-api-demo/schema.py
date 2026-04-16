"""Pydantic models for the GA4GH federated rate card schema v0.1.0.

See rate-card-spec.md for the schema definition.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_CONTEXT: list = [
    "https://schema.org",
    {"x_ga4gh": "https://ga4gh.org/fedml/rate-card/v0#"},
]


class _Base(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")


class Organization(_Base):
    type_: str = Field(default="Organization", alias="@type")
    name: str


class Hardware(_Base):
    cpu_model: Optional[str] = Field(default=None, alias="cpuModel")
    arch: Optional[str] = None
    memory_gib: Optional[float] = Field(default=None, alias="memoryGiB")
    gpu_model: Optional[str] = Field(default=None, alias="gpuModel")
    interconnect: Optional[str] = None


class Limits(_Base):
    max_wall_hours: Optional[float] = Field(default=None, alias="maxWallHours")
    max_cpus_per_job: Optional[int] = Field(default=None, alias="maxCpusPerJob")
    max_memory_gib: Optional[float] = Field(default=None, alias="maxMemoryGiB")


class DataGovernance(_Base):
    phi_allowed: Optional[bool] = Field(default=None, alias="phiAllowed")
    export_controlled: Optional[bool] = Field(default=None, alias="exportControlled")
    irb_gated: Optional[bool] = Field(default=None, alias="irbGated")


class UnitPriceSpecification(_Base):
    type_: str = Field(default="UnitPriceSpecification", alias="@type")
    price: str
    price_currency: str = Field(alias="priceCurrency")
    unit_code: Optional[str] = Field(default=None, alias="unitCode")
    unit_text: str = Field(alias="unitText")
    valid_from: Optional[str] = Field(default=None, alias="validFrom")


class Offer(_Base):
    type_: str = Field(default="Offer", alias="@type")
    identifier: str
    name: Optional[str] = None
    sku_id: Optional[str] = Field(default=None, alias="x_ga4gh:skuId")
    allow_preemption: bool = Field(default=False, alias="x_ga4gh:allowPreemption")
    hardware: Optional[Hardware] = Field(default=None, alias="x_ga4gh:hardware")
    limits: Optional[Limits] = Field(default=None, alias="x_ga4gh:limits")
    price_specification: list[UnitPriceSpecification] = Field(alias="priceSpecification")


class RateCard(_Base):
    context: list = Field(default_factory=lambda: list(DEFAULT_CONTEXT), alias="@context")
    type_: str = Field(default="Service", alias="@type")
    id_: str = Field(alias="@id")
    identifier: str
    name: str
    provider: Organization

    spec_version: str = Field(default="0.1.0", alias="x_ga4gh:specVersion")
    rate_card_version: str = Field(alias="x_ga4gh:rateCardVersion")
    valid_from: Optional[str] = Field(default=None, alias="validFrom")
    valid_through: Optional[str] = Field(default=None, alias="validThrough")
    billing_currency: str = Field(default="USD", alias="x_ga4gh:billingCurrency")

    requires_allocation: Optional[bool] = Field(default=None, alias="x_ga4gh:requiresAllocation")
    allocation_contact: Optional[str] = Field(default=None, alias="x_ga4gh:allocationContact")
    payer_model: Optional[str] = Field(default=None, alias="x_ga4gh:payerModel")
    data_governance: Optional[DataGovernance] = Field(default=None, alias="x_ga4gh:dataGovernance")
    support_contact: Optional[str] = Field(default=None, alias="x_ga4gh:supportContact")
    authentication: Optional[str] = Field(default=None, alias="x_ga4gh:authentication")

    offers: list[Offer]
