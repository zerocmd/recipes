"""
SQLite-backed correlation store.

One row per discovered notable. Tracks the full lifecycle from discovery
through CZ submission, verdict receipt, and writeback.
"""

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class State(str, Enum):
    DISCOVERED = "discovered"
    NO_SCHEMA = "no_schema"         # alert type has no mapped schema; submission skipped
    INVESTIGATING = "investigating"
    MERGED = "merged"
    VERDICT_READY = "verdict_ready"
    COMMENT_DONE = "comment_done"   # notable_update comment posted; HEC event still pending
    WRITTEN_BACK = "written_back"
    FAILED = "failed"


@dataclass
class Record:
    event_id: str
    rule_name: str
    alert_type: str           # SplunkES:<correlation_search_name>
    raw_notable: str          # JSON blob of the original notable fields
    state: State = State.DISCOVERED
    investigation_id: Optional[str] = None
    cz_action: Optional[str] = None          # "created" | "merged"
    cz_status: Optional[str] = None          # CZ status at verdict capture (pending-review|in-progress|...)
    verdict: Optional[str] = None
    confidence: Optional[str] = None
    severity: Optional[str] = None
    summary: Optional[str] = None
    console_url: Optional[str] = None
    category: Optional[str] = None
    impact: Optional[str] = None
    description: Optional[str] = None
    submit_attempts: int = 0
    poll_attempts: int = 0
    writeback_attempts: int = 0
    last_error: Optional[str] = None
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    submitted_at: Optional[datetime] = None
    verdict_at: Optional[datetime] = None
    written_back_at: Optional[datetime] = None
    last_polled_at: Optional[datetime] = None


_SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    event_id            TEXT PRIMARY KEY,
    rule_name           TEXT NOT NULL,
    alert_type          TEXT NOT NULL,
    raw_notable         TEXT NOT NULL,
    state               TEXT NOT NULL DEFAULT 'discovered',
    investigation_id    TEXT,
    cz_action           TEXT,
    cz_status           TEXT,
    verdict             TEXT,
    confidence          TEXT,
    severity            TEXT,
    summary             TEXT,
    console_url         TEXT,
    category            TEXT,
    impact              TEXT,
    description         TEXT,
    submit_attempts     INTEGER NOT NULL DEFAULT 0,
    poll_attempts       INTEGER NOT NULL DEFAULT 0,
    writeback_attempts  INTEGER NOT NULL DEFAULT 0,
    last_error          TEXT,
    discovered_at       TEXT NOT NULL,
    submitted_at        TEXT,
    verdict_at          TEXT,
    written_back_at     TEXT,
    last_polled_at      TEXT
);

CREATE TABLE IF NOT EXISTS checkpoint (
    index_name  TEXT PRIMARY KEY,
    last_time   TEXT NOT NULL   -- ISO-8601 UTC; watermark for the Splunk poll
);
"""


class Store:
    def __init__(self, db_path: str):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        # Migrate existing databases that predate these columns.
        for col in ("last_polled_at TEXT", "cz_status TEXT",
                    "category TEXT", "impact TEXT", "description TEXT"):
            try:
                self._conn.execute(f"ALTER TABLE records ADD COLUMN {col}")
            except sqlite3.OperationalError:
                pass  # column already exists
        # Rename legacy state value.
        self._conn.execute(
            "UPDATE records SET state = 'verdict_ready' WHERE state = 'pending_review'"
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Records
    # ------------------------------------------------------------------

    def upsert(self, rec: Record) -> None:
        self._conn.execute(
            """
            INSERT INTO records (
                event_id, rule_name, alert_type, raw_notable, state,
                investigation_id, cz_action, cz_status, verdict, confidence, severity,
                summary, console_url, category, impact, description,
                submit_attempts, poll_attempts,
                writeback_attempts, last_error, discovered_at, submitted_at,
                verdict_at, written_back_at, last_polled_at
            ) VALUES (
                :event_id, :rule_name, :alert_type, :raw_notable, :state,
                :investigation_id, :cz_action, :cz_status, :verdict, :confidence, :severity,
                :summary, :console_url, :category, :impact, :description,
                :submit_attempts, :poll_attempts,
                :writeback_attempts, :last_error, :discovered_at, :submitted_at,
                :verdict_at, :written_back_at, :last_polled_at
            )
            ON CONFLICT(event_id) DO UPDATE SET
                state              = excluded.state,
                investigation_id   = excluded.investigation_id,
                cz_action          = excluded.cz_action,
                cz_status          = excluded.cz_status,
                verdict            = excluded.verdict,
                confidence         = excluded.confidence,
                severity           = excluded.severity,
                summary            = excluded.summary,
                console_url        = excluded.console_url,
                category           = excluded.category,
                impact             = excluded.impact,
                description        = excluded.description,
                submit_attempts    = excluded.submit_attempts,
                poll_attempts      = excluded.poll_attempts,
                writeback_attempts = excluded.writeback_attempts,
                last_error         = excluded.last_error,
                submitted_at       = excluded.submitted_at,
                verdict_at         = excluded.verdict_at,
                written_back_at    = excluded.written_back_at,
                last_polled_at     = excluded.last_polled_at
            """,
            _record_to_row(rec),
        )
        self._conn.commit()

    def get(self, event_id: str) -> Optional[Record]:
        row = self._conn.execute(
            "SELECT * FROM records WHERE event_id = ?", (event_id,)
        ).fetchone()
        return _row_to_record(row) if row else None

    def get_by_investigation(self, investigation_id: str) -> list[Record]:
        rows = self._conn.execute(
            "SELECT * FROM records WHERE investigation_id = ?", (investigation_id,)
        ).fetchall()
        return [_row_to_record(r) for r in rows]

    def pending_submission(self) -> list[Record]:
        rows = self._conn.execute(
            "SELECT * FROM records WHERE state = ?", (State.DISCOVERED.value,)
        ).fetchall()
        return [_row_to_record(r) for r in rows]

    def pending_verdict(self) -> list[Record]:
        rows = self._conn.execute(
            """SELECT * FROM records
               WHERE state IN (?, ?)""",
            (State.INVESTIGATING.value, State.MERGED.value),
        ).fetchall()
        return [_row_to_record(r) for r in rows]

    def pending_writeback(self) -> list[Record]:
        rows = self._conn.execute(
            "SELECT * FROM records WHERE state IN (?, ?)",
            (State.VERDICT_READY.value, State.COMMENT_DONE.value),
        ).fetchall()
        return [_row_to_record(r) for r in rows]

    # ------------------------------------------------------------------
    # Checkpoint
    # ------------------------------------------------------------------

    def get_checkpoint(self, index_name: str) -> Optional[str]:
        row = self._conn.execute(
            "SELECT last_time FROM checkpoint WHERE index_name = ?", (index_name,)
        ).fetchone()
        return row["last_time"] if row else None

    def set_checkpoint(self, index_name: str, last_time: str) -> None:
        self._conn.execute(
            """INSERT INTO checkpoint (index_name, last_time) VALUES (?, ?)
               ON CONFLICT(index_name) DO UPDATE SET last_time = excluded.last_time""",
            (index_name, last_time),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


# ------------------------------------------------------------------
# Row ↔ Record helpers
# ------------------------------------------------------------------

def _dt(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _record_to_row(rec: Record) -> dict:
    return {
        "event_id": rec.event_id,
        "rule_name": rec.rule_name,
        "alert_type": rec.alert_type,
        "raw_notable": rec.raw_notable,
        "state": rec.state.value,
        "investigation_id": rec.investigation_id,
        "cz_action": rec.cz_action,
        "cz_status": rec.cz_status,
        "verdict": rec.verdict,
        "confidence": rec.confidence,
        "severity": rec.severity,
        "summary": rec.summary,
        "console_url": rec.console_url,
        "category": rec.category,
        "impact": rec.impact,
        "description": rec.description,
        "submit_attempts": rec.submit_attempts,
        "poll_attempts": rec.poll_attempts,
        "writeback_attempts": rec.writeback_attempts,
        "last_error": rec.last_error,
        "discovered_at": rec.discovered_at.isoformat(),
        "submitted_at": rec.submitted_at.isoformat() if rec.submitted_at else None,
        "verdict_at": rec.verdict_at.isoformat() if rec.verdict_at else None,
        "written_back_at": rec.written_back_at.isoformat() if rec.written_back_at else None,
        "last_polled_at": rec.last_polled_at.isoformat() if rec.last_polled_at else None,
    }


def _row_to_record(row: sqlite3.Row) -> Record:
    return Record(
        event_id=row["event_id"],
        rule_name=row["rule_name"],
        alert_type=row["alert_type"],
        raw_notable=row["raw_notable"],
        state=State(row["state"]),
        investigation_id=row["investigation_id"],
        cz_action=row["cz_action"],
        cz_status=row["cz_status"],
        verdict=row["verdict"],
        confidence=row["confidence"],
        severity=row["severity"],
        summary=row["summary"],
        console_url=row["console_url"],
        category=row["category"],
        impact=row["impact"],
        description=row["description"],
        submit_attempts=row["submit_attempts"],
        poll_attempts=row["poll_attempts"],
        writeback_attempts=row["writeback_attempts"],
        last_error=row["last_error"],
        discovered_at=_dt(row["discovered_at"]),
        submitted_at=_dt(row["submitted_at"]),
        verdict_at=_dt(row["verdict_at"]),
        written_back_at=_dt(row["written_back_at"]),
        last_polled_at=_dt(row["last_polled_at"]),
    )
