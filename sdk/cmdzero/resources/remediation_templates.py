from __future__ import annotations

from uuid import UUID

from ..models import RemediationTemplate
from ..pagination import PaginatedIterator
from .base import BaseResource


class RemediationTemplatesResource(BaseResource):
    def _path(self, organization_id: str | UUID | None, suffix: str = "") -> str:
        return f"/organizations/{self._org(organization_id)}/remediation-templates{suffix}"

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
        """Fetch a single remediation template by id.

        The public API does not expose a GET-by-id endpoint for remediation
        templates (it returns 404), and server-side filtering is not honored
        on this endpoint either. As a workaround we paginate the list and
        match client-side. This is fine in practice — the catalog of
        remediation templates is small.
        """
        for tmpl in self.list(organization_id=organization_id):
            if tmpl.id == template_id:
                return tmpl
        from ..exceptions import NotFoundError
        raise NotFoundError(404, f"remediation template not found: {template_id}")

    def for_subject_type(
        self,
        subject_type: str,
        *,
        organization_id: str | UUID | None = None,
    ) -> PaginatedIterator[RemediationTemplate]:
        """Templates whose subject type matches (e.g. MICROSOFT_ENTRA_USER)."""
        safe = subject_type.replace("'", "''")
        return self.list(filter=f"subjectType eq '{safe}'", organization_id=organization_id)
