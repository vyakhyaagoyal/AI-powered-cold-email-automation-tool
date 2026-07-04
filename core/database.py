"""
SQLite logging layer.

Kept as a small synchronous wrapper (sqlite3 is not truly async-friendly)
and called from async code via `asyncio.to_thread` where needed. CLI
commands like `list`/`view`/`stats` call it directly since they're one-shot.
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS email_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    website TEXT,
    recipient TEXT NOT NULL,
    subject TEXT,
    body TEXT,
    time_sent TEXT,
    status TEXT NOT NULL,
    error TEXT
);
"""


class Database:
    """Synchronous SQLite wrapper for storing and querying email logs."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_schema()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self):
        with self._connect() as conn:
            conn.execute(SCHEMA)

    def insert_log(self, company_name: str, website: str, recipient: str, subject: str,
                    body: str, status: str, error: str = "") -> int:
        """Insert a new log row and return its id."""
        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO email_logs
                   (company_name, website, recipient, subject, body, time_sent, status, error)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (company_name, website, recipient, subject, body,
                 datetime.now(timezone.utc).isoformat(), status, error),
            )
            return cursor.lastrowid

    def update_log(self, log_id: int, status: str, error: str = "") -> None:
        """Update status/error/time_sent for an existing log row (used by resend)."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE email_logs SET status = ?, error = ?, time_sent = ? WHERE id = ?",
                (status, error, datetime.now(timezone.utc).isoformat(), log_id),
            )

    def get_log(self, log_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM email_logs WHERE id = ?", (log_id,)).fetchone()
            return dict(row) if row else None

    def list_logs(self, limit: int = 50) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM email_logs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def stats(self) -> dict:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) c FROM email_logs").fetchone()["c"]
            sent = conn.execute("SELECT COUNT(*) c FROM email_logs WHERE status='sent'").fetchone()["c"]
            failed = conn.execute("SELECT COUNT(*) c FROM email_logs WHERE status='failed'").fetchone()["c"]
            by_company = conn.execute(
                "SELECT company_name, COUNT(*) c FROM email_logs GROUP BY company_name ORDER BY c DESC"
            ).fetchall()
            return {
                "total": total,
                "sent": sent,
                "failed": failed,
                "success_rate": round((sent / total * 100), 1) if total else 0.0,
                "by_company": [dict(r) for r in by_company],
            }
