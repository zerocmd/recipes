"""Cross-cutting error handling. Each HTTP error class maps to a
specific exception subclass in cmdzero.exceptions."""
from __future__ import annotations

import httpx
import pytest
import respx

from cmdzero import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ServerError,
    UnauthorizedError,
    UnprocessableEntityError,
)


@respx.mock
def test_400_raises_bad_request(client, base_url):
    respx.get(f"{base_url}/organizations").mock(
        return_value=httpx.Response(400, json={"message": "bad request", "type": "bad_request"})
    )
    with pytest.raises(BadRequestError) as exc:
        list(client.organizations.list())
    assert exc.value.status == 400


@respx.mock
def test_401_raises_unauthorized(client, base_url):
    respx.get(f"{base_url}/organizations").mock(
        return_value=httpx.Response(401, json={"message": "unauthorized"})
    )
    with pytest.raises(UnauthorizedError):
        list(client.organizations.list())


@respx.mock
def test_403_raises_forbidden(client, fixture, base_url):
    respx.get(f"{base_url}/organizations").mock(
        return_value=httpx.Response(403, json=fixture("error_403"))
    )
    with pytest.raises(ForbiddenError):
        list(client.organizations.list())


@respx.mock
def test_404_raises_not_found(client, fixture, base_url):
    respx.get(f"{base_url}/organizations").mock(
        return_value=httpx.Response(404, json=fixture("error_404"))
    )
    with pytest.raises(NotFoundError):
        list(client.organizations.list())


@respx.mock
def test_409_raises_conflict(client, base_url):
    respx.get(f"{base_url}/organizations").mock(
        return_value=httpx.Response(409, json={"message": "conflict"})
    )
    with pytest.raises(ConflictError):
        list(client.organizations.list())


@respx.mock
def test_422_raises_unprocessable(client, base_url):
    respx.get(f"{base_url}/organizations").mock(
        return_value=httpx.Response(422, json={"message": "invalid"})
    )
    with pytest.raises(UnprocessableEntityError):
        list(client.organizations.list())


@respx.mock
def test_429_after_retry_budget_raises_rate_limit(client, fixture, base_url):
    """The transport retries 429 up to max_retries; once exhausted it raises."""
    respx.get(f"{base_url}/organizations").mock(
        return_value=httpx.Response(
            429,
            json=fixture("error_429"),
            headers={"Retry-After": "0"},
        )
    )
    with pytest.raises(RateLimitError):
        list(client.organizations.list())


@respx.mock
def test_500_raises_server_error(client, base_url):
    respx.get(f"{base_url}/organizations").mock(
        return_value=httpx.Response(500, json={"message": "boom"})
    )
    with pytest.raises(ServerError):
        list(client.organizations.list())


@respx.mock
def test_trace_id_propagated_on_error(client, fixture, base_url):
    respx.get(f"{base_url}/organizations").mock(
        return_value=httpx.Response(
            403,
            json=fixture("error_403"),
            headers={"X-Cmdzero-Traceid": "trace-abc-123"},
        )
    )
    with pytest.raises(ForbiddenError) as exc:
        list(client.organizations.list())
    assert exc.value.trace_id == "trace-abc-123"
