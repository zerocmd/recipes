"""Enum constants for the Command Zero API.

The API documents some enums as **closed** (a fixed set) and some as
**open** (new values may be added in future releases). For closed enums
the SDK uses the StrEnum as the model field type so the value is strictly
validated. For open enums the model field is plain ``str`` and these
StrEnums are provided as ergonomic constants (autocomplete, easy
comparison) without rejecting unknown values.

Open enums per the spec: investigation status, remediation status, role.
Closed enums: severity, sensitivity (TLP), confidence level, impact,
investigation type, attribution type, business-context status, postback
method, alert-entry action, create-investigation action.
"""
from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    """Backport-friendly str enum (Python 3.10 compatible)."""

    def __str__(self) -> str:  # pragma: no cover
        return self.value


# ---------------------------------------------------------------------------
# Closed enums — strictly validated by pydantic models.
# ---------------------------------------------------------------------------


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class Sensitivity(StrEnum):
    """TLP-style sensitivity classification."""
    RED = "red"
    STRICT = "strict"
    AMBER = "amber"
    GREEN = "green"
    CLEAR = "clear"


class ConfidenceLevel(StrEnum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"


class Impact(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class InvestigationType(StrEnum):
    ALERT = "alert"
    TEMPLATE = "template"
    MANUAL = "manual"


class CreateInvestigationAction(StrEnum):
    """Returned on POST /investigations to indicate whether the alert
    started a new investigation or merged into an existing one."""
    CREATED = "created"
    MERGED = "merged"


class AlertEntryAction(StrEnum):
    INVESTIGATED = "investigated"
    IGNORED = "ignored"


class AttributionType(StrEnum):
    USER = "user"
    APPLICATION = "application"
    C0 = "c0"
    SUPPORT = "support"


class BusinessContextStatus(StrEnum):
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class PostbackMethod(StrEnum):
    POST = "POST"
    PUT = "PUT"


class HealthStatus(StrEnum):
    OK = "ok"


# ---------------------------------------------------------------------------
# Open enums — provided as constants for ergonomics, but not validated.
# ---------------------------------------------------------------------------


class InvestigationStatus(StrEnum):
    """Open enum. Field type on the model is ``str`` so unknown future
    values flow through. The transitions accepted by PATCH are limited to
    IN_PROGRESS, ON_HOLD, COMPLETED."""

    INVESTIGATING = "investigating"
    PENDING_REVIEW = "pending-review"
    IN_PROGRESS = "in-progress"
    ON_HOLD = "on-hold"
    COMPLETED = "completed"
    FAILED = "failed"


class RemediationStatus(StrEnum):
    """Open enum."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    NOT_FOUND = "not_found"
    UNCHANGED = "unchanged"
    INTERRUPTED = "interrupted"


class Role(StrEnum):
    """Open enum. Used for users, applications, and organizations."""

    OBSERVER = "observer"
    INVESTIGATOR = "investigator"
    RESPONDER = "responder"
    ADMINISTRATOR = "administrator"


# ---------------------------------------------------------------------------
# Statuses the client may set via PATCH /investigations/{id}.
# Not modeled as an enum on the request schema so transition errors raise
# UnprocessableEntityError from the API; this set is exported for guards.
# ---------------------------------------------------------------------------


PATCHABLE_INVESTIGATION_STATUSES = frozenset({
    InvestigationStatus.IN_PROGRESS.value,
    InvestigationStatus.ON_HOLD.value,
    InvestigationStatus.COMPLETED.value,
})
