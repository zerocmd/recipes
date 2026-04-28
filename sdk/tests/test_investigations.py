"""Investigations resource: list, get, create, create_from_alert,
create_from_template, update.

create_from_alert and create_from_template are wrappers around create()
that POST to the same /investigations endpoint with different request
body shapes — there are no /alerts or /templates subpaths.
"""
from __future__ import annotations

import httpx
import respx

from cmdzero import (
    CreateInvestigationRequest,
    CreateInvestigationResponse,
    Investigation,
    InvestigationSummary,
)

PATH = "investigations"


def _create_response(**overrides):
    """Build a minimal valid CreateInvestigationResponse JSON body."""
    body = {
        "id": "11111111-1111-1111-1111-111111111111",
        "organizationId": "51c264ff-5a98-4f15-b7e1-07158d35151c",
        "title": "Test investigation",
        "status": "pending-review",
        "createdBy": {"type": "user", "name": "Test", "id": "22222222-2222-2222-2222-222222222222"},
        "createdTime": "2026-04-28T00:00:00Z",
        "updatedBy": {"type": "user", "name": "Test", "id": "22222222-2222-2222-2222-222222222222"},
        "updatedTime": "2026-04-28T00:00:00Z",
        "action": "created",
    }
    body.update(overrides)
    return body


@respx.mock
def test_investigations_list_returns_summary_models(client, fixture, base_url, org_id):
    """list() returns InvestigationSummary (the lighter schema the API
    returns on list), NOT the full Investigation."""
    route = respx.get(f"{base_url}/organizations/{org_id}/{PATH}").mock(
        return_value=httpx.Response(200, json=fixture("investigations_list"))
    )

    items = list(client.investigations.list())
    assert route.called
    assert route.calls[0].request.url.path == \
        f"/public/v1/organizations/{org_id}/{PATH}"
    assert all(isinstance(i, InvestigationSummary) for i in items)


@respx.mock
def test_investigations_list_query_method_uses_QUERY_verb(client, fixture, base_url, org_id):
    """method='QUERY' on list() routes the request via HTTP QUERY (POST-like
    body) for filters that exceed safe URL length."""
    route = respx.route(method="QUERY", url=f"{base_url}/organizations/{org_id}/{PATH}").mock(
        return_value=httpx.Response(200, json=fixture("investigations_list"))
    )

    list(client.investigations.list(method="QUERY", filter="status eq 'in-progress'"))

    assert route.called
    assert route.calls[0].request.method == "QUERY"


@respx.mock
def test_investigations_get(client, fixture, base_url, org_id):
    sample = fixture("investigations_list")["investigations"][0]
    inv_id = sample["id"]
    route = respx.get(f"{base_url}/organizations/{org_id}/{PATH}/{inv_id}").mock(
        return_value=httpx.Response(200, json=sample)
    )

    inv = client.investigations.get(inv_id)
    assert route.called
    assert isinstance(inv, Investigation)


@respx.mock
def test_investigations_create_posts_to_collection(client, base_url, org_id):
    route = respx.post(f"{base_url}/organizations/{org_id}/{PATH}").mock(
        return_value=httpx.Response(200, json=_create_response())
    )

    body = CreateInvestigationRequest(title="Test investigation")
    result = client.investigations.create(body)

    assert route.called
    assert route.calls[0].request.method == "POST"
    assert route.calls[0].request.url.path == \
        f"/public/v1/organizations/{org_id}/{PATH}"
    assert isinstance(result, CreateInvestigationResponse)


@respx.mock
def test_investigations_create_from_alert_posts_with_alert_data(client, base_url, org_id):
    """create_from_alert POSTs to /investigations (NOT /investigations/alerts)
    with alertData/alertType in the body."""
    route = respx.post(f"{base_url}/organizations/{org_id}/{PATH}").mock(
        return_value=httpx.Response(200, json=_create_response())
    )

    client.investigations.create_from_alert(
        alert_type="example.alert",
        alert_data={"key": "value"},
    )

    assert route.called
    assert route.calls[0].request.url.path == \
        f"/public/v1/organizations/{org_id}/{PATH}"
    body = route.calls[0].request.content
    assert b"alertType" in body
    assert b"alertData" in body


@respx.mock
def test_investigations_create_from_template_posts_with_template_id(client, base_url, org_id):
    """create_from_template POSTs to /investigations (NOT /investigations/templates/{id})
    with templateId/leads in the body."""
    route = respx.post(f"{base_url}/organizations/{org_id}/{PATH}").mock(
        return_value=httpx.Response(200, json=_create_response())
    )

    client.investigations.create_from_template(
        "tmpl-abc",
        leads=[{"type": "MICROSOFT_ENTRA_USER_PRINCIPAL_NAME", "value": "alice@example.com"}],
    )

    assert route.called
    assert route.calls[0].request.url.path == \
        f"/public/v1/organizations/{org_id}/{PATH}"
    body = route.calls[0].request.content
    assert b"templateId" in body
    assert b"tmpl-abc" in body


@respx.mock
def test_investigations_update_patches_id(client, fixture, base_url, org_id):
    """update() PATCHes /investigations/{id}; accepts kwargs as request
    body fields (status, severity, etc.)."""
    sample = fixture("investigations_list")["investigations"][0]
    inv_id = sample["id"]
    route = respx.patch(
        f"{base_url}/organizations/{org_id}/{PATH}/{inv_id}"
    ).mock(return_value=httpx.Response(200, json=sample))

    client.investigations.update(inv_id, status="completed")

    assert route.called
    assert route.calls[0].request.method == "PATCH"
    assert route.calls[0].request.url.path == \
        f"/public/v1/organizations/{org_id}/{PATH}/{inv_id}"
    assert b"completed" in route.calls[0].request.content
