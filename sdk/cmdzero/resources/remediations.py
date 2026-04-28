from __future__ import annotations

from typing import Any
from uuid import UUID

from ..models import (
    CreateRemediationRequest,
    Postback,
    Remediation,
    RemediationSubject,
)
from ..pagination import PaginatedIterator
from .base import BaseResource


class RemediationsResource(BaseResource):
    def _path(self, organization_id: str | UUID | None, suffix: str = "") -> str:
        return f"/organizations/{self._org(organization_id)}/remediations{suffix}"

    def list(
        self,
        *,
        filter: str | None = None,
        limit: int | None = None,
        method: str = "GET",
        organization_id: str | UUID | None = None,
    ) -> PaginatedIterator[Remediation]:
        return self._paginate(
            self._path(organization_id),
            Remediation,
            "remediations",
            filter=filter,
            limit=limit,
            method=method,
        )

    def get(self, remediation_id: str | UUID, *, organization_id: str | UUID | None = None) -> Remediation:
        data = self._request("GET", self._path(organization_id, f"/{remediation_id}"))
        return Remediation.model_validate(data)

    def create(
        self,
        *,
        template_id: str,
        subject: RemediationSubject | dict[str, Any],
        justification: str | None = None,
        postback: Postback | dict[str, Any] | None = None,
        organization_id: str | UUID | None = None,
    ) -> Remediation:
        request = CreateRemediationRequest(
            template_id=template_id,
            subject=subject if isinstance(subject, RemediationSubject) else RemediationSubject.model_validate(subject),
            justification=justification,
            postback=Postback.model_validate(postback) if isinstance(postback, dict) else postback,
        )
        data = self._request("POST", self._path(organization_id), json=self._dump(request))
        return Remediation.model_validate(data)
