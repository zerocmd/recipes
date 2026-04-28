"""Remediations resource: list, get, create."""
from __future__ import annotations

import httpx
import respx

from cmdzero import Remediation

PATH = "remediations"


@respx.mock
def test_remediations_list(client, fixture, base_url, org_id):
    route = respx.get(f"{base_url}/organizations/{org_id}/{PATH}").mock(
        return_value=httpx.Response(200, json=fixture("remediations_list"))
    )

    list(client.remediations.list())
    assert route.called
    assert route.calls[0].request.url.path == \
        f"/public/v1/organizations/{org_id}/{PATH}"


@respx.mock
def test_remediations_get(client, fixture, base_url, org_id):
    sample = fixture("remediations_list")["remediations"][0]
    rem_id = sample["id"]
    route = respx.get(f"{base_url}/organizations/{org_id}/{PATH}/{rem_id}").mock(
        return_value=httpx.Response(200, json=sample)
    )

    rem = client.remediations.get(rem_id)
    assert route.called
    assert isinstance(rem, Remediation)


@respx.mock
def test_remediations_create_posts_to_collection(client, fixture, base_url, org_id):
    sample = fixture("remediations_list")["remediations"][0]
    route = respx.post(f"{base_url}/organizations/{org_id}/{PATH}").mock(
        return_value=httpx.Response(200, json=sample)
    )

    client.remediations.create(
        template_id="tmpl-abc",
        subject={"type": "MICROSOFT_ENTRA_USER", "value": "alice@example.com"},
        justification="Automated containment",
    )

    assert route.called
    assert route.calls[0].request.method == "POST"
    assert route.calls[0].request.url.path == \
        f"/public/v1/organizations/{org_id}/{PATH}"
    body = route.calls[0].request.content
    assert b"templateId" in body
    assert b"tmpl-abc" in body
    assert b"justification" in body
