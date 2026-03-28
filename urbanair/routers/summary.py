from __future__ import annotations

import logging
from datetime import datetime
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi.templating import Jinja2Templates

from urbanair.cache.cache_manager import InMemoryTTLCache
from urbanair.cities import CityConfig, get_city, list_cities
from urbanair.config import Settings, get_settings
from urbanair.models.response_models import (
    AlertSignupRequest,
    AnalyticsEventRequest,
    DailySummary,
)
from urbanair.services.analytics_service import AnalyticsService
from urbanair.services.scoring_service import ScoringService
from urbanair.services.summary_service import SummaryService
from urbanair.services.waitlist_service import WaitlistService
from urbanair.storage import Storage

router = APIRouter()
templates = Jinja2Templates(directory="urbanair/templates")
logger = logging.getLogger(__name__)
cache_instance: InMemoryTTLCache | None = None
storage_instance: Storage | None = None
analytics_service: AnalyticsService | None = None
waitlist_service: WaitlistService | None = None


GUIDES = {
    "understanding-aqi": {
        "title": "How to read AQI without overthinking it",
        "description": "A plain-language guide to AQI, outdoor timing, and why the best window matters more than a daily average.",
        "body": [
            "AQI tells you how polluted the air is, but it does not tell you everything about how outdoor time will feel. Timing still matters.",
            "UrbanAir combines AQI with temperature and humidity so you can decide whether to go now, wait for a cleaner window, or keep the outing short.",
            "For most people, the most useful question is not whether a whole day is good or bad. It is whether the next two hours are workable.",
        ],
    },
    "outdoor-safety": {
        "title": "How to plan outdoor time on poor-air days",
        "description": "Quick guidance for commuters, families, and sensitive users when pollution, heat, or humidity make outdoor time harder.",
        "body": [
            "On poor-air days, reduce strenuous activity and try to move outdoor time into the best highlighted window.",
            "Families, older adults, and people with asthma should treat rising pollution as a reason to shorten outdoor plans or shift them later.",
            "Ventilation is also a timing decision. Open windows briefly during better periods instead of leaving them open all day.",
        ],
    },
}


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


def get_storage(settings: Settings = Depends(get_settings)) -> Storage:
    global storage_instance
    if storage_instance is None:
        storage_instance = Storage(settings.storage_path)
    return storage_instance


def get_analytics_service(storage: Storage = Depends(get_storage)) -> AnalyticsService:
    global analytics_service
    if analytics_service is None:
        analytics_service = AnalyticsService(storage)
    return analytics_service


def get_waitlist_service(storage: Storage = Depends(get_storage)) -> WaitlistService:
    global waitlist_service
    if waitlist_service is None:
        waitlist_service = WaitlistService(storage)
    return waitlist_service


def build_page_url(settings: Settings, path: str) -> str:
    base = settings.site_url.rstrip("/")
    suffix = path if path.startswith("/") else f"/{path}"
    return f"{base}{suffix}"


def build_summary_context(
    *,
    summary: DailySummary | None,
    city: CityConfig,
    scoring_service: ScoringService,
    settings: Settings,
) -> dict:
    timeline = summary.timeline if summary else []
    current_aqi_label = scoring_service.aqi_label(summary.current_aqi) if summary else "Unavailable"
    current_aqi_tone = aqi_tone(current_aqi_label) if summary else "poor"
    current_outdoor_label = (
        scoring_service.outdoor_label(summary.current_outdoor_score) if summary else "Unavailable"
    )

    best_summary = ""
    worst_summary = ""
    action_message = ""
    current_vs_next = ""
    generated_label = ""
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

        current_window_avg = round(sum(point.outdoor_score for point in timeline[:3]) / max(len(timeline[:3]), 1), 1)
        next_window_avg = round(sum(point.outdoor_score for point in timeline[3:6]) / max(len(timeline[3:6]), 1), 1)
        if next_window_avg > current_window_avg + 0.5:
            current_vs_next = "Waiting a little may improve outdoor comfort over the next few hours."
        elif current_window_avg > next_window_avg + 0.5:
            current_vs_next = "If you need to step out, the current stretch looks better than the next few hours."
        else:
            current_vs_next = "Conditions look fairly steady between now and the next few hours."
        generated_label = summary.generated_at.strftime("%d %b %Y, %I:%M %p")

    best_start = summary.best_window.start if summary else None
    best_end = summary.best_window.end if summary else None
    worst_start = summary.worst_window.start if summary else None
    worst_end = summary.worst_window.end if summary else None
    timeline_chart = [
        {
            "label": point.time.strftime("%I %p"),
            "score": point.outdoor_score,
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
        "related_cities": [item for item in related_cities if item is not None],
        "current_vs_next": current_vs_next,
        "generated_label": generated_label,
    }


async def load_city_summary(
    city: CityConfig,
    settings: Settings,
    cache: InMemoryTTLCache,
) -> tuple[DailySummary | None, str | None]:
    try:
        summary_service = SummaryService(settings=settings, cache=cache)
        summary = await summary_service.get_daily_summary(city)
        return summary, None
    except Exception as exc:
        logger.exception("Unable to build daily summary for %s: %s", city.slug, exc)
        return None, "Live data is temporarily unavailable. Please try again shortly."


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
            "disclaimer": "UrbanAir is informational only and is not medical advice.",
        }
    )
    return context


@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    settings: Settings = Depends(get_settings),
    cache: InMemoryTTLCache = Depends(get_cache),
    waitlist: WaitlistService = Depends(get_waitlist_service),
):
    default_city = get_city(settings.default_city_slug) or list_cities()[0]
    summary, error_message = await load_city_summary(default_city, settings, cache)
    featured_cities = list_cities()[: settings.launch_city_count]
    context = city_template_context(
        request=request,
        settings=settings,
        city=default_city,
        summary=summary,
        error_message=error_message,
        page_title=f"{settings.app_name} | India AQI and best time to go outside today",
        page_description="Check AQI, outdoor timing, commute guidance, and ventilation advice for major Indian cities on one fast website.",
        canonical_path="/",
        waitlist_count=waitlist.count(),
    )
    context.update(
        {
            "featured_cities": featured_cities,
            "guide_links": [
                {"slug": slug, "title": item["title"]}
                for slug, item in GUIDES.items()
            ],
        }
    )
    return templates.TemplateResponse(request=request, name="index.html", context=context)


@router.get("/cities/{city_slug}", response_class=HTMLResponse)
async def city_page(
    city_slug: str,
    request: Request,
    settings: Settings = Depends(get_settings),
    cache: InMemoryTTLCache = Depends(get_cache),
    waitlist: WaitlistService = Depends(get_waitlist_service),
):
    city = get_city(city_slug)
    if city is None:
        raise HTTPException(status_code=404, detail="City not found")

    summary, error_message = await load_city_summary(city, settings, cache)
    context = city_template_context(
        request=request,
        settings=settings,
        city=city,
        summary=summary,
        error_message=error_message,
        page_title=f"{city.name} AQI now, best outdoor time today, and commute guidance | {settings.app_name}",
        page_description=city.meta_description,
        canonical_path=f"/cities/{city.slug}",
        waitlist_count=waitlist.count(),
    )
    return templates.TemplateResponse(request=request, name="city.html", context=context)


@router.get("/compare/{city_slug}", response_class=HTMLResponse)
async def compare_city(
    city_slug: str,
    request: Request,
    settings: Settings = Depends(get_settings),
    cache: InMemoryTTLCache = Depends(get_cache),
    waitlist: WaitlistService = Depends(get_waitlist_service),
):
    city = get_city(city_slug)
    if city is None:
        raise HTTPException(status_code=404, detail="City not found")

    summary, error_message = await load_city_summary(city, settings, cache)
    context = city_template_context(
        request=request,
        settings=settings,
        city=city,
        summary=summary,
        error_message=error_message,
        page_title=f"Compare {city.name} AQI now vs later today | {settings.app_name}",
        page_description=f"Compare current and upcoming outdoor conditions in {city.name} to decide when to walk, commute, or ventilate.",
        canonical_path=f"/compare/{city.slug}",
        waitlist_count=waitlist.count(),
    )
    return templates.TemplateResponse(request=request, name="compare.html", context=context)


@router.get("/alerts", response_class=HTMLResponse)
async def alerts_page(
    request: Request,
    city: str | None = None,
    status: str | None = None,
    settings: Settings = Depends(get_settings),
    waitlist: WaitlistService = Depends(get_waitlist_service),
):
    selected_city = get_city(city or settings.default_city_slug) or list_cities()[0]
    context = {
        "request": request,
        "app_name": settings.app_name,
        "selected_city": selected_city,
        "all_cities": list_cities(),
        "page_title": f"Alerts waitlist | {settings.app_name}",
        "page_description": "Join the UrbanAir alert waitlist for AQI changes, best-time reminders, and commute-ready updates.",
        "canonical_url": build_page_url(settings, "/alerts"),
        "status": status,
        "waitlist_count": waitlist.count(),
        "disclaimer": "Get first access to timing alerts for your city.",
    }
    return templates.TemplateResponse(request=request, name="alerts.html", context=context)


@router.get("/guides/{guide_slug}", response_class=HTMLResponse)
async def guide_page(
    guide_slug: str,
    request: Request,
    settings: Settings = Depends(get_settings),
):
    guide = GUIDES.get(guide_slug)
    if guide is None:
        raise HTTPException(status_code=404, detail="Guide not found")

    return templates.TemplateResponse(
        request=request,
        name="guide.html",
        context={
            "request": request,
            "app_name": settings.app_name,
            "guide": guide,
            "guide_slug": guide_slug,
            "page_title": f"{guide['title']} | {settings.app_name}",
            "page_description": guide["description"],
            "canonical_url": build_page_url(settings, f"/guides/{guide_slug}"),
            "all_cities": list_cities(),
        },
    )


@router.get("/api/cities/{city_slug}/summary")
async def city_summary_api(
    city_slug: str,
    settings: Settings = Depends(get_settings),
    cache: InMemoryTTLCache = Depends(get_cache),
):
    city = get_city(city_slug)
    if city is None:
        raise HTTPException(status_code=404, detail="City not found")
    summary, error_message = await load_city_summary(city, settings, cache)
    if summary is None:
        return JSONResponse(status_code=503, content={"city": city.slug, "error": error_message})
    return {
        "city": city.slug,
        "state": city.state,
        "summary": summary.model_dump(mode="json"),
    }


@router.post("/api/events")
async def track_event(
    payload: AnalyticsEventRequest,
    service: AnalyticsService = Depends(get_analytics_service),
):
    service.track(payload.event_name, payload.city_slug)
    return {"ok": True}


@router.post("/api/alerts")
async def signup_alert(
    payload: AlertSignupRequest,
    service: WaitlistService = Depends(get_waitlist_service),
    analytics: AnalyticsService = Depends(get_analytics_service),
):
    city = get_city(payload.city_slug)
    if city is None:
        raise HTTPException(status_code=404, detail="City not found")
    email = payload.email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    service.add(email, city.slug)
    analytics.track("alert_signup", city.slug)
    return {"ok": True, "city": city.slug, "waitlist_count": service.count()}


@router.get("/sitemap.xml")
async def sitemap(settings: Settings = Depends(get_settings)):
    urls = ["/", "/alerts"]
    urls.extend(f"/cities/{city.slug}" for city in list_cities())
    urls.extend(f"/compare/{city.slug}" for city in list_cities())
    urls.extend(f"/guides/{slug}" for slug in GUIDES)
    body = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for path in urls:
        location = escape(build_page_url(settings, path))
        body.append("<url>")
        body.append(f"<loc>{location}</loc>")
        body.append("</url>")
    body.append("</urlset>")
    return Response("\n".join(body), media_type="application/xml")


@router.get("/robots.txt")
async def robots(settings: Settings = Depends(get_settings)):
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {build_page_url(settings, '/sitemap.xml')}\n"
    )
    return PlainTextResponse(content)
