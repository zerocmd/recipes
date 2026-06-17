"""
CZ ⇄ Splunk ES Connector — main loop.

Lifecycle per notable:
  1. Poll Splunk index=notable → discover new notables (checkpoint-based)
  2. Submit each new notable to CZ. Alert types in schemas.py are forwarded;
     all others are silently dropped. If an explicit schema is defined for the
     alert type it is sent on the first submission (CZ caches it); if the entry
     is None, CZ uses auto-schema to infer observables automatically.
  3. Poll CZ for verdict-ready status (status=pending-review + non-empty verdict)
  4. Write the verdict back onto the ES notable (notable_update comment + HEC event)
"""

import asyncio
import json
import logging
import signal
from datetime import datetime, timezone
from typing import Optional

from config import Config
from cz import CZClient
from schemas import get_schema, is_allowed
from splunk import SplunkClient
from store import Record, State, Store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger("connector")

def _scalar(value):
    """Coerce a Splunk multi-value field (list) to a single string."""
    if isinstance(value, list):
        return value[0] if value else None
    return value


MAX_SUBMIT_ATTEMPTS = 5
MAX_WRITEBACK_ATTEMPTS = 5
# Give up polling an investigation that never produces a verdict after this long.
MAX_POLL_AGE_SECONDS = 86400  # 1 day


class Connector:
    def __init__(self, cfg: Config):
        self._cfg = cfg
        self._store = Store(cfg.db_path)
        self._splunk = SplunkClient(cfg)
        self._cz = CZClient(cfg)
        self._running = False
        self._submitted_schemas: set[str] = set()  # alert types whose schema has been sent this session

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def run(self) -> None:
        self._running = True
        log.info("Connector starting (Splunk=%s, CZ org=%s)", self._cfg.splunk_rest_url, self._cfg.cz_org_id)

        while self._running:
            try:
                await self._tick()
            except Exception as exc:
                log.error("Tick error: %s", exc, exc_info=True)

            await asyncio.sleep(self._cfg.splunk_poll_interval)

    async def _tick(self) -> None:
        await self._poll_splunk()
        await self._submit_pending()
        await self._poll_cz()
        await self._writeback_ready()

    def stop(self) -> None:
        log.info("Shutdown requested")
        self._running = False

    # ------------------------------------------------------------------
    # Step 1: poll Splunk for new notables
    # ------------------------------------------------------------------

    async def _poll_splunk(self) -> None:
        index = self._cfg.notable_index
        checkpoint = self._store.get_checkpoint(index)

        notables, new_checkpoint = await self._splunk.poll_notables(since=checkpoint)
        self._store.set_checkpoint(index, new_checkpoint)

        for notable in notables:
            event_id = _scalar(notable.get("event_id"))
            if not event_id:
                log.warning("Notable missing event_id, skipping: %s", notable)
                continue

            if self._store.get(event_id):
                log.debug("Already seen %s, skipping", event_id)
                continue

            rule_name = _scalar(notable.get("source")) or _scalar(notable.get("rule_name")) or "unknown"
            alert_type = f"{self._cfg.alert_type_prefix}:{rule_name}"

            initial_state = State.DISCOVERED if is_allowed(alert_type) else State.NO_SCHEMA

            rec = Record(
                event_id=event_id,
                rule_name=rule_name,
                alert_type=alert_type,
                raw_notable=json.dumps(notable),
                state=initial_state,
            )
            self._store.upsert(rec)
            if initial_state is State.NO_SCHEMA:
                log.info("Discovered notable %s (type=%s) — not in allow-list, skipping submission", event_id, alert_type)
            else:
                log.info("Discovered notable %s (type=%s)", event_id, alert_type)

    # ------------------------------------------------------------------
    # Step 2: submit discovered notables to CZ
    # ------------------------------------------------------------------

    async def _submit_pending(self) -> None:
        for rec in self._store.pending_submission():
            if rec.submit_attempts >= MAX_SUBMIT_ATTEMPTS:
                log.error("Notable %s exceeded max submit attempts, marking failed", rec.event_id)
                rec.state = State.FAILED
                rec.last_error = "exceeded max submit attempts"
                self._store.upsert(rec)
                continue

            notable = json.loads(rec.raw_notable)
            title = notable.get("rule_title") or rec.rule_name
            description = notable.get("rule_description") or f"Splunk ES notable: {rec.rule_name}"

            try:
                # Send the schema on the first submission of each alert type so CZ
                # knows which fields contain observables; omit it on subsequent
                # submissions (CZ caches it). For auto-schema entries (None value in
                # schemas.py) get_schema returns None and no alertSchema is sent —
                # CZ will infer observables automatically.
                if rec.alert_type not in self._submitted_schemas:
                    schema = get_schema(rec.alert_type)
                    if schema is not None:
                        log.info("Sending alertSchema for type %s", rec.alert_type)
                    else:
                        log.info("Submitting type %s without schema (auto-schema)", rec.alert_type)
                else:
                    schema = None

                result = await self._cz.submit(
                    event_id=rec.event_id,
                    alert_type=rec.alert_type,
                    title=title,
                    description=description,
                    alert_data=notable,
                    schema=schema,
                )
                self._submitted_schemas.add(rec.alert_type)
                rec.investigation_id = result.investigation_id
                rec.cz_action = result.action
                rec.submitted_at = datetime.now(timezone.utc)
                rec.submit_attempts += 1
                rec.last_error = None
                rec.state = State.MERGED if result.action == "merged" else State.INVESTIGATING

                # For merged records, link this event_id to the existing investigation
                if result.action == "merged":
                    log.info("Notable %s merged into investigation %s", rec.event_id, result.investigation_id)

            except Exception as exc:
                rec.submit_attempts += 1
                rec.last_error = str(exc)
                log.warning("Submit failed for %s (attempt %d): %s", rec.event_id, rec.submit_attempts, exc)

            self._store.upsert(rec)

            if self._cfg.cz_submit_delay > 0:
                await asyncio.sleep(self._cfg.cz_submit_delay)

    # ------------------------------------------------------------------
    # Step 3: poll CZ for verdict-ready investigations
    # ------------------------------------------------------------------

    def _due_for_poll(self, rec: Record) -> bool:
        """Return True if enough time has passed since the last CZ poll for this record."""
        if rec.last_polled_at is None:
            return True
        wait = min(
            self._cfg.cz_poll_interval * (2 ** rec.poll_attempts),
            self._cfg.cz_poll_max_backoff,
        )
        elapsed = (datetime.now(timezone.utc) - rec.last_polled_at).total_seconds()
        return elapsed >= wait

    async def _poll_cz(self) -> None:
        pending = self._store.pending_verdict()
        if not pending:
            return

        # Give up on investigations that have been polling too long without a
        # verdict, so they reach a terminal state instead of polling forever.
        now = datetime.now(timezone.utc)
        live = []
        for rec in pending:
            started = rec.submitted_at or rec.discovered_at
            if started and (now - started).total_seconds() >= MAX_POLL_AGE_SECONDS:
                rec.state = State.FAILED
                rec.last_error = f"no verdict after {MAX_POLL_AGE_SECONDS}s; giving up"
                self._store.upsert(rec)
                log.error("Investigation for notable %s exceeded max poll age, marking failed", rec.event_id)
            else:
                live.append(rec)

        due = [r for r in live if self._due_for_poll(r)]
        if not due:
            return

        inv_ids = list({r.investigation_id for r in due if r.investigation_id})
        verdicts = await self._cz.poll_pending(inv_ids)

        for vr in verdicts:
            if vr.is_ready:
                affected = self._store.get_by_investigation(vr.investigation_id)
                for rec in affected:
                    if rec.state not in (State.INVESTIGATING, State.MERGED):
                        continue
                    rec.state = State.VERDICT_READY
                    rec.verdict = ", ".join(vr.verdict)
                    rec.confidence = vr.confidence
                    rec.severity = vr.severity
                    rec.summary = vr.summary
                    rec.console_url = vr.console_url
                    rec.cz_status = vr.status
                    rec.category = vr.category
                    rec.impact = vr.impact
                    rec.description = vr.description
                    rec.verdict_at = datetime.now(timezone.utc)
                    self._store.upsert(rec)
                    log.info("Verdict ready for notable %s: %s", rec.event_id, rec.verdict)

            elif vr.is_failed:
                affected = self._store.get_by_investigation(vr.investigation_id)
                for rec in affected:
                    rec.state = State.FAILED
                    rec.last_error = "CZ investigation failed"
                    self._store.upsert(rec)
                    log.warning("Investigation %s failed for notable %s", vr.investigation_id, rec.event_id)

            else:
                # Still investigating — bump poll attempt counter and record when we last checked
                affected = self._store.get_by_investigation(vr.investigation_id)
                for rec in affected:
                    rec.poll_attempts += 1
                    rec.last_polled_at = datetime.now(timezone.utc)
                    self._store.upsert(rec)

    # ------------------------------------------------------------------
    # Step 4: write back to Splunk for verdict-ready notables
    # ------------------------------------------------------------------

    async def _writeback_ready(self) -> None:
        pending = self._store.pending_writeback()

        for rec in pending:
            if rec.writeback_attempts >= MAX_WRITEBACK_ATTEMPTS:
                log.error("Notable %s exceeded max writeback attempts", rec.event_id)
                rec.state = State.FAILED
                rec.last_error = "exceeded max writeback attempts"
                self._store.upsert(rec)
                continue

            try:
                # Step 4a: post the analyst-visible comment. Skipped when
                # splunk_es_writeback=False (no ES licence). notable_update is not
                # idempotent (each call appends a comment), so the moment it succeeds
                # we persist COMMENT_DONE. A later HEC failure then resumes at step 4b
                # and never re-posts the comment.
                if rec.state == State.VERDICT_READY:
                    if self._cfg.splunk_es_writeback:
                        await self._splunk.write_verdict(
                            event_id=rec.event_id,
                            rule_uid=rec.event_id,  # event_id doubles as the ruleUID target
                            verdict=rec.verdict or "",
                            confidence=rec.confidence,
                            severity=rec.severity,
                            summary=rec.summary,
                            console_url=rec.console_url,
                            investigation_id=rec.investigation_id or "",
                            category=rec.category,
                            impact=rec.impact,
                            description=rec.description,
                        )
                    rec.state = State.COMMENT_DONE
                    rec.last_error = None
                    self._store.upsert(rec)

                # Step 4b: structured enrichment event (no-op if HEC not configured).
                await self._splunk.send_enrichment_event(
                    event_id=rec.event_id,
                    investigation_id=rec.investigation_id or "",
                    verdict=rec.verdict,
                    confidence=rec.confidence,
                    severity=rec.severity,
                    status=rec.cz_status or "pending-review",
                    console_url=rec.console_url,
                    enrichment_index=self._cfg.enrichment_index,
                    category=rec.category,
                    impact=rec.impact,
                    description=rec.description,
                )
                rec.state = State.WRITTEN_BACK
                rec.written_back_at = datetime.now(timezone.utc)
                rec.writeback_attempts += 1
                rec.last_error = None
                log.info("Writeback complete for notable %s", rec.event_id)

            except Exception as exc:
                rec.writeback_attempts += 1
                rec.last_error = str(exc)
                log.warning("Writeback failed for %s (attempt %d): %s", rec.event_id, rec.writeback_attempts, exc)

            self._store.upsert(rec)

    async def close(self) -> None:
        await self._splunk.close()
        await self._cz.close()
        self._store.close()


# ------------------------------------------------------------------
# Entrypoint
# ------------------------------------------------------------------

async def preflight(cfg: Config) -> None:
    """
    Fast-fail startup check. Validates that required config fields aren't placeholders,
    then verifies connectivity and auth for both Splunk REST and the CZ API.
    Raises SystemExit(1) on any failure so the process exits cleanly without a traceback.
    """
    required = [
        ("CZ_ORG_ID", cfg.cz_org_id),
        ("CZ_BEARER_TOKEN", cfg.cz_bearer_token),
        ("SPLUNK_REST_URL", cfg.splunk_rest_url),
        ("SPLUNK_SVC_TOKEN", cfg.splunk_svc_token),
    ]
    bad = [name for name, val in required if not val or val.startswith("<")]
    if bad:
        for name in bad:
            log.error("Preflight: %s is not configured — edit .env and try again", name)
        raise SystemExit(1)

    splunk = SplunkClient(cfg)
    cz = CZClient(cfg)
    try:
        log.info("Preflight: checking Splunk REST (%s)...", cfg.splunk_rest_url)
        await splunk.health_check()
        log.info("Preflight: Splunk OK")

        log.info("Preflight: checking CZ API (org=%s)...", cfg.cz_org_id)
        await cz.health_check()
        log.info("Preflight: CZ API OK")
    except RuntimeError as exc:
        log.error("Preflight failed: %s", exc)
        raise SystemExit(1) from exc
    finally:
        await splunk.close()
        await cz.close()

    log.info("Preflight complete — starting connector")


async def _run() -> None:
    cfg = Config()
    await preflight(cfg)
    connector = Connector(cfg)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, connector.stop)

    try:
        await connector.run()
    finally:
        await connector.close()
        log.info("Connector shut down cleanly")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
