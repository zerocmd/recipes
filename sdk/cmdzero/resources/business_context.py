from __future__ import annotations

from typing import Any
from uuid import UUID

from ..models import (
    BusinessContextUpload,
    CreateBusinessContextUploadRequest,
    ReplaceBusinessContextUploadRequest,
    TypeAnnotation,
)
from ..pagination import PaginatedIterator
from .base import BaseResource


class BusinessContextResource(BaseResource):
    """Upload and manage business-context datasets that enrich
    investigations (HR directory, CMDB, IAM exports, etc.).
    """

    def _path(self, organization_id: str | UUID | None, suffix: str = "") -> str:
        return f"/organizations/{self._org(organization_id)}/business-context/uploads{suffix}"

    def list(
        self,
        *,
        filter: str | None = None,
        limit: int | None = None,
        method: str = "GET",
        organization_id: str | UUID | None = None,
    ) -> PaginatedIterator[BusinessContextUpload]:
        return self._paginate(
            self._path(organization_id),
            BusinessContextUpload,
            "uploads",
            filter=filter,
            limit=limit,
            method=method,
        )

    def get(self, upload_id: str, *, organization_id: str | UUID | None = None) -> BusinessContextUpload:
        data = self._request("GET", self._path(organization_id, f"/{upload_id}"))
        return BusinessContextUpload.model_validate(data)

    def upload(
        self,
        *,
        name: str,
        records: list[dict[str, Any]],
        schema: list[TypeAnnotation] | list[dict[str, str]],
        description: str | None = None,
        organization_id: str | UUID | None = None,
    ) -> BusinessContextUpload:
        request = CreateBusinessContextUploadRequest(
            name=name,
            records=records,
            schema_=[TypeAnnotation.model_validate(s) for s in schema],
            description=description,
        )
        data = self._request("POST", self._path(organization_id), json=self._dump(request))
        return BusinessContextUpload.model_validate(data)

    def replace(
        self,
        upload_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        records: list[dict[str, Any]] | None = None,
        schema: list[TypeAnnotation] | list[dict[str, str]] | None = None,
        organization_id: str | UUID | None = None,
    ) -> BusinessContextUpload:
        if (records is None) ^ (schema is None):
            raise ValueError("records and schema must be provided together")
        request = ReplaceBusinessContextUploadRequest(
            name=name,
            description=description,
            records=records,
            schema_=[TypeAnnotation.model_validate(s) for s in schema] if schema else None,
        )
        data = self._request(
            "PUT",
            self._path(organization_id, f"/{upload_id}"),
            json=self._dump(request),
        )
        return BusinessContextUpload.model_validate(data)

    def delete(self, upload_id: str, *, organization_id: str | UUID | None = None) -> None:
        self._request("DELETE", self._path(organization_id, f"/{upload_id}"))
