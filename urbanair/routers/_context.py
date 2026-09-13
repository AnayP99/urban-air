"""Context-building helpers shared between page routers."""
from __future__ import annotations

import logging
from datetime import datetime

from fastapi import Request

from urbanair.cache.cache_manager import InMemoryTTLCache
from urbanair.cities import CityConfig, get_city, list_cities
from urbanair.config import Settings
from urbanair.models.response_models import DailySummary
from urbanair.services.scoring_service import ScoringService
from urbanair.services.summary_service import SummaryService

logger = logging.getLogger(__name__)


def build_page_url(settings: Settings, path: str) -> str:
    base = settings.site_url.rstrip("/")
    suffix = path if path.startswith("/") else f"/{path}"
    return f"{base}{suffix}"


def format_window(start: datetime, end: datetime) -> str:
    return f"{start.strftime('%I:%M %p')} – {end.strftime('%I:%M %p')}"


def timeline_category(outdoor_score: float) -> str:
    if outdoor_score >= 7.0:
        return "good"
    if outdoor_score >= 4.5:
        return "moderate"
    return "poor"


def aqi_tone(label: str) -> str:
    mapping = {
        "Good": "good",
        "Moderate": "moderate",
        "Unhealthy for Sensitive Groups": "sensitive",
        "Unhealthy": "unhealthy",
        "Very Unhealthy": "very-unhealthy",
        "Hazardous": "hazardous",
    }
    return mapping.get(label, "poor")


async def load_city_summary(
    city: CityConfig,
    settings: Settings,
    cache: InMemoryTTLCache,
) -> tuple[DailySummary | None, str | None]:
    """Fetch the DailySummary for *city*, returning (None, error_message) on failure."""
    try:
        service = SummaryService(settings=settings, cache=cache)
        summary = await service.get_daily_summary(city)
        return summary, None
    except Exception as exc:
        logger.exception("Failed to build summary for %s: %s", city.slug, exc)
        return None, "Live data is temporarily unavailable. Please try again shortly."


def build_summary_context(
    *,
    summary: DailySummary | None,
    city: CityConfig,
    scoring_service: ScoringService,
    settings: Settings,
) -> dict:
    """Build the template context dict for a city's summary data."""
    timeline = summary.timeline if summary else []
    current_aqi_label = scoring_service.aqi_label(summary.current_aqi) if summary else "Unavailable"
    current_aqi_tone = aqi_tone(current_aqi_label)
    current_outdoor_label = (
        scoring_service.outdoor_label(summary.current_outdoor_score) if summary else "Unavailable"
    )

    best_summary = worst_summary = action_message = current_vs_next = generated_label = ""
    if summary:
        best_summary = format_window(summary.best_window.start, summary.best_window.end)
        worst_summary = format_window(summary.worst_window.start, summary.worst_window.end)
        
        now = datetime.now(tz=settings.tz())
        start = summary.best_window.start
        end = summary.best_window.end
        if start.tzinfo is None:
            start = start.replace(tzinfo=settings.tz())
        if end.tzinfo is None:
            end = end.replace(tzinfo=settings.tz())

        if start <= now <= end:
            action_message = "Conditions are favourable right now — a good time to step out."
        else:
            action_message = (
                f"The best window starts around "
                f"{start.strftime('%I:%M %p')}."
            )

        current_avg = round(
            sum(p.outdoor_score for p in timeline[:3]) / max(len(timeline[:3]), 1), 1
        )
        next_avg = round(
            sum(p.outdoor_score for p in timeline[3:6]) / max(len(timeline[3:6]), 1), 1
        )
        if next_avg > current_avg + 0.5:
            current_vs_next = "Waiting a little may improve outdoor comfort over the next few hours."
        elif current_avg > next_avg + 0.5:
            current_vs_next = "The current stretch looks better than the next few hours — go now if you can."
        else:
            current_vs_next = "Conditions look fairly steady through the next few hours."

        generated_label = summary.generated_at.strftime("%d %b %Y, %I:%M %p")

    best_start = summary.best_window.start if summary else None
    best_end = summary.best_window.end if summary else None
    worst_start = summary.worst_window.start if summary else None
    worst_end = summary.worst_window.end if summary else None

    timeline_chart = [
        {
            "label": point.time.strftime("%I %p"),
            "score": point.outdoor_score,
            "aqi": point.aqi,
            "temperature": point.temperature,
            "humidity": point.humidity,
            "category": timeline_category(point.outdoor_score),
            "is_best": bool(best_start and best_end and best_start <= point.time < best_end),
            "is_worst": bool(worst_start and worst_end and worst_start <= point.time < worst_end),
        }
        for point in timeline
    ]

    related_cities = [get_city(slug) for slug in city.related_slugs]
    return {
        "summary": summary,
        "current_aqi_label": current_aqi_label,
        "current_aqi_tone": current_aqi_tone,
        "current_outdoor_label": current_outdoor_label,
        "best_summary": best_summary,
        "worst_summary": worst_summary,
        "action_message": action_message,
        "timeline_chart": timeline_chart,
        "related_cities": [c for c in related_cities if c is not None],
        "current_vs_next": current_vs_next,
        "generated_label": generated_label,
    }


def city_template_context(
    *,
    request: Request,
    settings: Settings,
    city: CityConfig,
    summary: DailySummary | None,
    error_message: str | None,
    page_title: str,
    page_description: str,
    canonical_path: str,
    waitlist_count: int,
) -> dict:
    """Assemble the full Jinja2 template context for any city-centric page."""
    scoring_service = ScoringService()
    page_url = build_page_url(settings, canonical_path)
    context = build_summary_context(
        summary=summary,
        city=city,
        scoring_service=scoring_service,
        settings=settings,
    )
    context.update(
        {
            "request": request,
            "now": datetime.now(tz=settings.tz()),
            "app_name": settings.app_name,
            "city": city,
            "page_title": page_title,
            "page_description": page_description,
            "canonical_url": page_url,
            "home_url": build_page_url(settings, "/"),
            "compare_url": build_page_url(settings, f"/compare/{city.slug}"),
            "alerts_url": build_page_url(settings, f"/alerts?city={city.slug}"),
            "api_url": build_page_url(settings, f"/api/cities/{city.slug}/summary"),
            "error_message": error_message,
            "waitlist_count": waitlist_count,
            "all_cities": list_cities(),
            "data_sources": [
                {"name": "World Air Quality Index", "url": "https://aqicn.org/api/"},
                {"name": "OpenWeather", "url": "https://openweathermap.org/api"},
            ],
            "disclaimer": "UrbanAir is for informational purposes only and is not medical advice.",
        }
    )
    return context
