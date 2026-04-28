from __future__ import annotations

from uuid import UUID

from ..models import User
from ..pagination import PaginatedIterator
from .base import BaseResource


class UsersResource(BaseResource):
    def _path(self, organization_id: str | UUID | None, suffix: str = "") -> str:
        return f"/organizations/{self._org(organization_id)}/users{suffix}"

    def list(
        self,
        *,
        filter: str | None = None,
        limit: int | None = None,
        organization_id: str | UUID | None = None,
    ) -> PaginatedIterator[User]:
        return self._paginate(
            self._path(organization_id),
            User,
            "users",
            filter=filter,
            limit=limit,
        )

    def get(self, user_id: str | UUID, *, organization_id: str | UUID | None = None) -> User:
        data = self._request("GET", self._path(organization_id, f"/{user_id}"))
        return User.model_validate(data)

    def assignable(self, *, organization_id: str | UUID | None = None) -> PaginatedIterator[User]:
        """Convenience wrapper for `role ne 'observer'`, the canonical
        filter for users who can be assigned an investigation."""
        return self.list(filter="role ne 'observer'", organization_id=organization_id)
