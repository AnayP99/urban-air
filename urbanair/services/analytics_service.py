from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from urbanair.storage import Storage


@dataclass
class AnalyticsSnapshot:
    total_events: int
    event_counts: dict[str, int]
    top_cities: list[tuple[str, int]]


class AnalyticsService:
    def __init__(self, storage: Storage) -> None:
        self.storage = storage

    def track(self, event_name: str, city_slug: str | None = None) -> None:
        normalized = event_name.strip().lower() or "unknown"
        normalized_city = city_slug.strip().lower() if city_slug else None
        created_at = datetime.now(tz=timezone.utc).isoformat()
        with self.storage.connect() as connection:
            connection.execute(
                """
                INSERT INTO analytics_events (event_name, city_slug, created_at)
                VALUES (?, ?, ?)
                """,
                (normalized, normalized_city, created_at),
            )

    def snapshot(self) -> AnalyticsSnapshot:
        with self.storage.connect() as connection:
            total_events = connection.execute(
                "SELECT COUNT(*) AS count FROM analytics_events"
            ).fetchone()["count"]
            event_rows = connection.execute(
                """
                SELECT event_name, COUNT(*) AS count
                FROM analytics_events
                GROUP BY event_name
                ORDER BY count DESC, event_name ASC
                """
            ).fetchall()
            city_rows = connection.execute(
                """
                SELECT city_slug, COUNT(*) AS count
                FROM analytics_events
                WHERE city_slug IS NOT NULL AND city_slug != ''
                GROUP BY city_slug
                ORDER BY count DESC, city_slug ASC
                LIMIT 5
                """
            ).fetchall()

        return AnalyticsSnapshot(
            total_events=int(total_events),
            event_counts={row["event_name"]: int(row["count"]) for row in event_rows},
            top_cities=[(row["city_slug"], int(row["count"])) for row in city_rows],
        )
