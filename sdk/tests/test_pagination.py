"""Cross-cutting pagination behavior. Uses organizations.list() as the
exercise vehicle but the logic under test is in
sdk/cmdzero/pagination.py and sdk/cmdzero/resources/base.py."""
from __future__ import annotations

import httpx
import respx


def _org(id_suffix: str, name: str) -> dict:
    """Build a minimal valid Organization JSON body."""
    user = {"type": "user", "name": "Test", "id": "22222222-2222-2222-2222-222222222222"}
    return {
        "id": f"00000000-0000-0000-0000-00000000000{id_suffix}",
        "name": name,
        "role": "Investigators",
        "createdBy": user,
        "createdTime": "2026-04-28T00:00:00Z",
        "updatedBy": user,
        "updatedTime": "2026-04-28T00:00:00Z",
    }


@respx.mock
def test_single_page_terminates_when_next_is_empty(client, base_url):
    respx.get(f"{base_url}/organizations").mock(
        return_value=httpx.Response(
            200,
            json={"organizations": [_org("1", "a")], "next": ""},
        )
    )

    orgs = list(client.organizations.list())
    assert len(orgs) == 1


@respx.mock
def test_multi_page_follows_next_cursor(client, base_url):
    page1 = {"organizations": [_org("a", "a")], "next": "cursor-1"}
    page2 = {"organizations": [_org("b", "b")], "next": "cursor-2"}
    page3 = {"organizations": [_org("c", "c")], "next": ""}

    route = respx.get(f"{base_url}/organizations").mock(
        side_effect=[
            httpx.Response(200, json=page1),
            httpx.Response(200, json=page2),
            httpx.Response(200, json=page3),
        ]
    )

    orgs = list(client.organizations.list())

    assert [o.name for o in orgs] == ["a", "b", "c"]
    assert route.call_count == 3
    # second call must include the cursor returned by the first
    assert route.calls[1].request.url.params.get("next") == "cursor-1"
    assert route.calls[2].request.url.params.get("next") == "cursor-2"


@respx.mock
def test_empty_first_page_returns_no_items(client, base_url):
    respx.get(f"{base_url}/organizations").mock(
        return_value=httpx.Response(200, json={"organizations": [], "next": ""})
    )

    assert list(client.organizations.list()) == []


@respx.mock
def test_limit_is_forwarded(client, base_url):
    route = respx.get(f"{base_url}/organizations").mock(
        return_value=httpx.Response(200, json={"organizations": [], "next": ""})
    )

    list(client.organizations.list(limit=25))

    assert route.calls[0].request.url.params.get("limit") == "25"


@respx.mock
def test_filter_is_forwarded(client, base_url):
    route = respx.get(f"{base_url}/organizations").mock(
        return_value=httpx.Response(200, json={"organizations": [], "next": ""})
    )

    list(client.organizations.list(filter="role eq 'Investigators'"))

    assert route.calls[0].request.url.params.get("filter") == "role eq 'Investigators'"
