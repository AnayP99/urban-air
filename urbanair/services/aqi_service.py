"""AQI service fetching hourly data from WAQI with OpenWeather air pollution fallback."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import logging

import httpx

from urbanair.config import Settings

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2
_RETRY_BACKOFF_S = [0.5, 1.5]


def pm25_to_aqi(pm25: float) -> float:
    """Convert PM2.5 concentration (ug/m3) to US EPA AQI index (0-500)."""
    breakpoints = [
        (0.0, 12.0, 0, 50),
        (12.1, 35.4, 51, 100),
        (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200),
        (150.5, 250.4, 201, 300),
        (250.5, 500.4, 301, 500),
    ]
    if pm25 <= 0:
        return 0.0
    for c_low, c_high, i_low, i_high in breakpoints:
        if c_low <= pm25 <= c_high:
            return round(((i_high - i_low) / (c_high - c_low)) * (pm25 - c_low) + i_low, 1)
    if pm25 > 500.4:
        return 500.0
    return 0.0


class AQIService:
    """Fetches hourly AQI data from WAQI, falling back to OpenWeather air pollution."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def fetch_hourly_aqi(
        self,
        city_slug: str,
        lat: float | None = None,
        lon: float | None = None,
    ) -> list[dict]:
        """Return a list of up to 24 hourly AQI dicts for *city_slug*.

        Tries WAQI city slug first, falls back to WAQI geo coordinates,
        and finally falls back to OpenWeather Air Pollution Forecast.
        """
        # 1. Attempt WAQI city slug
        if self.settings.waqi_api_key:
            try:
                result = await self._fetch_waqi_feed(f"{self.settings.waqi_base_url}/feed/{city_slug}/")
                if result:
                    return result
            except Exception as exc:
                logger.warning("WAQI slug fetch failed for '%s': %s", city_slug, exc)

            # 2. Attempt WAQI geo coordinates
            if lat is not None and lon is not None:
                try:
                    result = await self._fetch_waqi_feed(f"{self.settings.waqi_base_url}/feed/geo:{lat};{lon}/")
                    if result:
                        return result
                except Exception as exc:
                    logger.warning("WAQI geo fetch failed for '%s' (%s, %s): %s", city_slug, lat, lon, exc)

        # 3. Fall back to OpenWeather Air Pollution Forecast API
        if self.settings.openweather_api_key and lat is not None and lon is not None:
            try:
                result = await self._fetch_openweather_pollution(lat, lon)
                if result:
                    logger.info("Using OpenWeather air pollution forecast fallback for '%s'", city_slug)
                    return result
            except Exception as exc:
                logger.warning("OpenWeather pollution fallback failed for '%s': %s", city_slug, exc)

        raise RuntimeError(
            f"Unable to retrieve live AQI data for '{city_slug}' from WAQI or OpenWeather."
        )

    async def _fetch_waqi_feed(self, url: str) -> list[dict] | None:
        params = {"token": self.settings.waqi_api_key}
        for attempt in range(_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    payload = response.json()
                    if payload.get("status") == "ok":
                        return self._parse_response(payload)
                    logger.debug("WAQI endpoint %s returned non-ok: %s", url, payload.get("data"))
                    return None
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                if attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(_RETRY_BACKOFF_S[attempt])
                else:
                    raise exc
        return None

    async def _fetch_openweather_pollution(self, lat: float, lon: float) -> list[dict]:
        url = f"{self.settings.openweather_base_url}/data/2.5/air_pollution/forecast"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.settings.openweather_api_key,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

        tz = self.settings.tz()
        series: list[dict] = []
        for item in payload.get("list", [])[:24]:
            dt_utc = datetime.fromtimestamp(item["dt"], tz=timezone.utc)
            dt_local = dt_utc.astimezone(tz)
            pm25 = float(item.get("components", {}).get("pm2_5", 25.0))
            series.append({
                "time": dt_local,
                "aqi": pm25_to_aqi(pm25),
            })

        series.sort(key=lambda x: x["time"])
        return series[:24]

    def _parse_response(self, payload: dict) -> list[dict]:
        """Parse the WAQI JSON payload into a normalized hourly series."""
        data = payload.get("data", {})
        tz = self.settings.tz()
        now_local = datetime.now(tz=tz).replace(minute=0, second=0, microsecond=0)

        hourly_forecast = data.get("forecast", {}).get("hourly", {})
        series = hourly_forecast.get("pm25") or hourly_forecast.get("aqi") or []
        normalized = self._parse_hourly_series(series, tz)

        if len(normalized) < 24:
            current_aqi = self._to_float(data.get("aqi"), fallback=75.0)
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
                dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz)
            except ValueError:
                continue
            out.append({"time": dt, "aqi": value})

        out.sort(key=lambda x: x["time"])
        return out

    @staticmethod
    def _to_float(value: object, fallback: float | None) -> float | None:
        try:
            return float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return fallback
