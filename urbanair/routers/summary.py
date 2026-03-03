from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates

from urbanair.cache.cache_manager import InMemoryTTLCache
from urbanair.config import Settings, get_settings
from urbanair.models.response_models import DailySummary
from urbanair.services.aqi_service import AQIService
from urbanair.services.insight_service import InsightService
from urbanair.services.scoring_service import ScoringService
from urbanair.services.weather_service import WeatherService

router = APIRouter()
templates = Jinja2Templates(directory="urbanair/templates")
logger = logging.getLogger(__name__)
cache_instance: InMemoryTTLCache | None = None


def comfort_category(comfort: int) -> str:
    if comfort >= 75:
        return "good"
    if comfort >= 50:
        return "okay"
    return "poor"


def get_cache(settings: Settings = Depends(get_settings)) -> InMemoryTTLCache:
    global cache_instance
    if cache_instance is None:
        cache_instance = InMemoryTTLCache(ttl_seconds=settings.cache_ttl_seconds)
    return cache_instance


@router.get("/")
async def index(
    request: Request,
    settings: Settings = Depends(get_settings),
    cache: InMemoryTTLCache = Depends(get_cache),
):
    cache_key = f"summary:{settings.default_city_slug}"
    summary: DailySummary | None = cache.get(cache_key)

    error_message = None
    scoring_service = ScoringService()
    if summary is None:
        try:
            insight_service = InsightService(
                settings=settings,
                aqi_service=AQIService(settings),
                weather_service=WeatherService(settings),
                scoring_service=scoring_service,
            )
            summary = await insight_service.build_daily_summary(
                city_name=settings.default_city_name,
                city_slug=settings.default_city_slug,
                lat=settings.default_city_lat,
                lon=settings.default_city_lon,
            )
            cache.set(cache_key, summary)
        except Exception as exc:
            logger.exception("Unable to build daily summary: %s", exc)
            error_message = "Live data is temporarily unavailable. Please try again shortly."

    timeline = summary.timeline if summary else []
    comfort_points = [scoring_service.comfort_percent(point.score) for point in timeline]
    current_comfort = comfort_points[0] if comfort_points else 0
    current_aqi_label = (
        scoring_service.aqi_label(summary.current_aqi)
        if summary
        else "Unavailable"
    )

    best_summary = None
    worst_summary = None
    action_message = None
    if summary:
        best_summary = (
            f"{summary.best_window.start.strftime('%I:%M %p')} to "
            f"{summary.best_window.end.strftime('%I:%M %p')}"
        )
        worst_summary = (
            f"{summary.worst_window.start.strftime('%I:%M %p')} to "
            f"{summary.worst_window.end.strftime('%I:%M %p')}"
        )
        now = datetime.now(tz=settings.tz())
        if summary.best_window.start <= now <= summary.best_window.end:
            action_message = "This is a good time to step outside."
        else:
            action_message = (
                f"Plan outdoor activity around {summary.best_window.start.strftime('%I:%M %p')}."
            )

    comfort_timeline = []
    for idx, point in enumerate(timeline):
        comfort_value = comfort_points[idx]
        comfort_timeline.append(
            {
                "time": point.time.strftime("%I %p"),
                "comfort": comfort_value,
                "category": comfort_category(comfort_value),
            }
        )

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": settings.app_name,
            "city": settings.default_city_name,
            "summary": summary,
            "error_message": error_message,
            "current_comfort": current_comfort,
            "current_aqi_label": current_aqi_label,
            "best_summary": best_summary,
            "worst_summary": worst_summary,
            "action_message": action_message,
            "comfort_timeline": comfort_timeline,
        },
    )
