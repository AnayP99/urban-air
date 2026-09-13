"""Rule-based urban air quality insight text generation."""
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
    """Builds a DailySummary by fetching data and generating insights."""

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
        aqi_series, weather_series = await asyncio.gather(
            self.aqi_service.fetch_hourly_aqi(city_slug, lat=lat, lon=lon),
            self.weather_service.fetch_hourly_weather(lat, lon),
        )
        merged = self._merge_hourly(aqi_series, weather_series)

        best_window, worst_window = self.scoring_service.compute_windows(merged)
        current = merged[0] if merged else None

        insight_text = self.generate_insight(merged) if merged else "Data unavailable."
        activities = (
            self.activity_service.generate(
                aqi=current.aqi,
                outdoor_score=current.outdoor_score,
                temperature=current.temperature,
                humidity=current.humidity,
                wind_speed=current.wind_speed,
            )
            if current
            else []
        )

        tz = self.settings.tz()
        return DailySummary(
            city=city_name,
            generated_at=datetime.now(tz=tz),
            current_aqi=current.aqi if current else 0.0,
            current_outdoor_score=current.outdoor_score if current else 0.0,
            current_temperature=current.temperature if current else 0.0,
            current_humidity=current.humidity if current else 0.0,
            current_wind_speed=current.wind_speed if current else 0.0,
            timeline=merged,
            best_window=best_window,
            worst_window=worst_window,
            insight=insight_text,
            activities=activities,
        )

    def _merge_hourly(
        self, aqi_series: list[dict], weather_series: list[dict]
    ) -> list[HourlyPoint]:
        """Merge AQI and weather series on the hour timestamp."""
        weather_map = {
            w["time"].replace(minute=0, second=0, microsecond=0): w
            for w in weather_series
        }

        merged: list[HourlyPoint] = []
        for aqi_item in aqi_series:
            at = aqi_item["time"].replace(minute=0, second=0, microsecond=0)
            wx = weather_map.get(at)
            if not wx:
                continue
            temp = wx["temperature"]
            humidity = wx["humidity"]
            wind_speed = wx.get("wind_speed", 0.0)
            score = self.scoring_service.combined_score(
                aqi=aqi_item["aqi"],
                temp_c=temp,
                humidity=humidity,
                wind_speed_ms=wind_speed,
            )
            merged.append(
                HourlyPoint(
                    time=at,
                    aqi=round(float(aqi_item["aqi"]), 1),
                    temperature=round(float(temp), 1),
                    humidity=round(float(humidity), 1),
                    wind_speed=round(float(wind_speed), 1),
                    score=score,
                    outdoor_score=self.scoring_service.outdoor_score(score),
                )
            )

        merged.sort(key=lambda x: x.time)
        return merged[:24]

    def generate_insight(self, timeline: list[HourlyPoint]) -> str:
        """Build a multi-sentence contextual insight string from the timeline."""
        if not timeline:
            return "Data unavailable."

        current = timeline[0]
        tz = self.settings.tz()
        now_hour = datetime.now(tz=tz).hour

        aqi_note = self._aqi_label(current.aqi)
        parts: list[str] = [f"Air quality is {aqi_note} right now."]

        trend = self._aqi_trend_note(timeline)
        if trend:
            parts.append(trend)

        time_note = self._time_of_day_note(now_hour, current.outdoor_score)
        if time_note:
            parts.append(time_note)

        temp_note = self._temp_label(current.temperature)
        if temp_note:
            parts.append(temp_note)

        humidity_note = self._humidity_label(current.humidity)
        if humidity_note:
            parts.append(humidity_note)

        for note in (
            self._humidity_trap_note(current.humidity, current.aqi),
            self._heat_note(current.temperature),
            self._wind_note(current.wind_speed, current.aqi),
            self._season_note(datetime.now(tz=tz).month),
        ):
            if note:
                parts.append(note)

        return " ".join(parts)

    # ------------------------------------------------------------------
    # Note generators
    # ------------------------------------------------------------------

    def _aqi_trend_note(self, timeline: list[HourlyPoint]) -> str:
        if len(timeline) < 4:
            return ""
        future_avg = sum(p.aqi for p in timeline[1:4]) / 3
        current = timeline[0].aqi
        if future_avg >= current + 15:
            return "Pollution looks likely to rise over the next few hours."
        if future_avg <= current - 15:
            return "Air quality should improve over the next few hours."
        return "Conditions look fairly steady through the near term."

    def _time_of_day_note(self, hour: int, outdoor_score: float) -> str:
        if 6 <= hour <= 9 and outdoor_score >= 6.0:
            return "Morning conditions are favourable — a good window for outdoor activity."
        if 6 <= hour <= 9 and outdoor_score < 6.0:
            return "Morning conditions are not ideal today; consider a later window."
        if 17 <= hour <= 20 and outdoor_score >= 6.0:
            return "Evening air looks manageable for a walk or light exercise."
        if 12 <= hour <= 15:
            return "Midday heat can add stress even on cleaner-air days."
        return ""

    def _humidity_trap_note(self, humidity: float, aqi: float) -> str:
        if humidity >= 75 and aqi >= 100:
            return "High humidity is trapping pollutants close to the ground."
        return ""

    def _heat_note(self, temperature: float) -> str:
        if temperature >= 36:
            return "Intense heat will make any outdoor time feel significantly harder."
        if temperature >= 34:
            return "High heat adds physical strain beyond what the air quality number suggests."
        if temperature <= 22:
            return "Cooler temperatures make short outdoor activity easier today."
        return ""

    def _wind_note(self, wind_speed: float, aqi: float) -> str:
        if wind_speed >= 5.0 and aqi >= 80:
            return "A good breeze is helping to disperse pollution."
        if wind_speed <= 1.5 and aqi >= 100:
            return "Light wind means pollution can linger longer than usual."
        return ""

    def _season_note(self, month: int) -> str:
        """Add a seasonal context note for key Indian seasons."""
        if month in (11, 12, 1):
            return "Winter mornings often hold trapped ground-level haze — consider shifting walks to mid-morning."
        if month in (3, 4):
            return "Afternoon heat is rising ahead of the monsoon — plan outdoor errands earlier in the day."
        if month in (6, 7, 8, 9):
            return "Monsoon rains help clear the air, though higher humidity can make outdoor activity feel stickier."
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
        if aqi <= 300:
            return "very unhealthy"
        return "hazardous"

    @staticmethod
    def _temp_label(temp_c: float) -> str:
        if temp_c < 20:
            return "Temperatures are on the cooler side."
        if temp_c <= 30:
            return "Temperatures are comfortable."
        if temp_c <= 35:
            return "It will feel warm outside."
        return "High temperatures add stress outdoors."

    @staticmethod
    def _humidity_label(humidity: float) -> str:
        if humidity < 35:
            return "Low humidity makes the air feel drier today."
        if humidity <= 65:
            return "Humidity is in a manageable range."
        return "High humidity may feel sticky and uncomfortable."
