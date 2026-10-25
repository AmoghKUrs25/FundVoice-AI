
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "fundvoice_audit.db"
)


class AuditRepository:
    """Persist and retrieve FundVoice AI audit events using SQLite."""

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
    ) -> None:
        self.db_path = Path(db_path)

        if str(db_path) != ":memory:":
            self.db_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

        self._initialize_database()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def _initialize_database(self) -> None:
        """Create the audit table if it does not exist."""

        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    details_json TEXT NOT NULL
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_audit_events_run_id
                ON audit_events(run_id, id)
                """
            )

    def record_event(
        self,
        run_id: str,
        event: dict[str, Any],
    ) -> int:
        """Save one event and return its database ID."""

        if not run_id.strip():
            raise ValueError("run_id must not be empty.")

        event_type = event.get("event_type")
        if not isinstance(event_type, str) or not event_type.strip():
            raise ValueError("event_type must not be empty.")

        timestamp = event.get("timestamp")
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat()
        elif isinstance(timestamp, datetime):
            timestamp = timestamp.isoformat()

        details = event.get("details", {})

        details_json = json.dumps(
            details,
            ensure_ascii=False,
            default=str,
        )

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO audit_events (
                    run_id,
                    event_type,
                    timestamp,
                    details_json
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    run_id,
                    event_type,
                    str(timestamp),
                    details_json,
                ),
            )

            return int(cursor.lastrowid)

    def record_events(
        self,
        run_id: str,
        events: list[dict[str, Any]],
    ) -> list[int]:
        """Save multiple events in their supplied order."""

        if not run_id.strip():
            raise ValueError("run_id must not be empty.")

        event_ids = []

        with self._connect() as connection:
            for event in events:
                event_type = event.get("event_type")

                if (
                    not isinstance(event_type, str)
                    or not event_type.strip()
                ):
                    raise ValueError(
                        "Every event must have a non-empty event_type."
                    )

                timestamp = event.get("timestamp")
                if timestamp is None:
                    timestamp = datetime.now(timezone.utc).isoformat()
                elif isinstance(timestamp, datetime):
                    timestamp = timestamp.isoformat()

                details_json = json.dumps(
                    event.get("details", {}),
                    ensure_ascii=False,
                    default=str,
                )

                cursor = connection.execute(
                    """
                    INSERT INTO audit_events (
                        run_id,
                        event_type,
                        timestamp,
                        details_json
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        event_type,
                        str(timestamp),
                        details_json,
                    ),
                )

                event_ids.append(int(cursor.lastrowid))

        return event_ids
    
    def record_verification(
        self,
        run_id: str,
        portfolio_id: str,
        verification_status: str,
        checks_passed: list[str],
        issues: list[dict[str, Any]],
        nav_evidence: list[dict[str, Any]],
    ) -> int:
        """
        Record a portfolio verification result and its NAV evidence.

        The supplied evidence metadata is preserved for traceability.
        This records the verification outcome; it does not independently
        authenticate the NAV source.
        """

        if not portfolio_id.strip():
            raise ValueError("portfolio_id must not be empty.")

        if not verification_status.strip():
            raise ValueError("verification_status must not be empty.")

        return self.record_event(
            run_id=run_id,
            event={
                "event_type": "PORTFOLIO_VERIFICATION",
                "timestamp": datetime.now(timezone.utc),
                "details": {
                    "portfolio_id": portfolio_id,
                    "verification_status": verification_status,
                    "checks_passed": checks_passed,
                    "issues": issues,
                    "nav_evidence": nav_evidence,
                },
            },
        )


    def get_events(
        self,
        run_id: str,
    ) -> list[dict[str, Any]]:
        """Return all audit events for one run, in insertion order."""

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, run_id, event_type, timestamp, details_json
                FROM audit_events
                WHERE run_id = ?
                ORDER BY id
                """,
                (run_id,),
            ).fetchall()

        return [
            {
                "id": row[0],
                "run_id": row[1],
                "event_type": row[2],
                "timestamp": row[3],
                "details": json.loads(row[4]),
            }
            for row in rows
        ]

    def get_all_events(self) -> list[dict[str, Any]]:
        """Return all audit events, in insertion order."""

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, run_id, event_type, timestamp, details_json
                FROM audit_events
                ORDER BY id
                """
            ).fetchall()

        return [
            {
                "id": row[0],
                "run_id": row[1],
                "event_type": row[2],
                "timestamp": row[3],
                "details": json.loads(row[4]),
            }
            for row in rows
        ]