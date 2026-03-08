from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates

from urbanair.cache.cache_manager import InMemoryTTLCache
from urbanair.config import Settings, get_settings
from urbanair.models.response_models import DailySummary
from urbanair.services.activity_service import ActivityService
from urbanair.services.aqi_service import AQIService
from urbanair.services.insight_service import InsightService
from urbanair.services.scoring_service import ScoringService
from urbanair.services.weather_service import WeatherService

router = APIRouter()
templates = Jinja2Templates(directory="urbanair/templates")
logger = logging.getLogger(__name__)
cache_instance: InMemoryTTLCache | None = None


def timeline_category(outdoor_score: float) -> str:
    if outdoor_score >= 7.0:
        return "good"
    if outdoor_score >= 4.5:
        return "moderate"
    return "poor"


def format_window(start: datetime, end: datetime) -> str:
    return f"{start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')}"


def aqi_tone(aqi_label: str) -> str:
    if aqi_label == "Good":
        return "good"
    if aqi_label == "Moderate":
        return "moderate"
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
                activity_service=ActivityService(),
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
    current_aqi_label = (
        scoring_service.aqi_label(summary.current_aqi)
        if summary
        else "Unavailable"
    )
    current_aqi_tone = aqi_tone(current_aqi_label) if summary else "poor"
    current_outdoor_label = (
        scoring_service.outdoor_label(summary.current_outdoor_score)
        if summary
        else "Unavailable"
    )

    best_summary = ""
    worst_summary = ""
    action_message = ""
    if summary:
        best_summary = format_window(summary.best_window.start, summary.best_window.end)
        worst_summary = format_window(summary.worst_window.start, summary.worst_window.end)
        now = datetime.now(tz=settings.tz())
        if summary.best_window.start <= now <= summary.best_window.end:
            action_message = "Conditions are favorable right now. A short outdoor trip makes sense."
        else:
            action_message = (
                f"The best part of the day starts around {summary.best_window.start.strftime('%I:%M %p')}."
            )

    best_start = summary.best_window.start if summary else None
    best_end = summary.best_window.end if summary else None
    worst_start = summary.worst_window.start if summary else None
    worst_end = summary.worst_window.end if summary else None
    timeline_chart = []
    for point in timeline:
        timeline_chart.append(
            {
                "label": point.time.strftime("%I %p"),
                "score": point.outdoor_score,
                "category": timeline_category(point.outdoor_score),
                "is_best": bool(best_start and best_end and best_start <= point.time < best_end),
                "is_worst": bool(worst_start and worst_end and worst_start <= point.time < worst_end),
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
            "current_aqi_label": current_aqi_label,
            "current_aqi_tone": current_aqi_tone,
            "current_outdoor_label": current_outdoor_label,
            "best_summary": best_summary,
            "worst_summary": worst_summary,
            "action_message": action_message,
            "timeline_chart": timeline_chart,
        },
    )
