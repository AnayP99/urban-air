from __future__ import annotations

import asyncio
from datetime import datetime

from urbanair.config import Settings
from urbanair.models.response_models import DailySummary, HourlyPoint
from urbanair.services.activity_service import ActivityService
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
        activity_service: ActivityService,
    ) -> None:
        self.settings = settings
        self.aqi_service = aqi_service
        self.weather_service = weather_service
        self.scoring_service = scoring_service
        self.activity_service = activity_service

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
        current_outdoor_score = merged[0].outdoor_score if merged else 0.0
        insight_text = self.generate_urban_insight(merged) if merged else "Data unavailable."
        activities = (
            self.activity_service.generate(
                aqi=merged[0].aqi,
                outdoor_score=merged[0].outdoor_score,
                temperature=merged[0].temperature,
                humidity=merged[0].humidity,
            )
            if merged
            else []
        )

        tz = self.settings.tz()
        return DailySummary(
            city=city_name,
            generated_at=datetime.now(tz=tz),
            current_aqi=current_aqi,
            current_outdoor_score=current_outdoor_score,
            timeline=merged,
            best_window=best_window,
            worst_window=worst_window,
            insight=insight_text,
            activities=activities,
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
            outdoor_score = self.scoring_service.outdoor_score(score)
            merged.append(
                HourlyPoint(
                    time=at,
                    aqi=round(float(aqi_item["aqi"]), 1),
                    temperature=round(float(temp), 1),
                    humidity=round(float(humidity), 1),
                    wind_speed=round(float(weather_item.get("wind_speed", 0.0)), 1),
                    score=score,
                    outdoor_score=outdoor_score,
                )
            )

        merged.sort(key=lambda x: x.time)
        return merged[:24]

    def generate_urban_insight(self, timeline: list[HourlyPoint]) -> str:
        current = timeline[0]
        aqi_note = self._aqi_label(current.aqi)
        temp_note = self._temp_label(current.temperature)
        humidity_note = self._humidity_label(current.humidity)
        trend_note = self._aqi_trend_note(timeline)
        trap_note = self._humidity_trap_note(current.humidity, current.aqi)
        heat_note = self._heat_note(current.temperature)
        wind_note = self._wind_note(current.wind_speed, current.aqi)

        notes = [
            f"Air quality is {aqi_note} right now.",
            trend_note,
            temp_note,
            humidity_note,
            trap_note,
            heat_note,
            wind_note,
        ]
        return " ".join(note for note in notes if note)

    def _aqi_trend_note(self, timeline: list[HourlyPoint]) -> str:
        if len(timeline) < 4:
            return ""
        future_avg = sum(point.aqi for point in timeline[1:4]) / 3
        current = timeline[0].aqi
        if future_avg >= current + 15:
            return "Air pollution looks likely to rise over the next few hours."
        if future_avg <= current - 15:
            return "Air quality should improve over the next few hours."
        return "Conditions look fairly steady through the near term."

    def _humidity_trap_note(self, humidity: float, aqi: float) -> str:
        if humidity >= 75 and aqi >= 100:
            return "High humidity may trap pollutants close to the ground."
        return ""

    def _heat_note(self, temperature: float) -> str:
        if temperature >= 34:
            return "Heat will make outdoor time feel more tiring than the air number alone suggests."
        if temperature <= 22:
            return "Cooler temperatures should make short outdoor activity easier."
        return ""

    def _wind_note(self, wind_speed: float, aqi: float) -> str:
        if wind_speed >= 5 and aqi >= 80:
            return "Breezier air may help disperse pollution later."
        if wind_speed <= 1.5 and aqi >= 100:
            return "Light wind means pollution can linger for longer."
        return ""

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
            return "Temperatures are on the cooler side."
        if temp_c <= 30:
            return "Temperatures are comfortable."
        if temp_c <= 35:
            return "It will feel warm outside."
        return "High temperatures will add stress outdoors."

    @staticmethod
    def _humidity_label(humidity: float) -> str:
        if humidity < 35:
            return "Humidity is relatively low."
        if humidity <= 65:
            return "Humidity is in a manageable range."
        return "Humidity is high and may feel sticky."
