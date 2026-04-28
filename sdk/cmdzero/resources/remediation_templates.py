from __future__ import annotations

from uuid import UUID

from ..models import RemediationTemplate
from ..pagination import PaginatedIterator
from .base import BaseResource


class RemediationTemplatesResource(BaseResource):
    def _path(self, organization_id: str | UUID | None, suffix: str = "") -> str:
        return f"/organizations/{self._org(organization_id)}/remediations/templates{suffix}"

    def list(
        self,
        *,
        filter: str | None = None,
        limit: int | None = None,
        organization_id: str | UUID | None = None,
    ) -> PaginatedIterator[RemediationTemplate]:
        return self._paginate(
            self._path(organization_id),
            RemediationTemplate,
            "remediationTemplates",
            filter=filter,
            limit=limit,
        )

    def get(self, template_id: str, *, organization_id: str | UUID | None = None) -> RemediationTemplate:
        data = self._request("GET", self._path(organization_id, f"/{template_id}"))
        return RemediationTemplate.model_validate(data)

    def for_subject_type(
        self,
        subject_type: str,
        *,
        organization_id: str | UUID | None = None,
    ) -> PaginatedIterator[RemediationTemplate]:
        """Templates whose subject type matches (e.g. MICROSOFT_ENTRA_USER)."""
        safe = subject_type.replace("'", "''")
        return self.list(filter=f"subjectType eq '{safe}'", organization_id=organization_id)
