"""Business context resource: list, get, upload, replace, delete."""
from __future__ import annotations

import httpx
import respx

from cmdzero import BusinessContextUpload

BC_PATH = "business-context/uploads"


@respx.mock
def test_business_context_list_uses_kebab_uploads_path(client, fixture, base_url, org_id):
    route = respx.get(f"{base_url}/organizations/{org_id}/{BC_PATH}").mock(
        return_value=httpx.Response(200, json=fixture("business_context_list"))
    )

    list(client.business_context.list())

    assert route.called
    assert route.calls[0].request.url.path == \
        f"/public/v1/organizations/{org_id}/{BC_PATH}"


@respx.mock
def test_business_context_get_appends_id(client, fixture, base_url, org_id):
    sample = fixture("business_context_list")["uploads"][0]
    upload_id = sample["id"]
    route = respx.get(
        f"{base_url}/organizations/{org_id}/{BC_PATH}/{upload_id}"
    ).mock(return_value=httpx.Response(200, json=sample))

    upload = client.business_context.get(upload_id)

    assert route.called
    assert isinstance(upload, BusinessContextUpload)
    assert upload.id == upload_id


@respx.mock
def test_business_context_upload_posts_to_collection(client, fixture, base_url, org_id):
    sample = fixture("business_context_list")["uploads"][0]
    route = respx.post(f"{base_url}/organizations/{org_id}/{BC_PATH}").mock(
        return_value=httpx.Response(200, json=sample)
    )

    result = client.business_context.upload(
        name="HR Directory",
        records=[{"email": "alice@example.com", "vip": True}],
        schema=[{"path": "email", "type": "EMAIL_ADDRESS"}],
        description="HR data",
    )

    assert route.called
    assert route.calls[0].request.method == "POST"
    assert isinstance(result, BusinessContextUpload)


@respx.mock
def test_business_context_replace_puts_to_id(client, fixture, base_url, org_id):
    sample = fixture("business_context_list")["uploads"][0]
    upload_id = sample["id"]
    route = respx.put(
        f"{base_url}/organizations/{org_id}/{BC_PATH}/{upload_id}"
    ).mock(return_value=httpx.Response(200, json=sample))

    result = client.business_context.replace(
        upload_id,
        name="HR Directory v2",
        records=[{"email": "bob@example.com"}],
        schema=[{"path": "email", "type": "EMAIL_ADDRESS"}],
    )

    assert route.called
    assert route.calls[0].request.method == "PUT"
    assert isinstance(result, BusinessContextUpload)


@respx.mock
def test_business_context_delete_calls_delete_on_id(client, base_url, org_id):
    upload_id = "abc-123"
    route = respx.delete(
        f"{base_url}/organizations/{org_id}/{BC_PATH}/{upload_id}"
    ).mock(return_value=httpx.Response(204))

    client.business_context.delete(upload_id)

    assert route.called
    assert route.calls[0].request.method == "DELETE"
