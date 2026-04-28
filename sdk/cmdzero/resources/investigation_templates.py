from __future__ import annotations

from uuid import UUID

from ..models import InvestigationTemplate
from ..pagination import PaginatedIterator
from .base import BaseResource


class InvestigationTemplatesResource(BaseResource):
    def _path(self, organization_id: str | UUID | None, suffix: str = "") -> str:
        return f"/organizations/{self._org(organization_id)}/investigations/templates{suffix}"

    def list(
        self,
        *,
        filter: str | None = None,
        limit: int | None = None,
        organization_id: str | UUID | None = None,
    ) -> PaginatedIterator[InvestigationTemplate]:
        return self._paginate(
            self._path(organization_id),
            InvestigationTemplate,
            "investigationTemplates",
            filter=filter,
            limit=limit,
        )

    def get(self, template_id: str, *, organization_id: str | UUID | None = None) -> InvestigationTemplate:
        data = self._request("GET", self._path(organization_id, f"/{template_id}"))
        return InvestigationTemplate.model_validate(data)
