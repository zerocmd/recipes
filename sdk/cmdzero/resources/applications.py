from __future__ import annotations

from uuid import UUID

from ..models import Application
from ..pagination import PaginatedIterator
from .base import BaseResource


class ApplicationsResource(BaseResource):
    def _path(self, organization_id: str | UUID | None, suffix: str = "") -> str:
        return f"/organizations/{self._org(organization_id)}/applications{suffix}"

    def list(
        self,
        *,
        filter: str | None = None,
        limit: int | None = None,
        method: str = "GET",
        organization_id: str | UUID | None = None,
    ) -> PaginatedIterator[Application]:
        return self._paginate(
            self._path(organization_id),
            Application,
            "applications",
            filter=filter,
            limit=limit,
            method=method,
        )

    def get(self, application_id: str | UUID, *, organization_id: str | UUID | None = None) -> Application:
        data = self._request("GET", self._path(organization_id, f"/{application_id}"))
        return Application.model_validate(data)
