"""Resource base — shared transport, default-org resolution, paginate helper."""
from __future__ import annotations

from typing import Any, Callable, TypeVar
from uuid import UUID

from pydantic import BaseModel

from ..pagination import PaginatedIterator
from ..transport import HttpTransport

T = TypeVar("T", bound=BaseModel)


class BaseResource:
    def __init__(self, transport: HttpTransport, default_organization_id: str | None = None):
        self._transport = transport
        self._default_org = default_organization_id

    # -- helpers ---------------------------------------------------------

    def _org(self, organization_id: str | UUID | None) -> str:
        org = organization_id or self._default_org
        if org is None:
            raise RuntimeError(
                "organization_id not provided and no default set on the client"
            )
        return str(org)

    def _request(self, method: str, path: str, *, json: Any = None, params: dict | None = None) -> dict:
        return self._transport.request(method, path, json=json, params=params)

    def _paginate(
        self,
        path: str,
        item_cls: type[T],
        items_key: str,
        *,
        filter: str | None = None,
        limit: int | None = None,
        method: str = "GET",
    ) -> PaginatedIterator[T]:
        """Iterate a list endpoint.

        Defaults to ``GET`` because a) it's compatible with role policies
        that expose only GET on a path and b) GET is cache-friendly.
        Pass ``method='QUERY'`` for filters that exceed safe URL length
        (the spec recommends QUERY for "complex requests").
        """
        params_or_body: dict[str, Any] = {}
        if filter is not None:
            params_or_body["filter"] = filter
        if limit is not None:
            params_or_body["limit"] = limit

        if method.upper() == "QUERY":
            def fetch(cursor: str | None) -> dict:
                payload = dict(params_or_body)
                if cursor:
                    payload["next"] = cursor
                return self._request("QUERY", path, json=payload)
        else:
            def fetch(cursor: str | None) -> dict:
                params = dict(params_or_body)
                if cursor:
                    params["next"] = cursor
                return self._request(method.upper(), path, params=params or None)

        return PaginatedIterator(fetch, items_key, item_cls)

    @staticmethod
    def _dump(model: BaseModel) -> dict[str, Any]:
        return model.model_dump(by_alias=True, exclude_none=True, mode="json")
