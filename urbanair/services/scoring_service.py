from __future__ import annotations

from datetime import datetime, timedelta, timezone

from urbanair.models.response_models import HourlyPoint, TwoHourWindow


class ScoringService:
    # Lower internal stress score is better; outdoor score is a user-facing 0-10 scale.
    MAX_AQI = 300.0
    IDEAL_TEMP_C = 24.0
    TEMP_RANGE_C = 14.0
    IDEAL_HUMIDITY = 50.0
    HUMIDITY_RANGE = 40.0

    def normalize_aqi(self, aqi: float) -> float:
        return self._clamp(aqi / self.MAX_AQI)

    def temperature_stress(self, temp_c: float) -> float:
        deviation = abs(temp_c - self.IDEAL_TEMP_C)
        return self._clamp(deviation / self.TEMP_RANGE_C)

    def humidity_stress(self, humidity: float) -> float:
        deviation = abs(humidity - self.IDEAL_HUMIDITY)
        return self._clamp(deviation / self.HUMIDITY_RANGE)

    def combined_score(self, aqi: float, temp_c: float, humidity: float) -> float:
        score = (
            (self.normalize_aqi(aqi) * 0.6)
            + (self.temperature_stress(temp_c) * 0.2)
            + (self.humidity_stress(humidity) * 0.2)
        )
        return round(score, 4)

    def outdoor_score(self, score: float) -> float:
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
        if aqi <= 50:
            return "Good"
        if aqi <= 100:
            return "Moderate"
        if aqi <= 150:
            return "Unhealthy for Sensitive People"
        if aqi <= 200:
            return "Unhealthy"
        return "Very Unhealthy"

    def compute_windows(self, timeline: list[HourlyPoint]) -> tuple[TwoHourWindow, TwoHourWindow]:
        if not timeline:
            now = datetime.now(timezone.utc)
            empty = TwoHourWindow(start=now, end=now, average_score=1.0)
            return empty, empty

        if len(timeline) < 2:
            point = timeline[0]
            single_window = TwoHourWindow(
                start=point.time,
                end=point.time,
                average_score=point.score,
            )
            return single_window, single_window

        windows: list[TwoHourWindow] = []
        for idx in range(len(timeline) - 1):
            p1 = timeline[idx]
            p2 = timeline[idx + 1]
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
