"""OpenWeather API client with retry logic and 3h forecast interpolation."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone, tzinfo
import logging

import httpx

from urbanair.config import Settings

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_BACKOFF_S = [0.5, 1.5, 3.0]


class WeatherService:
    """Fetches hourly weather from OpenWeather (OneCall 3.0 with 2.5 fallback)."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def fetch_hourly_weather(self, lat: float, lon: float) -> list[dict]:
        """Fetch up to 24 hours of weather forecasts for the given coordinates."""
        if not self.settings.openweather_api_key:
            raise RuntimeError(
                "OpenWeather API key is missing. Set OPENWEATHER_API_KEY in environment."
            )

        tz = self.settings.tz()
        one_call_url = f"{self.settings.openweather_base_url}/data/3.0/onecall"
        one_call_params = {
            "lat": lat,
            "lon": lon,
            "exclude": "current,minutely,daily,alerts",
            "units": "metric",
            "appid": self.settings.openweather_api_key,
        }

        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.get(one_call_url, params=one_call_params)
                    if response.status_code == 200:
                        payload = response.json()
                        return self._parse_onecall_hourly(payload, tz)

                    # Free-tier keys commonly support 2.5 forecast but not One Call 3.0.
                    if response.status_code in (401, 403, 404):
                        return await self._fetch_forecast_fallback(client, lat, lon, tz)

                    response.raise_for_status()
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                last_exc = exc
                logger.warning(
                    "OpenWeather request error (attempt %d/%d): %s",
                    attempt + 1,
                    _MAX_RETRIES,
                    exc,
                )
                if attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(_RETRY_BACKOFF_S[attempt])

        # If OneCall attempts failed due to network, try fallback once
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                return await self._fetch_forecast_fallback(client, lat, lon, tz)
        except Exception:
            pass

        raise RuntimeError(
            f"OpenWeather request failed after {_MAX_RETRIES} attempts for ({lat}, {lon})."
        ) from last_exc

    def _parse_onecall_hourly(self, payload: dict, tz: tzinfo) -> list[dict]:
        hourly = payload.get("hourly", [])[:24]
        out: list[dict] = []
        for item in hourly:
            dt_utc = datetime.fromtimestamp(item["dt"], tz=timezone.utc)
            dt_local = dt_utc.astimezone(tz)
            out.append(
                {
                    "time": dt_local,
                    "temperature": float(item.get("temp", 0.0)),
                    "humidity": float(item.get("humidity", 0.0)),
                    "wind_speed": float(item.get("wind_speed", 0.0)),
                }
            )
        return out

    async def _fetch_forecast_fallback(
        self,
        client: httpx.AsyncClient,
        lat: float,
        lon: float,
        tz: tzinfo,
    ) -> list[dict]:
        url = f"{self.settings.openweather_base_url}/data/2.5/forecast"
        params = {
            "lat": lat,
            "lon": lon,
            "units": "metric",
            "appid": self.settings.openweather_api_key,
        }
        response = await client.get(url, params=params)
        response.raise_for_status()
        payload = response.json()

        points_3h: list[dict] = []
        for item in payload.get("list", [])[:8]:
            dt_utc = datetime.fromtimestamp(item["dt"], tz=timezone.utc)
            dt_local = dt_utc.astimezone(tz)
            main = item.get("main", {})
            points_3h.append(
                {
                    "time": dt_local,
                    "temperature": float(main.get("temp", 0.0)),
                    "humidity": float(main.get("humidity", 0.0)),
                    "wind_speed": float(item.get("wind", {}).get("speed", 0.0)),
                }
            )

        return self._expand_3h_to_hourly(points_3h)[:24]

    @staticmethod
    def _expand_3h_to_hourly(points_3h: list[dict]) -> list[dict]:
        if not points_3h:
            return []

        if len(points_3h) == 1:
            item = points_3h[0]
            base_time = item["time"].replace(minute=0, second=0, microsecond=0)
            return [
                {
                    "time": base_time + timedelta(hours=i),
                    "temperature": round(float(item["temperature"]), 1),
                    "humidity": round(float(item["humidity"]), 1),
                    "wind_speed": round(float(item["wind_speed"]), 1),
                }
                for i in range(3)
            ]

        out: list[dict] = []
        # Interpolate hourly values between 3-hour forecast anchors.
        for idx in range(len(points_3h) - 1):
            start = points_3h[idx]
            end = points_3h[idx + 1]
            start_time = start["time"].replace(minute=0, second=0, microsecond=0)

            for step in range(3):
                ratio = step / 3.0
                temp = start["temperature"] + (end["temperature"] - start["temperature"]) * ratio
                humidity = start["humidity"] + (end["humidity"] - start["humidity"]) * ratio
                wind = start["wind_speed"] + (end["wind_speed"] - start["wind_speed"]) * ratio
                out.append(
                    {
                        "time": start_time + timedelta(hours=step),
                        "temperature": round(float(temp), 1),
                        "humidity": round(float(humidity), 1),
                        "wind_speed": round(float(wind), 1),
                    }
                )

        # Include final anchor point
        last = points_3h[-1]
        out.append(
            {
                "time": last["time"].replace(minute=0, second=0, microsecond=0),
                "temperature": round(float(last["temperature"]), 1),
                "humidity": round(float(last["humidity"]), 1),
                "wind_speed": round(float(last["wind_speed"]), 1),
            }
        )
        out.sort(key=lambda x: x["time"])
        return out
