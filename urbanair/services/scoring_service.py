from __future__ import annotations

from datetime import datetime, timezone

from urbanair.models.response_models import HourlyPoint, TwoHourWindow


class ScoringService:
    # Tuned for a conservative "comfort outdoors" interpretation.
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

    def comfort_percent(self, score: float) -> int:
        # Score: lower is better. Comfort: higher is better.
        return int(round((1 - self._clamp(score)) * 100))

    def comfort_label(self, score: float) -> str:
        comfort = self.comfort_percent(score)
        if comfort >= 75:
            return "Good"
        if comfort >= 50:
            return "Okay"
        return "Poor"

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
                    end=p2.time,
                    average_score=avg,
                )
            )

        best = min(windows, key=lambda w: w.average_score)
        worst = max(windows, key=lambda w: w.average_score)
        return best, worst

    @staticmethod
    def _clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
        return max(min_value, min(max_value, value))
