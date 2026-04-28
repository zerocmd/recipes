"""Applications resource: list and get."""
from __future__ import annotations

import httpx
import respx

from cmdzero import Application


@respx.mock
def test_applications_list_uses_org_scoped_path(client, fixture, base_url, org_id):
    route = respx.get(f"{base_url}/organizations/{org_id}/applications").mock(
        return_value=httpx.Response(200, json=fixture("applications_list"))
    )

    apps = list(client.applications.list())

    assert route.called
    assert route.calls[0].request.url.path == \
        f"/public/v1/organizations/{org_id}/applications"
    assert all(isinstance(a, Application) for a in apps)


@respx.mock
def test_applications_get_appends_id_to_path(client, fixture, base_url, org_id):
    sample = fixture("applications_list")["applications"][0]
    app_id = sample["id"]
    route = respx.get(
        f"{base_url}/organizations/{org_id}/applications/{app_id}"
    ).mock(return_value=httpx.Response(200, json=sample))

    app = client.applications.get(app_id)

    assert route.called
    assert isinstance(app, Application)
    assert str(app.id) == app_id
