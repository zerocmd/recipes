"""
Splunk client — two responsibilities:
  1. Poll index=notable for new notables since the last checkpoint.
  2. Write the C0 verdict back onto the notable (notable_update comment + HEC event).
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from config import Config

log = logging.getLogger(__name__)

# Splunk search/jobs API returns results as JSON; we request JSON format.
_SEARCH_OUTPUT_MODE = "json"


class SplunkClient:
    def __init__(self, cfg: Config):
        self._cfg = cfg
        # TLS verification is on by default; SPLUNK_VERIFY_TLS=false opts out for a
        # self-signed cert (see Config.splunk_verify_tls). Disabling it exposes the
        # service token and notable data to MITM, so it should stay True in production.
        self._rest = httpx.AsyncClient(
            base_url=cfg.splunk_rest_url,
            headers={"Authorization": f"Splunk {cfg.splunk_svc_token}"},
            verify=cfg.splunk_verify_tls,
            timeout=30,
        )
        # ES search head for the notable_update writeback. Only spin up a distinct
        # client when the writeback is actually enabled AND ES lives on a different
        # host (Splunk Cloud / distributed). Otherwise alias the poll client, so the
        # single-instance case — and the writeback-disabled case — open no extra
        # connection. write_verdict (the only _es_rest consumer) still resolves.
        if cfg.splunk_es_writeback and cfg.splunk_es_rest_url != cfg.splunk_rest_url:
            self._es_rest = httpx.AsyncClient(
                base_url=cfg.splunk_es_rest_url,
                headers={"Authorization": f"Splunk {cfg.splunk_svc_token}"},
                verify=cfg.splunk_verify_tls,
                timeout=30,
            )
        else:
            self._es_rest = self._rest
        self._hec: Optional[httpx.AsyncClient] = None
        if cfg.splunk_hec_url and cfg.splunk_hec_token:
            self._hec = httpx.AsyncClient(
                base_url=cfg.splunk_hec_url,
                headers={"Authorization": f"Splunk {cfg.splunk_hec_token}"},
                verify=cfg.splunk_verify_tls,
                timeout=15,
            )

    # ------------------------------------------------------------------
    # Poll
    # ------------------------------------------------------------------

    async def poll_notables(self, since: Optional[str]) -> tuple[list[dict], str]:
        """
        Search index=notable for events since `since` (ISO-8601 UTC string).
        Returns (list of notable dicts, new checkpoint timestamp as ISO string).

        The checkpoint is pushed back by poll_window_overlap seconds to avoid
        gaps caused by Splunk's eventual-consistency indexing.
        """
        cfg = self._cfg
        overlap = timedelta(seconds=cfg.poll_window_overlap)

        if since:
            earliest_dt = datetime.fromisoformat(since) - overlap
            earliest = earliest_dt.strftime("%m/%d/%Y:%H:%M:%S")
        else:
            # First run: look back 24 hours
            earliest_dt = datetime.now(timezone.utc) - timedelta(hours=24)
            earliest = earliest_dt.strftime("%m/%d/%Y:%H:%M:%S")

        search = (
            f"search index={cfg.notable_index} earliest={earliest} latest=now"
            " | spath"
            " | fields event_id, rule_name, source, rule_title, rule_description,"
            "   security_domain, severity, urgency, status, owner, _time, *"
            " | sort _time"
        )

        log.debug("Splunk poll: %s", search)

        # Step 1: create the search job
        resp = await self._rest.post(
            "/services/search/jobs",
            data={"search": search, "output_mode": _SEARCH_OUTPUT_MODE},
        )
        resp.raise_for_status()
        sid = resp.json()["sid"]

        # Step 2: wait for the job to complete
        await self._wait_for_job(sid)

        # Step 3: fetch results
        results_resp = await self._rest.get(
            f"/services/search/jobs/{sid}/results",
            params={"output_mode": _SEARCH_OUTPUT_MODE, "count": 1000},
        )
        results_resp.raise_for_status()
        results = results_resp.json().get("results", [])

        new_checkpoint = datetime.now(timezone.utc).isoformat()
        log.info("Splunk poll returned %d notables", len(results))
        return results, new_checkpoint

    async def _wait_for_job(self, sid: str, timeout_s: int = 60) -> None:
        import asyncio

        deadline = datetime.now(timezone.utc) + timedelta(seconds=timeout_s)
        while datetime.now(timezone.utc) < deadline:
            resp = await self._rest.get(
                f"/services/search/jobs/{sid}",
                params={"output_mode": _SEARCH_OUTPUT_MODE},
            )
            resp.raise_for_status()
            state = resp.json()["entry"][0]["content"]["dispatchState"]
            if state in ("DONE", "FAILED"):
                if state == "FAILED":
                    raise RuntimeError(f"Splunk search job {sid} failed")
                return
            await asyncio.sleep(1)
        raise TimeoutError(f"Splunk search job {sid} timed out after {timeout_s}s")

    # ------------------------------------------------------------------
    # Writeback
    # ------------------------------------------------------------------

    async def write_verdict(
        self,
        event_id: str,
        rule_uid: str,
        verdict: str,
        confidence: Optional[str],
        severity: Optional[str],
        summary: Optional[str],
        console_url: Optional[str],
        investigation_id: str,
        category: Optional[str] = None,
        impact: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """Post a C0 verdict comment onto the ES notable via notable_update."""
        comment = _build_comment(
            verdict, confidence, severity, summary, console_url, investigation_id,
            category, impact, description,
        )
        log.info("Writing verdict back to notable %s: %s", event_id, verdict)

        resp = await self._es_rest.post(
            "/services/notable_update",
            data={
                "ruleUIDs": rule_uid,
                "comment": comment,
                "output_mode": _SEARCH_OUTPUT_MODE,
            },
        )
        resp.raise_for_status()
        log.debug("notable_update response: %s", resp.text)

    async def send_enrichment_event(
        self,
        event_id: str,
        investigation_id: str,
        verdict: Optional[str],
        confidence: Optional[str],
        severity: Optional[str],
        status: str,
        console_url: Optional[str],
        enrichment_index: str,
        category: Optional[str] = None,
        impact: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """Send a structured enrichment event to the HEC c0_enrichment index."""
        if not self._hec:
            log.debug("HEC not configured; skipping enrichment event")
            return

        payload = {
            "index": enrichment_index,
            "sourcetype": "c0:enrichment",
            "event": {
                "event_id": event_id,
                "c0_investigation_id": investigation_id,
                "c0_verdict": verdict,
                "c0_severity": severity,
                "c0_status": status,
                "c0_console_url": console_url,
                "c0_impact": impact,
                "c0_description": description,
            },
        }
        resp = await self._hec.post("/services/collector/event", json=payload)
        resp.raise_for_status()
        log.debug("HEC enrichment event sent for %s", event_id)

    async def health_check(self) -> None:
        """Verify Splunk REST connectivity and auth. Raises RuntimeError with a human-readable message."""
        try:
            resp = await self._rest.get("/services/server/info", params={"output_mode": "json"})
            resp.raise_for_status()
        except httpx.ConnectError as exc:
            raise RuntimeError(
                f"Cannot connect to Splunk REST at {self._cfg.splunk_rest_url} — is the server running?"
            ) from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise RuntimeError("Splunk authentication failed — check SPLUNK_SVC_TOKEN") from exc
            raise RuntimeError(f"Splunk health check failed (HTTP {exc.response.status_code})") from exc

    async def close(self) -> None:
        await self._rest.aclose()
        if self._es_rest is not self._rest:
            await self._es_rest.aclose()
        if self._hec:
            await self._hec.aclose()


def _build_comment(
    verdict: str,
    confidence: Optional[str],
    severity: Optional[str],
    summary: Optional[str],
    console_url: Optional[str],
    investigation_id: str,
    category: Optional[str] = None,
    impact: Optional[str] = None,
    description: Optional[str] = None,
) -> str:
    lines = [f"[Command Zero] Verdict: {verdict}"]
    if severity:
        lines.append(f"Severity: {severity}")
    if impact:
        lines.append(f"Impact: {impact}")
    if summary:
        lines.append(f"Summary: {summary}")
    if description:
        lines.append(f"Description: {description}")
    if console_url:
        lines.append(f"Investigation: {console_url}")
    lines.append(f"(C0 investigation ID: {investigation_id})")
    return "\n".join(lines)
