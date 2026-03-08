from __future__ import annotations

from urbanair.models.response_models import ActivityRecommendation


class ActivityService:
    def generate(
        self,
        *,
        aqi: float,
        outdoor_score: float,
        temperature: float,
        humidity: float,
    ) -> list[ActivityRecommendation]:
        return [
            self._walking(aqi, outdoor_score, temperature),
            self._running(aqi, outdoor_score, temperature, humidity),
            self._cycling(aqi, outdoor_score, temperature),
            self._ventilation(aqi, outdoor_score, humidity),
        ]

    def _walking(self, aqi: float, outdoor_score: float, temperature: float) -> ActivityRecommendation:
        if aqi <= 100 and outdoor_score >= 6.0 and temperature <= 33:
            return ActivityRecommendation(
                name="Walking",
                status="Recommended",
                note="Good option for a normal outdoor walk.",
            )
        if aqi <= 140 and outdoor_score >= 4.5:
            return ActivityRecommendation(
                name="Walking",
                status="Okay",
                note="Keep it short and choose the best time window.",
            )
        return ActivityRecommendation(
            name="Walking",
            status="Avoid",
            note="Air or heat is not ideal for walking right now.",
        )

    def _running(
        self,
        aqi: float,
        outdoor_score: float,
        temperature: float,
        humidity: float,
    ) -> ActivityRecommendation:
        if aqi <= 80 and outdoor_score >= 7.0 and temperature <= 30 and humidity <= 75:
            return ActivityRecommendation(
                name="Running",
                status="Recommended",
                note="Suitable for higher-effort outdoor exercise.",
            )
        if aqi <= 110 and outdoor_score >= 5.5:
            return ActivityRecommendation(
                name="Running",
                status="Okay",
                note="Prefer light intensity and shorter duration.",
            )
        return ActivityRecommendation(
            name="Running",
            status="Avoid",
            note="Strenuous outdoor exercise is not a good idea now.",
        )

    def _cycling(self, aqi: float, outdoor_score: float, temperature: float) -> ActivityRecommendation:
        if aqi <= 90 and outdoor_score >= 6.5 and temperature <= 32:
            return ActivityRecommendation(
                name="Cycling",
                status="Recommended",
                note="Reasonable conditions for a ride.",
            )
        if aqi <= 125 and outdoor_score >= 5.0:
            return ActivityRecommendation(
                name="Cycling",
                status="Okay",
                note="Better during the highlighted best window.",
            )
        return ActivityRecommendation(
            name="Cycling",
            status="Avoid",
            note="Traffic pollution or heat can make cycling uncomfortable.",
        )

    def _ventilation(self, aqi: float, outdoor_score: float, humidity: float) -> ActivityRecommendation:
        if aqi <= 70 and outdoor_score >= 6.5 and humidity <= 80:
            return ActivityRecommendation(
                name="Window Ventilation",
                status="Recommended",
                note="A good time to let outside air in.",
            )
        if aqi <= 100 and outdoor_score >= 5.0:
            return ActivityRecommendation(
                name="Window Ventilation",
                status="Okay",
                note="Ventilate briefly rather than leaving windows open for long.",
            )
        return ActivityRecommendation(
            name="Window Ventilation",
            status="Avoid",
            note="Keep windows mostly closed until air improves.",
        )
