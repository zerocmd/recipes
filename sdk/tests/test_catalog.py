"""Catalog resource: types list, alert_types convenience, get."""
from __future__ import annotations

import httpx
import respx

from cmdzero import CatalogType


@respx.mock
def test_catalog_list_uses_catalog_types_path(client, fixture, base_url, org_id):
    route = respx.get(f"{base_url}/organizations/{org_id}/catalog/types").mock(
        return_value=httpx.Response(200, json=fixture("catalog_types_list"))
    )

    types = list(client.catalog.list())

    assert route.called
    assert route.calls[0].request.url.path == \
        f"/public/v1/organizations/{org_id}/catalog/types"
    assert all(isinstance(t, CatalogType) for t in types)


@respx.mock
def test_catalog_alert_types_filters_by_isAlert(client, fixture, base_url, org_id):
    """alert_types() is a wrapper for list(filter='isAlert eq true')."""
    route = respx.get(f"{base_url}/organizations/{org_id}/catalog/types").mock(
        return_value=httpx.Response(200, json=fixture("catalog_types_list"))
    )

    list(client.catalog.alert_types())

    assert route.called
    assert route.calls[0].request.url.params.get("filter") == "isAlert eq true"
