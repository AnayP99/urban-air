"""Outdoor scoring logic combining AQI, temperature, humidity, and wind speed.

Scoring formula (lower internal stress = better outdoor conditions):
    stress = (aqi_norm * 0.55) + (temp_stress * 0.20) + (humidity_stress * 0.18) + (wind_relief * 0.07)

The user-facing outdoor score (0–10) is computed as:  (1 - stress) * 10
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from urbanair.models.response_models import HourlyPoint, TwoHourWindow


class ScoringService:
    """Converts raw environmental data into a user-friendly outdoor score."""

    MAX_AQI: float = 300.0
    IDEAL_TEMP_C: float = 24.0
    TEMP_RANGE_C: float = 14.0
    IDEAL_HUMIDITY: float = 50.0
    HUMIDITY_RANGE: float = 40.0
    # Wind speeds above this threshold provide a full relief bonus.
    WIND_RELIEF_THRESHOLD_MS: float = 5.0

    # Scoring weights (must sum to 1.0).
    W_AQI = 0.55
    W_TEMP = 0.20
    W_HUMIDITY = 0.18
    W_WIND = 0.07

    def normalize_aqi(self, aqi: float) -> float:
        """Normalise AQI to [0, 1] where 1 is maximally poor."""
        return self._clamp(aqi / self.MAX_AQI)

    def temperature_stress(self, temp_c: float) -> float:
        """Return a [0, 1] stress value for temperature deviation from 24 °C."""
        deviation = abs(temp_c - self.IDEAL_TEMP_C)
        return self._clamp(deviation / self.TEMP_RANGE_C)

    def humidity_stress(self, humidity: float) -> float:
        """Return a [0, 1] stress value for humidity deviation from 50 %."""
        deviation = abs(humidity - self.IDEAL_HUMIDITY)
        return self._clamp(deviation / self.HUMIDITY_RANGE)

    def wind_relief(self, wind_speed_ms: float, aqi: float) -> float:
        """Return a [0, 1] relief value — higher wind provides more relief when AQI is high.

        Wind only helps when air quality is already stressed.  Below AQI 60 the
        wind bonus is minimal; above AQI 100 a good breeze provides its full bonus.
        """
        if aqi < 50:
            return 0.0
        aqi_factor = self._clamp((aqi - 50) / 150)  # ramps between AQI 50..200
        speed_factor = self._clamp(wind_speed_ms / self.WIND_RELIEF_THRESHOLD_MS)
        return aqi_factor * speed_factor

    def combined_score(self, aqi: float, temp_c: float, humidity: float, wind_speed_ms: float = 0.0) -> float:
        """Return the overall stress score [0, 1] combining all factors."""
        score = (
            self.normalize_aqi(aqi) * self.W_AQI
            + self.temperature_stress(temp_c) * self.W_TEMP
            + self.humidity_stress(humidity) * self.W_HUMIDITY
            - self.wind_relief(wind_speed_ms, aqi) * self.W_WIND  # relief *reduces* stress
        )
        return round(self._clamp(score), 4)

    def outdoor_score(self, score: float) -> float:
        """Convert internal stress score to user-facing 0–10 outdoor score."""
        return round((1 - self._clamp(score)) * 10, 1)

    def outdoor_label(self, outdoor_score: float) -> str:
        if outdoor_score >= 7.0:
            return "Good"
        if outdoor_score >= 4.5:
            return "Moderate"
        return "Poor"

    def outdoor_category(self, outdoor_score: float) -> str:
        if outdoor_score >= 7.0:
            return "good"
        if outdoor_score >= 4.5:
            return "moderate"
        return "poor"

    def aqi_label(self, aqi: float) -> str:
        """Return the EPA-aligned AQI category label."""
        if aqi <= 50:
            return "Good"
        if aqi <= 100:
            return "Moderate"
        if aqi <= 150:
            return "Unhealthy for Sensitive Groups"
        if aqi <= 200:
            return "Unhealthy"
        if aqi <= 300:
            return "Very Unhealthy"
        return "Hazardous"

    def aqi_category(self, aqi: float) -> str:
        """Return the CSS-safe AQI category key."""
        if aqi <= 50:
            return "good"
        if aqi <= 100:
            return "moderate"
        if aqi <= 150:
            return "sensitive"
        if aqi <= 200:
            return "unhealthy"
        if aqi <= 300:
            return "very-unhealthy"
        return "hazardous"

    def compute_windows(self, timeline: list[HourlyPoint]) -> tuple[TwoHourWindow, TwoHourWindow]:
        """Return (best_window, worst_window) 2-hour blocks from *timeline*."""
        if not timeline:
            now = datetime.now(timezone.utc)
            empty = TwoHourWindow(start=now, end=now, average_score=1.0)
            return empty, empty

        if len(timeline) < 2:
            point = timeline[0]
            single = TwoHourWindow(start=point.time, end=point.time, average_score=point.score)
            return single, single

        windows: list[TwoHourWindow] = []
        for idx in range(len(timeline) - 1):
            p1, p2 = timeline[idx], timeline[idx + 1]
            avg = round((p1.score + p2.score) / 2, 4)
            windows.append(
                TwoHourWindow(
                    start=p1.time,
                    end=p1.time + timedelta(hours=2),
                    average_score=avg,
                )
            )

        best = min(windows, key=lambda w: w.average_score)
        worst = max(windows, key=lambda w: w.average_score)
        return best, worst

    @staticmethod
    def _clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
        return max(min_value, min(max_value, value))
