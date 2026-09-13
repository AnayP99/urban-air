"""SQLite-backed persistence layer for analytics events and waitlist entries."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from collections.abc import Generator
from pathlib import Path
from typing import Any


class Storage:
    """Thin wrapper around a SQLite database.

    Enables WAL journal mode for better read concurrency, creates the schema
    on first use, and provides context-managed sessions to prevent connection leaks.
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def connect(self) -> sqlite3.Connection:
        """Open and return a new SQLite connection with Row factory."""
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        # WAL mode gives better read concurrency for a web app.
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    @contextmanager
    def session(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager that commits on exit and closes the connection cleanly."""
        conn = self.connect()
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Create tables and indexes if they do not already exist."""
        with self.session() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS analytics_events (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_name TEXT    NOT NULL,
                    city_slug  TEXT,
                    created_at TEXT    NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_analytics_city
                    ON analytics_events(city_slug);
                CREATE INDEX IF NOT EXISTS idx_analytics_created
                    ON analytics_events(created_at);

                CREATE TABLE IF NOT EXISTS waitlist_entries (
                    email      TEXT PRIMARY KEY,
                    city_slug  TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_waitlist_city
                    ON waitlist_entries(city_slug);
            """)

    def execute_many(self, sql: str, params_seq: list[tuple[Any, ...]]) -> None:
        """Execute *sql* for each parameter tuple in *params_seq* in one transaction."""
        with self.session() as conn:
            conn.executemany(sql, params_seq)
