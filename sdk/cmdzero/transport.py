"""HTTP transport: bearer auth, retry-on-429, structured error mapping.

Each Command Zero response is wrapped into either a parsed JSON dict
returned to the caller, or one of the typed exceptions in
``cmdzero.exceptions``. The X-Cmdzero-Traceid header is preserved on
every error so support escalations always carry the trace id.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx

from .exceptions import CommandZeroError, RateLimitError, TransportError, from_status

DEFAULT_BASE_URL = "https://api.cmdzero.io/public/v1"
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 5
DEFAULT_BACKOFF_BASE = 1.0
DEFAULT_BACKOFF_CAP = 30.0

log = logging.getLogger("cmdzero")


def env_api_key() -> str | None:
    """Return the API key from env, preferring COMMAND_ZERO_API.

    Falls back to CMDZERO_API_KEY for backwards compatibility.
    """
    return os.environ.get("COMMAND_ZERO_API") or os.environ.get("CMDZERO_API_KEY")


def env_organization_id() -> str | None:
    """Return the organization id from env, preferring COMMAND_ZERO_ORG."""
    return os.environ.get("COMMAND_ZERO_ORG") or os.environ.get("CMDZERO_ORG_ID")


class HttpTransport:
    """Sync HTTP transport built on httpx.

    Lifetime: a single HttpTransport owns one ``httpx.Client``. Closing
    the transport closes the client. The transport is safe to use across
    threads but not across processes.
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_base: float = DEFAULT_BACKOFF_BASE,
        backoff_cap: float = DEFAULT_BACKOFF_CAP,
        user_agent: str = "cmdzero-python-sdk/0.1.0",
        client: httpx.Client | None = None,
    ):
        self.base_url = base_url.rstrip("/") + "/"
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.backoff_cap = backoff_cap
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "User-Agent": user_agent,
        }
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=self.base_url,
            headers=headers,
            timeout=timeout,
        )
        if not self._owns_client:
            self._client.headers.update(headers)

    @classmethod
    def from_env(cls, **overrides) -> HttpTransport:
        api_key = overrides.pop("api_key", None) or env_api_key()
        if not api_key:
            raise RuntimeError("COMMAND_ZERO_API (or CMDZERO_API_KEY) env var or api_key arg required")
        base_url = overrides.pop("base_url", None) or os.environ.get("CMDZERO_API_BASE", DEFAULT_BASE_URL)
        return cls(api_key, base_url=base_url, **overrides)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> HttpTransport:
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    # ------------------------------------------------------------------ core

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        """Issue an HTTP request and return the parsed JSON body.

        Raises one of the ``cmdzero.exceptions`` subclasses on any error
        response, after exhausting the configured retry budget for 429s.
        """
        url = path if path.startswith("http") else path.lstrip("/")
        delay = self.backoff_base
        last_exc: CommandZeroError | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._client.request(method, url, json=json, params=params)
            except httpx.TimeoutException as e:
                raise TransportError(f"request timed out: {e}", cause=e) from e
            except httpx.HTTPError as e:
                raise TransportError(f"transport failure: {e}", cause=e) from e

            trace_id = response.headers.get("X-Cmdzero-Traceid")

            if response.status_code == 429 and attempt < self.max_retries:
                retry_after = _retry_after_seconds(response, fallback=delay)
                log.warning(
                    "429 throttled (trace=%s), sleeping %.2fs (attempt %d/%d)",
                    trace_id, retry_after, attempt, self.max_retries,
                )
                time.sleep(retry_after)
                delay = min(delay * 2, self.backoff_cap)
                continue

            if response.is_success:
                if response.status_code == 204 or not response.content:
                    return {}
                return response.json()

            last_exc = _build_error(response, trace_id)
            raise last_exc

        # only reachable if every retry was a 429 and we exhausted attempts
        if last_exc:
            raise last_exc
        raise RateLimitError(429, "exceeded retry budget", trace_id=None)


def _retry_after_seconds(response: httpx.Response, fallback: float) -> float:
    raw = response.headers.get("Retry-After")
    if not raw:
        return fallback
    try:
        return max(0.0, float(raw))
    except ValueError:
        # Date-form Retry-After is rare in practice; fall back to backoff.
        return fallback


def _build_error(response: httpx.Response, trace_id: str | None) -> CommandZeroError:
    body: Any
    try:
        body = response.json()
        message = body.get("message") if isinstance(body, dict) else response.text
        type_ = body.get("type") if isinstance(body, dict) else None
    except ValueError:
        body = response.text
        message = response.text
        type_ = None

    cls = from_status(response.status_code)
    if cls is RateLimitError:
        return RateLimitError(
            response.status_code,
            message or "rate limited",
            trace_id=trace_id,
            type=type_,
            body=body,
            retry_after=_retry_after_seconds(response, fallback=0.0),
        )
    return cls(
        response.status_code,
        message or response.reason_phrase,
        trace_id=trace_id,
        type=type_,
        body=body,
    )
