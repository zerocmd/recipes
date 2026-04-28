"""Shared HTTP client for the Command Zero Public API.

Used by every example script. Handles bearer-token auth, 429 retry with
backoff, X-Cmdzero-Traceid logging, and the GET/QUERY pagination pattern
described at https://api.cmdzero.io/public/v1/doc.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Iterator
from urllib.parse import urljoin

import requests

DEFAULT_BASE_URL = "https://api.cmdzero.io/public/v1"
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 5

log = logging.getLogger("cmdzero")


def _maybe_load_dotenv() -> None:
    """Load a .env from the current dir or any ancestor, if python-dotenv
    is installed. Silent no-op otherwise."""
    try:
        from dotenv import load_dotenv, find_dotenv
    except ImportError:
        return
    path = find_dotenv(usecwd=True)
    if path:
        load_dotenv(path, override=False)


_maybe_load_dotenv()


def _env_api_key() -> str | None:
    return os.environ.get("COMMAND_ZERO_API") or os.environ.get("CMDZERO_API_KEY")


def _env_org_id() -> str | None:
    return os.environ.get("COMMAND_ZERO_ORG") or os.environ.get("CMDZERO_ORG_ID")


class CommandZeroError(Exception):
    def __init__(self, status: int, message: str, trace_id: str | None, body: Any = None):
        super().__init__(f"[{status}] {message} (trace={trace_id})")
        self.status = status
        self.trace_id = trace_id
        self.body = body


class CommandZeroClient:
    def __init__(
        self,
        api_key: str | None = None,
        organization_id: str | None = None,
        base_url: str | None = None,
    ):
        self.api_key = api_key or _env_api_key()
        if not self.api_key:
            raise RuntimeError("COMMAND_ZERO_API (or CMDZERO_API_KEY) env var or api_key arg required")
        self.organization_id = organization_id or _env_org_id()
        self.base_url = (base_url or os.environ.get("CMDZERO_API_BASE") or DEFAULT_BASE_URL).rstrip("/") + "/"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def _org(self, organization_id: str | None) -> str:
        if organization_id:
            return organization_id
        if self.organization_id:
            return self.organization_id
        # No org configured — discover from the API. Same endpoint health_check.py
        # uses. Cache on the client so subsequent calls in the same session skip the
        # round-trip.
        orgs = self.list_organizations()
        if not orgs:
            raise RuntimeError(
                "API key has no organization access — check the application's role "
                "in the Command Zero console"
            )
        if len(orgs) > 1:
            listing = "\n".join(f"  {o['id']}  {o.get('name', '')}" for o in orgs)
            raise RuntimeError(
                "API key can access multiple organizations — set COMMAND_ZERO_ORG "
                "(or CMDZERO_ORG_ID) to pick one:\n" + listing
            )
        self.organization_id = orgs[0]["id"]
        log.info("auto-selected organization %s (%s)", self.organization_id, orgs[0].get("name", ""))
        return self.organization_id

    def request(self, method: str, path: str, *, json: Any = None, params: dict | None = None) -> dict:
        url = urljoin(self.base_url, path.lstrip("/"))
        delay = 1.0
        for attempt in range(1, MAX_RETRIES + 1):
            resp = self.session.request(method, url, json=json, params=params, timeout=DEFAULT_TIMEOUT)
            trace_id = resp.headers.get("X-Cmdzero-Traceid")

            if resp.status_code == 429 and attempt < MAX_RETRIES:
                retry_after = float(resp.headers.get("Retry-After", delay))
                log.warning("429 throttled (trace=%s) — sleeping %.1fs", trace_id, retry_after)
                time.sleep(retry_after)
                delay = min(delay * 2, 30)
                continue

            if not resp.ok:
                try:
                    body = resp.json()
                    message = body.get("message", resp.text)
                except ValueError:
                    body = resp.text
                    message = resp.text
                raise CommandZeroError(resp.status_code, message, trace_id, body)

            log.debug("%s %s -> %d (trace=%s)", method, url, resp.status_code, trace_id)
            if resp.status_code == 204 or not resp.content:
                return {}
            return resp.json()

        raise CommandZeroError(429, "exceeded retry budget", None)

    def get(self, path: str, **kw) -> dict:
        return self.request("GET", path, **kw)

    def post(self, path: str, json: Any = None, **kw) -> dict:
        return self.request("POST", path, json=json, **kw)

    def put(self, path: str, json: Any = None, **kw) -> dict:
        return self.request("PUT", path, json=json, **kw)

    def patch(self, path: str, json: Any = None, **kw) -> dict:
        return self.request("PATCH", path, json=json, **kw)

    def delete(self, path: str, **kw) -> dict:
        return self.request("DELETE", path, **kw)

    def query(
        self,
        path: str,
        *,
        filter: str | None = None,
        limit: int = 100,
        extra: dict | None = None,
        method: str = "GET",
    ) -> Iterator[dict]:
        """Iterate every item across pages.

        Defaults to ``GET`` because role policies often allow GET on
        a path while restricting QUERY. Pass ``method='QUERY'`` for
        complex filters that exceed safe URL length.
        """
        params: dict[str, Any] = {"limit": limit}
        if filter:
            params["filter"] = filter
        if extra:
            params.update(extra)
        next_cursor = ""
        while True:
            if next_cursor:
                params["next"] = next_cursor
            if method.upper() == "QUERY":
                page = self.request("QUERY", path, json=params)
            else:
                page = self.request("GET", path, params=params)
            items_key = _find_items_key(page)
            for item in page.get(items_key, []):
                yield item
            next_cursor = page.get("next", "") or ""
            if not next_cursor:
                return

    # Convenience wrappers — keep them thin; each script composes its own logic.

    def health(self) -> dict:
        return self.get("/ok")

    def list_organizations(self) -> list[dict]:
        return self.get("/organizations").get("organizations", [])

    def org_path(self, suffix: str, organization_id: str | None = None) -> str:
        return f"/organizations/{self._org(organization_id)}{suffix}"


_KNOWN_ITEM_KEYS = (
    "investigations",
    "investigationTemplates",
    "remediations",
    "remediationTemplates",
    "uploads",
    "applications",
    "users",
    "organizations",
    "catalogTypes",
    "types",
)


def _find_items_key(page: dict) -> str:
    for key in _KNOWN_ITEM_KEYS:
        if key in page:
            return key
    for key, value in page.items():
        if isinstance(value, list) and key not in {"errors", "warnings"}:
            return key
    return "items"


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
