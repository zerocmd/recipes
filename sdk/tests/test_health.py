"""Health resource: cz.health.check() should hit /ok unauthenticated-style."""
from __future__ import annotations

import httpx
import respx

from cmdzero import HealthResponse


@respx.mock
def test_health_check_calls_ok_endpoint(client, fixture, base_url):
    route = respx.get(f"{base_url}/ok").mock(
        return_value=httpx.Response(200, json=fixture("health_ok"))
    )

    result = client.health.check()

    assert route.called
    assert route.calls[0].request.method == "GET"
    assert route.calls[0].request.url.path == "/public/v1/ok"
    assert isinstance(result, HealthResponse)
    assert result.status == "ok"
