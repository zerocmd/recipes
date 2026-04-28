"""Users resource: list, get, assignable."""
from __future__ import annotations

import httpx
import respx

from cmdzero import User


@respx.mock
def test_users_list_uses_org_scoped_path(client, fixture, base_url, org_id):
    route = respx.get(f"{base_url}/organizations/{org_id}/users").mock(
        return_value=httpx.Response(200, json=fixture("users_list"))
    )

    users = list(client.users.list())

    assert route.called
    assert route.calls[0].request.url.path == \
        f"/public/v1/organizations/{org_id}/users"
    assert all(isinstance(u, User) for u in users)


@respx.mock
def test_users_get_appends_user_id(client, fixture, base_url, org_id):
    sample = fixture("users_list")["users"][0]
    user_id = sample["id"]
    route = respx.get(
        f"{base_url}/organizations/{org_id}/users/{user_id}"
    ).mock(return_value=httpx.Response(200, json=sample))

    user = client.users.get(user_id)

    assert route.called
    assert str(user.id) == user_id


@respx.mock
def test_users_assignable_filters_by_role_ne_observer(client, fixture, base_url, org_id):
    """assignable() is a wrapper for list(filter="role ne 'observer'") — same
    /users path, just with the filter applied."""
    route = respx.get(
        f"{base_url}/organizations/{org_id}/users"
    ).mock(return_value=httpx.Response(200, json=fixture("users_list")))

    list(client.users.assignable())

    assert route.called
    assert route.calls[0].request.url.params.get("filter") == "role ne 'observer'"
