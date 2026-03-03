from __future__ import annotations

import asyncio
from datetime import datetime

from urbanair.config import Settings
from urbanair.models.response_models import DailySummary, HourlyPoint
from urbanair.services.aqi_service import AQIService
from urbanair.services.scoring_service import ScoringService
from urbanair.services.weather_service import WeatherService


class InsightService:
    def __init__(
        self,
        settings: Settings,
        aqi_service: AQIService,
        weather_service: WeatherService,
        scoring_service: ScoringService,
    ) -> None:
        self.settings = settings
        self.aqi_service = aqi_service
        self.weather_service = weather_service
        self.scoring_service = scoring_service

    async def build_daily_summary(
        self,
        city_name: str,
        city_slug: str,
        lat: float,
        lon: float,
    ) -> DailySummary:
        aqi_series, weather_series = await self._fetch_sources(city_slug, lat, lon)
        merged = self._merge_hourly(aqi_series, weather_series)

        best_window, worst_window = self.scoring_service.compute_windows(merged)
        current_aqi = merged[0].aqi if merged else 0.0
        insight_text = self.generate_urban_insight(merged[0]) if merged else "Data unavailable."

        tz = self.settings.tz()
        return DailySummary(
            city=city_name,
            generated_at=datetime.now(tz=tz),
            current_aqi=current_aqi,
            timeline=merged,
            best_window=best_window,
            worst_window=worst_window,
            insight=insight_text,
        )

    async def _fetch_sources(self, city_slug: str, lat: float, lon: float) -> tuple[list[dict], list[dict]]:
        aqi_series, weather_series = await asyncio.gather(
            self.aqi_service.fetch_hourly_aqi(city_slug),
            self.weather_service.fetch_hourly_weather(lat, lon),
        )
        return aqi_series, weather_series

    def _merge_hourly(self, aqi_series: list[dict], weather_series: list[dict]) -> list[HourlyPoint]:
        weather_map = {w["time"].replace(minute=0, second=0, microsecond=0): w for w in weather_series}

        merged: list[HourlyPoint] = []
        for aqi_item in aqi_series:
            at = aqi_item["time"].replace(minute=0, second=0, microsecond=0)
            weather_item = weather_map.get(at)
            if not weather_item:
                continue
            temp = weather_item["temperature"]
            humidity = weather_item["humidity"]
            score = self.scoring_service.combined_score(
                aqi=aqi_item["aqi"],
                temp_c=temp,
                humidity=humidity,
            )
            merged.append(
                HourlyPoint(
                    time=at,
                    aqi=round(float(aqi_item["aqi"]), 1),
                    temperature=round(float(temp), 1),
                    humidity=round(float(humidity), 1),
                    score=score,
                )
            )

        merged.sort(key=lambda x: x.time)
        return merged[:24]

    def generate_urban_insight(self, hour: HourlyPoint) -> str:
        aqi_note = self._aqi_label(hour.aqi)
        temp_note = self._temp_label(hour.temperature)
        humidity_note = self._humidity_label(hour.humidity)
        return (
            f"Air quality is {aqi_note} right now. Temperature is {temp_note}, and humidity is {humidity_note}. "
            "Use the green time window for walks or errands, and avoid the red window when possible."
        )

    @staticmethod
    def _aqi_label(aqi: float) -> str:
        if aqi <= 50:
            return "healthy"
        if aqi <= 100:
            return "moderate"
        if aqi <= 150:
            return "unhealthy for sensitive groups"
        if aqi <= 200:
            return "unhealthy"
        return "very unhealthy"

    @staticmethod
    def _temp_label(temp_c: float) -> str:
        if temp_c < 20:
            return "cool temperatures"
        if temp_c <= 30:
            return "comfortable temperatures"
        if temp_c <= 35:
            return "warm conditions"
        return "high heat"

    @staticmethod
    def _humidity_label(humidity: float) -> str:
        if humidity < 35:
            return "dry air"
        if humidity <= 65:
            return "balanced humidity"
        return "sticky humidity"
