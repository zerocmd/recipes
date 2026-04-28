"""Organizations resource: cz.organizations.list() iterates /organizations."""
from __future__ import annotations

import httpx
import respx

from cmdzero import Organization


@respx.mock
def test_organizations_list_calls_top_level_organizations(client, fixture, base_url):
    route = respx.get(f"{base_url}/organizations").mock(
        return_value=httpx.Response(200, json=fixture("organizations_list"))
    )

    orgs = list(client.organizations.list())

    assert route.called
    assert route.calls[0].request.url.path == "/public/v1/organizations"
    assert all(isinstance(o, Organization) for o in orgs)
    assert any(o.id == "51c264ff-5a98-4f15-b7e1-07158d35151c" for o in orgs)


@respx.mock
def test_organizations_list_forwards_filter_and_limit(client, fixture, base_url):
    route = respx.get(f"{base_url}/organizations").mock(
        return_value=httpx.Response(200, json=fixture("organizations_list"))
    )

    list(client.organizations.list(filter="role eq 'Investigators'", limit=10))

    assert route.called
    sent = route.calls[0].request.url
    assert sent.params.get("filter") == "role eq 'Investigators'"
    assert sent.params.get("limit") == "10"
