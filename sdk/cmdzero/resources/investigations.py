from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from ..models import (
    CreateInvestigationRequest,
    CreateInvestigationResponse,
    Investigation,
    InvestigationSubject,
    InvestigationSummary,
    Postback,
    TypeAnnotation,
    UpdateInvestigationRequest,
)
from ..pagination import PaginatedIterator
from .base import BaseResource


class InvestigationsResource(BaseResource):
    """Start, query, and update investigations.

    The two main creation paths — alert-based and template-based — are
    exposed as ``create_from_alert`` and ``create_from_template``.
    ``create`` accepts the raw request schema for full flexibility.
    """

    def _path(self, organization_id: str | UUID | None, suffix: str = "") -> str:
        return f"/organizations/{self._org(organization_id)}/investigations{suffix}"

    # ---- read ----------------------------------------------------------

    def list(
        self,
        *,
        filter: str | None = None,
        limit: int | None = None,
        method: str = "GET",
        organization_id: str | UUID | None = None,
    ) -> PaginatedIterator[InvestigationSummary]:
        """Paginate the investigation list. Returns InvestigationSummary
        objects (the lighter schema the API returns on list); call get(id)
        for the full Investigation. Pass ``method='QUERY'`` for filters
        long enough to exceed safe URL length."""
        return self._paginate(
            self._path(organization_id),
            InvestigationSummary,
            "investigations",
            filter=filter,
            limit=limit,
            method=method,
        )

    def get(self, investigation_id: str | UUID, *, organization_id: str | UUID | None = None) -> Investigation:
        data = self._request("GET", self._path(organization_id, f"/{investigation_id}"))
        return Investigation.model_validate(data)

    # ---- create --------------------------------------------------------

    def create(
        self,
        request: CreateInvestigationRequest,
        *,
        nosettle: bool = False,
        organization_id: str | UUID | None = None,
    ) -> CreateInvestigationResponse:
        params = {"nosettle": "true"} if nosettle else None
        data = self._request(
            "POST",
            self._path(organization_id),
            json=self._dump(request),
            params=params,
        )
        return CreateInvestigationResponse.model_validate(data)

    def create_from_alert(
        self,
        *,
        alert_data: dict[str, Any],
        alert_type: str | None = None,
        alert_schema: list[TypeAnnotation] | list[dict[str, str]] | str | None = None,
        title: str | None = None,
        description: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        postback: Postback | dict[str, Any] | None = None,
        nosettle: bool = False,
        organization_id: str | UUID | None = None,
    ) -> CreateInvestigationResponse:
        request = CreateInvestigationRequest(
            alert_data=alert_data,
            alert_type=alert_type,
            alert_schema=_normalize_alert_schema(alert_schema),
            title=title,
            description=description,
            category=category,
            tags=tags,
            start_time=start_time,
            end_time=end_time,
            postback=Postback.model_validate(postback) if isinstance(postback, dict) else postback,
        )
        return self.create(request, nosettle=nosettle, organization_id=organization_id)

    def create_from_template(
        self,
        template_id: str,
        leads: list[InvestigationSubject] | list[dict[str, Any]],
        *,
        title: str | None = None,
        description: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        postback: Postback | dict[str, Any] | None = None,
        nosettle: bool = False,
        organization_id: str | UUID | None = None,
    ) -> CreateInvestigationResponse:
        normalized_leads = [
            lead if isinstance(lead, InvestigationSubject) else InvestigationSubject.model_validate(lead)
            for lead in leads
        ]
        request = CreateInvestigationRequest(
            template_id=template_id,
            leads=normalized_leads,
            title=title,
            description=description,
            category=category,
            tags=tags,
            start_time=start_time,
            end_time=end_time,
            postback=Postback.model_validate(postback) if isinstance(postback, dict) else postback,
        )
        return self.create(request, nosettle=nosettle, organization_id=organization_id)

    # ---- update --------------------------------------------------------

    def update(
        self,
        investigation_id: str | UUID,
        request: UpdateInvestigationRequest | None = None,
        *,
        organization_id: str | UUID | None = None,
        **fields: Any,
    ) -> Investigation:
        if request is None:
            request = UpdateInvestigationRequest(**fields)
        elif fields:
            raise TypeError("pass either a request object or keyword fields, not both")

        data = self._request(
            "PATCH",
            self._path(organization_id, f"/{investigation_id}"),
            json=self._dump(request),
        )
        return Investigation.model_validate(data)


def _normalize_alert_schema(schema: Any) -> Any:
    if schema is None or isinstance(schema, str):
        return schema
    return [
        item if isinstance(item, TypeAnnotation) else TypeAnnotation.model_validate(item)
        for item in schema
    ]
