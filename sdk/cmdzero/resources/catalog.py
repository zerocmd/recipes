from __future__ import annotations

from uuid import UUID

from ..models import CatalogType
from ..pagination import PaginatedIterator
from .base import BaseResource


class CatalogResource(BaseResource):
    """Catalog of subject types used to annotate alert payloads and
    business-context records (e.g. EMAIL_ADDRESS, IP_ADDRESS, SHA_256).

    The catalog endpoint does not paginate — every type comes back in
    one response — but the list method still returns a PaginatedIterator
    for shape consistency.
    """

    def _path(self, organization_id: str | UUID | None, suffix: str = "") -> str:
        return f"/organizations/{self._org(organization_id)}/catalog/types{suffix}"

    def list(
        self,
        *,
        filter: str | None = None,
        limit: int | None = None,
        organization_id: str | UUID | None = None,
    ) -> PaginatedIterator[CatalogType]:
        return self._paginate(
            self._path(organization_id),
            CatalogType,
            "types",
            filter=filter,
            limit=limit,
        )

    def alert_types(self, *, organization_id: str | UUID | None = None) -> PaginatedIterator[CatalogType]:
        """Catalog types valid in alert schemas (`isAlert eq true`)."""
        return self.list(filter="isAlert eq true", organization_id=organization_id)

    def get(self, type_id: str, *, organization_id: str | UUID | None = None) -> CatalogType:
        data = self._request("GET", self._path(organization_id, f"/{type_id}"))
        return CatalogType.model_validate(data)
