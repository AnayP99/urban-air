from __future__ import annotations

from datetime import datetime, timedelta

import httpx

from urbanair.config import Settings


class AQIService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def fetch_hourly_aqi(self, city_slug: str) -> list[dict]:
        if not self.settings.waqi_api_key:
            raise RuntimeError("WAQI API key is missing. Set WAQI_API_KEY in environment.")

        url = f"{self.settings.waqi_base_url}/feed/{city_slug}/"
        params = {"token": self.settings.waqi_api_key}

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

        if payload.get("status") != "ok":
            error_data = payload.get("data", "")
            raise RuntimeError(f"WAQI request failed: {error_data}")

        data = payload.get("data", {})
        tz = self.settings.tz()
        now_local = datetime.now(tz=tz).replace(minute=0, second=0, microsecond=0)
        hourly_forecast = data.get("forecast", {}).get("hourly", {})

        series = hourly_forecast.get("pm25") or hourly_forecast.get("aqi") or []
        normalized = self._parse_hourly_series(series, tz)

        # Some WAQI endpoints may not include hourly forecast. Fall back to flat series from current AQI.
        if len(normalized) < 24:
            current_aqi = self._to_float(data.get("aqi"), fallback=100.0)
            normalized = [
                {"time": now_local + timedelta(hours=idx), "aqi": current_aqi}
                for idx in range(24)
            ]

        return normalized[:24]

    def _parse_hourly_series(self, series: list[dict], tz) -> list[dict]:
        out: list[dict] = []
        for item in series:
            value = self._to_float(item.get("v"), fallback=None)
            ts = item.get("t")
            if value is None or not ts:
                continue
            try:
                # Common WAQI format: 2026-03-03 14:00:00
                dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz)
            except ValueError:
                continue
            out.append({"time": dt, "aqi": value})

        out.sort(key=lambda x: x["time"])
        return out

    @staticmethod
    def _to_float(value: object, fallback: float | None) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback
