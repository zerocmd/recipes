"""Top-level Command Zero SDK client.

Composes every resource into a single facade so callers do, e.g.::

    from cmdzero import CommandZero

    cz = CommandZero(api_key="c0...", organization_id="<uuid>")
    health = cz.health.check()
    for inv in cz.investigations.list(filter="severity eq 'high'"):
        print(inv.id, inv.status)
"""
from __future__ import annotations

import os
from typing import Any
from uuid import UUID

import httpx

from .resources import (
    ApplicationsResource,
    BusinessContextResource,
    CatalogResource,
    HealthResource,
    InvestigationTemplatesResource,
    InvestigationsResource,
    OrganizationsResource,
    RemediationTemplatesResource,
    RemediationsResource,
    UsersResource,
)
from .transport import DEFAULT_BASE_URL, HttpTransport, env_api_key, env_organization_id


class CommandZero:
    """Single-tenant by default (set organization_id once); for MSSP use
    cases pass ``organization_id`` per call instead.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        organization_id: str | UUID | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        client: httpx.Client | None = None,
        user_agent: str | None = None,
    ):
        api_key = api_key or env_api_key()
        if not api_key:
            raise RuntimeError("COMMAND_ZERO_API (or CMDZERO_API_KEY) env var or api_key arg required")
        organization_id = organization_id or env_organization_id()
        base_url = base_url or os.environ.get("CMDZERO_API_BASE", DEFAULT_BASE_URL)

        transport_kwargs: dict[str, Any] = {"base_url": base_url}
        if timeout is not None:
            transport_kwargs["timeout"] = timeout
        if max_retries is not None:
            transport_kwargs["max_retries"] = max_retries
        if user_agent is not None:
            transport_kwargs["user_agent"] = user_agent
        if client is not None:
            transport_kwargs["client"] = client

        self._transport = HttpTransport(api_key, **transport_kwargs)
        self.organization_id = str(organization_id) if organization_id else None

        org = self.organization_id
        self.health = HealthResource(self._transport, org)
        self.organizations = OrganizationsResource(self._transport, org)
        self.applications = ApplicationsResource(self._transport, org)
        self.users = UsersResource(self._transport, org)
        self.catalog = CatalogResource(self._transport, org)
        self.business_context = BusinessContextResource(self._transport, org)
        self.investigation_templates = InvestigationTemplatesResource(self._transport, org)
        self.investigations = InvestigationsResource(self._transport, org)
        self.remediation_templates = RemediationTemplatesResource(self._transport, org)
        self.remediations = RemediationsResource(self._transport, org)

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> CommandZero:
        return self

    def __exit__(self, *_exc) -> None:
        self.close()
