from __future__ import annotations

from ..models import Organization
from ..pagination import PaginatedIterator
from .base import BaseResource


class OrganizationsResource(BaseResource):
    """Organizations the application can act against.

    Note: this resource ignores the default organization_id since the
    organizations endpoint is itself the *discovery* mechanism for orgs.
    """

    PATH = "/organizations"

    def list(self, *, filter: str | None = None, limit: int | None = None) -> PaginatedIterator[Organization]:
        return self._paginate(self.PATH, Organization, "organizations", filter=filter, limit=limit)
