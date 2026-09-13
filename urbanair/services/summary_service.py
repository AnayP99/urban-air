"""High-level service that orchestrates AQI + weather fetch and caching."""
from __future__ import annotations

from urbanair.cache.cache_manager import InMemoryTTLCache
from urbanair.cities import CityConfig
from urbanair.config import Settings
from urbanair.models.response_models import DailySummary
from urbanair.services.activity_service import ActivityService
from urbanair.services.aqi_service import AQIService
from urbanair.services.insight_service import InsightService
from urbanair.services.scoring_service import ScoringService
from urbanair.services.weather_service import WeatherService


class SummaryService:
    """Fetches, merges, and caches the DailySummary for a given city."""

    def __init__(self, settings: Settings, cache: InMemoryTTLCache) -> None:
        self.settings = settings
        self.cache = cache
        self._scoring = ScoringService()

    async def get_daily_summary(self, city: CityConfig) -> DailySummary:
        """Return the cached DailySummary for *city*, fetching fresh data if needed."""
        cache_key = f"summary:{city.slug}"
        cached: DailySummary | None = self.cache.get(cache_key)
        if cached is not None:
            return cached

        insight_service = InsightService(
            settings=self.settings,
            aqi_service=AQIService(self.settings),
            weather_service=WeatherService(self.settings),
            scoring_service=self._scoring,
            activity_service=ActivityService(),
        )
        summary = await insight_service.build_daily_summary(
            city_name=city.name,
            city_slug=city.slug,
            lat=city.lat,
            lon=city.lon,
        )
        self.cache.set(cache_key, summary)
        return summary
