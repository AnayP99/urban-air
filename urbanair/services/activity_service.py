"""Activity recommendation engine for walks, runs, cycling, commute, and ventilation."""
from __future__ import annotations

from urbanair.models.response_models import ActivityRecommendation


class ActivityService:
    """Generates a list of activity recommendations based on current conditions."""

    def generate(
        self,
        *,
        aqi: float,
        outdoor_score: float,
        temperature: float,
        humidity: float,
        wind_speed: float = 0.0,
    ) -> list[ActivityRecommendation]:
        return [
            self._walking(aqi, outdoor_score, temperature),
            self._running(aqi, outdoor_score, temperature, humidity),
            self._cycling(aqi, outdoor_score, temperature),
            self._commute(aqi, outdoor_score, temperature),
            self._ventilation(aqi, outdoor_score, humidity),
        ]

    def _walking(self, aqi: float, outdoor_score: float, temperature: float) -> ActivityRecommendation:
        if aqi <= 100 and outdoor_score >= 6.0 and temperature <= 33:
            return ActivityRecommendation(
                name="Walking", icon="🚶",
                status="Recommended",
                note="Good conditions for a walk or short errand.",
            )
        if aqi <= 140 and outdoor_score >= 4.5:
            return ActivityRecommendation(
                name="Walking", icon="🚶",
                status="Okay",
                note="Keep it short and use the best time window.",
            )
        return ActivityRecommendation(
            name="Walking", icon="🚶",
            status="Avoid",
            note="Air quality or heat makes walking uncomfortable right now.",
        )

    def _running(
        self, aqi: float, outdoor_score: float, temperature: float, humidity: float
    ) -> ActivityRecommendation:
        if aqi <= 80 and outdoor_score >= 7.0 and temperature <= 30 and humidity <= 75:
            return ActivityRecommendation(
                name="Running", icon="🏃",
                status="Recommended",
                note="Good for higher-effort outdoor exercise.",
            )
        if aqi <= 110 and outdoor_score >= 5.5:
            return ActivityRecommendation(
                name="Running", icon="🏃",
                status="Okay",
                note="Keep intensity light and duration short.",
            )
        return ActivityRecommendation(
            name="Running", icon="🏃",
            status="Avoid",
            note="Strenuous outdoor exercise is not advisable now.",
        )

    def _cycling(self, aqi: float, outdoor_score: float, temperature: float) -> ActivityRecommendation:
        if aqi <= 90 and outdoor_score >= 6.5 and temperature <= 32:
            return ActivityRecommendation(
                name="Cycling", icon="🚲",
                status="Recommended",
                note="Reasonable conditions for a ride.",
            )
        if aqi <= 125 and outdoor_score >= 5.0:
            return ActivityRecommendation(
                name="Cycling", icon="🚲",
                status="Okay",
                note="Prefer the highlighted best window.",
            )
        return ActivityRecommendation(
            name="Cycling", icon="🚲",
            status="Avoid",
            note="Traffic pollution or heat makes cycling uncomfortable.",
        )

    def _commute(self, aqi: float, outdoor_score: float, temperature: float) -> ActivityRecommendation:
        if aqi <= 100 and outdoor_score >= 5.5 and temperature <= 35:
            return ActivityRecommendation(
                name="Commute", icon="🚌",
                status="Recommended",
                note="Manageable conditions for your journey.",
            )
        if aqi <= 150 and outdoor_score >= 4.0:
            return ActivityRecommendation(
                name="Commute", icon="🚌",
                status="Okay",
                note="Use covered transport where possible; limit walking segments.",
            )
        return ActivityRecommendation(
            name="Commute", icon="🚌",
            status="Avoid",
            note="Limit exposure — use enclosed transit and avoid walking segments.",
        )

    def _ventilation(
        self, aqi: float, outdoor_score: float, humidity: float
    ) -> ActivityRecommendation:
        if aqi <= 70 and outdoor_score >= 6.5 and humidity <= 80:
            return ActivityRecommendation(
                name="Ventilation", icon="🪟",
                status="Recommended",
                note="Good time to open windows and let fresh air in.",
            )
        if aqi <= 100 and outdoor_score >= 5.0:
            return ActivityRecommendation(
                name="Ventilation", icon="🪟",
                status="Okay",
                note="Ventilate briefly rather than leaving windows open all day.",
            )
        return ActivityRecommendation(
            name="Ventilation", icon="🪟",
            status="Avoid",
            note="Keep windows mostly closed until air quality improves.",
        )
