"""
Command Zero API client.

Handles two operations:
  1. Submit a Splunk notable as a CZ investigation with an explicit alertSchema
     (Case 2). The schema is sent on the first submission of each alertType so
     CZ knows how to extract observables; subsequent submissions omit it.
  2. Poll a batch of open investigations for verdict-ready status.
"""

import asyncio
import logging
from typing import Optional

import httpx

from config import Config

log = logging.getLogger(__name__)

# A verdict is ready once automation finishes. The verdict persists across every
# post-automation status (the CZ spec's `completed` example still carries a verdict),
# so we don't restrict to `pending-review` — otherwise a verdict picked up after an
# analyst has already moved the case past pending-review would be lost.
POST_AUTOMATION_STATUSES = {"pending-review", "in-progress", "on-hold", "completed"}

_MAX_429_RETRIES = 3
_DEFAULT_RETRY_AFTER_S = 60


class SubmitResult:
    def __init__(self, investigation_id: str, action: str):
        self.investigation_id = investigation_id
        self.action = action  # "created" | "merged"


class VerdictResult:
    def __init__(
        self,
        investigation_id: str,
        status: str,
        verdict: Optional[list[str]],
        confidence: Optional[str],
        severity: Optional[str],
        summary: Optional[str],
        console_url: Optional[str],
        category: Optional[str] = None,
        impact: Optional[str] = None,
        description: Optional[str] = None,
    ):
        self.investigation_id = investigation_id
        self.status = status
        self.verdict = verdict or []
        self.confidence = confidence
        self.severity = severity
        self.summary = summary
        self.console_url = console_url
        self.category = category
        self.impact = impact
        self.description = description

    @property
    def is_ready(self) -> bool:
        return self.status in POST_AUTOMATION_STATUSES and bool(self.verdict)

    @property
    def is_failed(self) -> bool:
        return self.status == "failed"


class CZClient:
    def __init__(self, cfg: Config):
        self._cfg = cfg
        self._client = httpx.AsyncClient(
            base_url=cfg.cz_api_base_url,
            headers={
                "Authorization": f"Bearer {cfg.cz_bearer_token}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Send an HTTP request, retrying on 429 with Retry-After back-off."""
        for attempt in range(_MAX_429_RETRIES + 1):
            resp = await getattr(self._client, method)(url, **kwargs)
            if resp.status_code != 429 or attempt == _MAX_429_RETRIES:
                return resp
            retry_after = int(resp.headers.get("Retry-After", _DEFAULT_RETRY_AFTER_S))
            log.warning(
                "CZ rate-limited (429); sleeping %ds before retry (attempt %d/%d)",
                retry_after, attempt + 1, _MAX_429_RETRIES,
            )
            await asyncio.sleep(retry_after)
        return resp  # unreachable, satisfies type checker

    # ------------------------------------------------------------------
    # Submit
    # ------------------------------------------------------------------

    async def submit(
        self,
        event_id: str,
        alert_type: str,
        title: str,
        description: str,
        alert_data: dict,
        schema: Optional[list[dict]] = None,
    ) -> SubmitResult:
        """
        Submit a notable as a CZ investigation.

        Pass `schema` (a list of TypeAnnotation dicts) on the first submission
        of a given alertType so CZ can extract the right observables. CZ caches
        the schema per alertType, so subsequent submissions can omit it.
        """
        # _alert_id must be set in alertData so CZ uses our event_id as the
        # correlation key rather than generating a random UUID (investigations.go:395).
        alert_data["_alert_id"] = event_id

        payload = {
            "alertType": alert_type,
            "title": title,
            "description": description,
            "alertData": alert_data,
        }
        if schema is not None:
            payload["alertSchema"] = schema
            log.debug("Including alertSchema (%d annotations) for type %s", len(schema), alert_type)

        log.info("Submitting notable %s as CZ investigation (type=%s)", event_id, alert_type)
        resp = await self._request(
            "post",
            f"/organizations/{self._cfg.cz_org_id}/investigations",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

        result = SubmitResult(
            investigation_id=data["id"],
            action=data.get("action", "created"),
        )
        log.info(
            "Notable %s → investigation %s (action=%s)",
            event_id,
            result.investigation_id,
            result.action,
        )
        return result

    # ------------------------------------------------------------------
    # Poll
    # ------------------------------------------------------------------

    async def poll_pending(self, investigation_ids: list[str]) -> list[VerdictResult]:
        """
        Fetch current status for a list of open investigations.
        Uses individual GET calls for now; can be replaced with a batch list
        endpoint once we confirm the exact filter params from the spec.
        """
        results = []
        for inv_id in investigation_ids:
            try:
                result = await self._get_investigation(inv_id)
                results.append(result)
            except Exception as exc:
                log.warning("Failed to poll investigation %s: %s", inv_id, exc)
        return results

    async def _get_investigation(self, investigation_id: str) -> VerdictResult:
        resp = await self._request(
            "get",
            f"/organizations/{self._cfg.cz_org_id}/investigations/{investigation_id}",
        )
        if resp.status_code == 404:
            log.warning("Investigation %s not found (archived or deleted); marking failed", investigation_id)
            return VerdictResult(
                investigation_id=investigation_id,
                status="failed",
                verdict=None,
                confidence=None,
                severity=None,
                summary=None,
                console_url=None,
            )
        resp.raise_for_status()
        data = resp.json()

        # verdict is a flat list of strings (e.g. ["Account Compromise"])
        verdicts = [v for v in data.get("verdict", []) if isinstance(v, str) and v]

        return VerdictResult(
            investigation_id=investigation_id,
            status=data.get("status", ""),
            verdict=verdicts,
            confidence=data.get("confidenceLevel") or data.get("confidence"),
            severity=data.get("severity"),
            summary=data.get("summary") or None,
            console_url=data.get("consoleUrl"),
            category=data.get("category") or None,
            impact=data.get("impact") or None,
            description=data.get("description") or None,
        )

    async def health_check(self) -> None:
        """Verify CZ API connectivity and auth. Raises RuntimeError with a human-readable message."""
        try:
            resp = await self._client.get(
                f"/organizations/{self._cfg.cz_org_id}/investigations"
            )
            resp.raise_for_status()
        except httpx.ConnectError as exc:
            raise RuntimeError(
                f"Cannot connect to CZ API at {self._cfg.cz_api_base_url}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 401:
                raise RuntimeError("CZ authentication failed — check CZ_BEARER_TOKEN") from exc
            if status in (403, 404):
                raise RuntimeError(
                    f"CZ org not found or access denied — check CZ_ORG_ID ({self._cfg.cz_org_id!r})"
                ) from exc
            raise RuntimeError(f"CZ health check failed (HTTP {status})") from exc

    async def close(self) -> None:
        await self._client.aclose()
