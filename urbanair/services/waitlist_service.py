from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from urbanair.storage import Storage


@dataclass
class WaitlistEntry:
    email: str
    city_slug: str
    created_at: datetime


class WaitlistService:
    def __init__(self, storage: Storage) -> None:
        self.storage = storage

    def add(self, email: str, city_slug: str) -> WaitlistEntry:
        key = email.strip().lower()
        normalized_city = city_slug.strip().lower()
        created_at = datetime.now(tz=timezone.utc)
        with self.storage.connect() as connection:
            connection.execute(
                """
                INSERT INTO waitlist_entries (email, city_slug, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(email) DO UPDATE SET
                    city_slug = excluded.city_slug,
                    created_at = excluded.created_at
                """,
                (key, normalized_city, created_at.isoformat()),
            )
        return WaitlistEntry(email=key, city_slug=normalized_city, created_at=created_at)

    def count(self) -> int:
        with self.storage.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM waitlist_entries"
            ).fetchone()
        return int(row["count"])
