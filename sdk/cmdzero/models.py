"""Pydantic v2 models for every documented Command Zero schema.

Naming: snake_case in Python; aliased to camelCase on the wire via
``alias_generator=to_camel`` and ``populate_by_name=True``. Unknown
fields are preserved (``extra='allow'``) so the SDK is forward-compatible
with new server fields.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from .enums import (
    AlertEntryAction,
    AttributionType,
    BusinessContextStatus,
    ConfidenceLevel,
    CreateInvestigationAction,
    HealthStatus,
    Impact,
    InvestigationType,
    PostbackMethod,
    Sensitivity,
    Severity,
)


class _Base(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="allow",
        use_enum_values=True,
    )


# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------


class Attribution(_Base):
    """Who performed an action. ``id`` is present for user/application,
    absent for c0/support attributions."""
    type: AttributionType
    name: str
    id: UUID | None = None


class Error(_Base):
    """Error response body returned for every status code >= 400."""
    message: str
    status: int
    trace_id: str
    type: str


class TypeAnnotation(_Base):
    """Maps a JSON path inside alert/business-context data to a catalog type."""
    path: str
    type: str


class Postback(_Base):
    """Webhook configuration for asynchronous result delivery."""
    url: str
    token: str | None = None
    method: PostbackMethod | None = None


class Observable(_Base):
    """Atom of intelligence found during an investigation."""
    type: str
    value: Any
    origin: list[str] = Field(default_factory=list)


class UserReference(_Base):
    """Lightweight user pointer used inside template / investigation payloads."""
    id: UUID
    name: str | None = None


class QueryRequest(_Base):
    """Body of any QUERY-method request."""
    filter: str | None = None
    limit: int | None = None
    next: str | None = None


class _ListEnvelope(_Base):
    """Common pagination envelope for list responses."""
    next: str = ""
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthResponse(_Base):
    status: HealthStatus


# ---------------------------------------------------------------------------
# Organizations
# ---------------------------------------------------------------------------


class Organization(_Base):
    id: UUID
    name: str
    role: str  # open enum (Role)
    created_by: Attribution
    created_time: datetime
    updated_by: Attribution
    updated_time: datetime


class ListOrganizationsResponse(_ListEnvelope):
    organizations: list[Organization] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------


class Application(_Base):
    id: UUID
    name: str
    role: str  # open enum (Role)
    fingerprint: str
    expires_at: datetime | None = None
    created_by: Attribution
    created_time: datetime
    updated_by: Attribution
    updated_time: datetime


class ListApplicationsResponse(_ListEnvelope):
    applications: list[Application] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


class User(_Base):
    id: UUID
    email: str | None = None
    name: str | None = None
    role: str  # open enum
    created_by: Attribution | None = None
    created_time: datetime | None = None
    updated_by: Attribution | None = None
    updated_time: datetime | None = None


class ListUsersResponse(_ListEnvelope):
    users: list[User] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------


class CatalogTypeField(_Base):
    name: str
    type: str
    required: bool = False
    description: str | None = None


class CatalogType(_Base):
    id: str
    name: str
    description: str | None = None
    is_alert: bool = False
    examples: list[Any] = Field(default_factory=list)
    fields: list[CatalogTypeField] = Field(default_factory=list)
    created_by: Attribution | None = None
    created_time: datetime | None = None
    updated_by: Attribution | None = None
    updated_time: datetime | None = None


class ListCatalogTypesResponse(_ListEnvelope):
    types: list[CatalogType] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Business Context
# ---------------------------------------------------------------------------


class BusinessContextUpload(_Base):
    id: str
    organization_id: UUID
    name: str
    description: str = ""
    record_count: int = 0
    status: BusinessContextStatus
    subject_types: list[str] = Field(default_factory=list)
    error: str = ""
    created_by: Attribution
    created_time: datetime
    updated_by: Attribution
    updated_time: datetime


class CreateBusinessContextUploadRequest(_Base):
    name: str
    records: list[dict[str, Any]]
    schema_: list[TypeAnnotation] = Field(alias="schema")
    description: str | None = None


class ReplaceBusinessContextUploadRequest(_Base):
    """At least one field required. records and schema must be paired."""
    name: str | None = None
    description: str | None = None
    records: list[dict[str, Any]] | None = None
    schema_: list[TypeAnnotation] | None = Field(default=None, alias="schema")


class ListBusinessContextUploadsResponse(_ListEnvelope):
    uploads: list[BusinessContextUpload] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Investigation Templates
# ---------------------------------------------------------------------------


class InvestigationTemplate(_Base):
    id: str
    name: str  # slug, e.g. "users-last-day"
    title: str | None = None
    description: str | None = None
    scenario: str | None = None
    sensitivity: str | None = None
    severity: str | None = None
    sliding_date: int | None = None
    lead_types: list[str] = Field(default_factory=list)
    assignees: list[UserReference] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    created_by: Attribution | None = None
    created_time: datetime | None = None
    updated_by: Attribution | None = None
    updated_time: datetime | None = None


class ListInvestigationTemplatesResponse(_ListEnvelope):
    investigation_templates: list[InvestigationTemplate] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Investigations
# ---------------------------------------------------------------------------


class InvestigationSubject(_Base):
    """Lead or remediation target."""
    type: str
    value: Any


class InvestigationAlertEntry(_Base):
    action: AlertEntryAction
    name: str | None = None
    description: str | None = None
    title: str | None = None
    time: datetime | None = None
    data: dict[str, Any] | None = None
    schema_: Any | None = Field(default=None, alias="schema")
    ids: list[str] = Field(default_factory=list)


class CreateInvestigationRequest(_Base):
    """One of three alert variants OR a templateId+leads payload.

    Validation of the variant combination is enforced server-side; the
    SDK accepts any combination and forwards it.
    """
    # Alert-based fields
    alert_data: dict[str, Any] | None = None
    alert_schema: Any | None = None  # str (catalog type) | TypeAnnotation[]
    alert_type: str | None = None
    # Template-based fields
    template_id: str | None = None
    leads: list[InvestigationSubject] | None = None
    # Optional on either form
    title: str | None = None
    description: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    postback: Postback | None = None


class UpdateInvestigationRequest(_Base):
    """All fields optional. Arrays fully replace the existing value."""
    assignees: list[UUID] | None = None
    category: str | None = None
    description: str | None = None
    sensitivity: Sensitivity | None = None
    severity: Severity | None = None
    status: str | None = None  # client-settable subset enforced server-side
    tags: list[str] | None = None
    title: str | None = None


class Investigation(_Base):
    id: UUID
    organization_id: UUID
    title: str
    description: str | None = None
    # Documented enums are treated as plain str on response models because
    # the production API returns mixed-case values (e.g. "Low" alongside
    # "high") and adds new values over time. The enum classes in
    # cmdzero.enums remain useful as constants for comparison.
    type: str | None = None
    status: str
    severity: str | None = None
    sensitivity: str | None = None
    category: str | None = None
    confidence_level: str | None = None
    impact: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    completed_time: datetime | None = None
    closed_time: datetime | None = None
    created_by: Attribution
    created_time: datetime
    updated_by: Attribution
    updated_time: datetime
    console_url: str | None = None
    investigation_url: str | None = None
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)
    verdict: list[str] = Field(default_factory=list)
    assignees: list[UserReference] = Field(default_factory=list)
    observables: list[Observable] = Field(default_factory=list)
    alerts: list[InvestigationAlertEntry] | None = None
    template_id: str | None = None


class CreateInvestigationResponse(Investigation):
    """Response from POST /investigations — extends Investigation with action."""
    action: CreateInvestigationAction


class ListInvestigationsResponse(_ListEnvelope):
    investigations: list[Investigation] = Field(default_factory=list)


class InvestigationPostbackPayload(_Base):
    investigation_id: UUID
    organization_id: UUID
    status: str
    severity: str | None = None
    summary: str | None = None
    verdict: list[str] = Field(default_factory=list)
    observables: list[Observable] = Field(default_factory=list)
    console_url: str | None = None
    error: str | None = None
    created_by: Attribution
    created_time: datetime
    updated_by: Attribution
    updated_time: datetime
    completed_time: datetime | None = None


# ---------------------------------------------------------------------------
# Remediations
# ---------------------------------------------------------------------------


class RemediationSubject(_Base):
    type: str
    value: Any


class RemediationTemplate(_Base):
    id: str
    name: str
    display_name: str | None = None
    description: str | None = None
    subject_type: str | None = None
    undo_template_id: str = ""
    created_by: Attribution | None = None
    created_time: datetime | None = None
    updated_by: Attribution | None = None
    updated_time: datetime | None = None


class ListRemediationTemplatesResponse(_ListEnvelope):
    remediation_templates: list[RemediationTemplate] = Field(default_factory=list)


class CreateRemediationRequest(_Base):
    template_id: str
    subject: RemediationSubject
    justification: str | None = None
    postback: Postback | None = None


class Remediation(_Base):
    id: UUID
    organization_id: UUID
    template_id: str
    template_name: str | None = None
    subject: RemediationSubject
    status: str  # open enum
    result: Any | None = None
    error: str = ""
    justification: str = ""
    console_url: str | None = None
    created_by: Attribution
    created_time: datetime
    updated_by: Attribution
    updated_time: datetime
    completed_time: datetime | None = None


class ListRemediationsResponse(_ListEnvelope):
    remediations: list[Remediation] = Field(default_factory=list)


class RemediationPostbackPayload(_Base):
    remediation_id: UUID
    organization_id: UUID
    template_id: str
    template_name: str | None = None
    subject: RemediationSubject
    status: str
    result: Any | None = None
    error: str | None = None
    console_url: str | None = None
    created_by: Attribution
    created_time: datetime
    updated_by: Attribution
    updated_time: datetime
    completed_time: datetime | None = None
