"""HTML page routes for the UrbanAir web application."""
from __future__ import annotations

from datetime import datetime
import logging
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.templating import Jinja2Templates

from urbanair.cache.cache_manager import InMemoryTTLCache
from urbanair.cities import get_city, list_cities
from urbanair.config import Settings, get_settings
from urbanair.routers._context import (
    build_page_url,
    city_template_context,
    load_city_summary,
)
from urbanair.services.waitlist_service import WaitlistService
from urbanair.storage import Storage

from pathlib import Path

router = APIRouter()
_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
logger = logging.getLogger(__name__)

GUIDES: dict[str, dict] = {
    "understanding-aqi": {
        "title": "How to read AQI without overthinking it",
        "description": "A plain-language guide to AQI, outdoor timing, and why the best window matters more than a daily average.",
        "body": [
            "AQI tells you how polluted the air is right now — but it does not tell you whether the next two hours will be manageable for a walk, a school run, or ventilating your home.",
            "UrbanAir combines AQI with temperature and humidity into a single Outdoor Score, so your timing decision becomes concrete rather than abstract.",
            "For most people, the most useful question is not whether the whole day looks bad. It is whether the next two hours are workable. That is exactly what the best-time window answers.",
        ],
    },
    "outdoor-safety": {
        "title": "How to plan outdoor time on poor-air days",
        "description": "Quick guidance for commuters, families, and sensitive users when pollution, heat, or humidity make outdoor time harder.",
        "body": [
            "On poor-air days, the best approach is to reduce strenuous activity and try to move any outdoor time into the highlighted best window — even a one- or two-hour difference can matter.",
            "Families, older adults, and people with asthma should treat rising pollution as a reason to shorten outdoor plans or shift them earlier or later in the day.",
            "Ventilation is also a timing decision. Opening windows briefly during the better period, rather than leaving them open all day, limits pollution entering your home.",
        ],
    },
    "commute-guide": {
        "title": "Commuting through poor air: a practical guide",
        "description": "How to plan your daily commute around AQI and outdoor conditions to reduce exposure.",
        "body": [
            "Commuters in high-density Indian cities are often exposed to some of the worst daily pollution — not because the city-wide AQI is high, but because road-level concentrations near traffic corridors are significantly higher.",
            "The best strategy is to align the walking or cycling segments of your commute with the highlighted best window. Even if you cannot avoid the bus or metro, reducing time on foot during the worst period helps.",
            "Covered transport limits direct pollution exposure. If conditions are poor, prioritise enclosed vehicles over auto-rickshaws for longer distances.",
        ],
    },
}


def _get_cache(request: Request) -> InMemoryTTLCache:
    return request.app.state.cache


def _get_storage(request: Request) -> Storage:
    return request.app.state.storage


def _get_waitlist(request: Request) -> WaitlistService:
    return request.app.state.waitlist_service


@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    settings: Settings = Depends(get_settings),
    cache: InMemoryTTLCache = Depends(_get_cache),
    waitlist: WaitlistService = Depends(_get_waitlist),
) -> Response:
    default_city = get_city(settings.default_city_slug) or list_cities()[0]
    summary, error_message = await load_city_summary(default_city, settings, cache)
    featured_cities = list_cities()[: settings.featured_city_count]
    context = city_template_context(
        request=request,
        settings=settings,
        city=default_city,
        summary=summary,
        error_message=error_message,
        page_title=f"{settings.app_name} | AQI and best time to go outside — Indian cities",
        page_description="Check AQI, outdoor timing, commute guidance, and ventilation advice for major Indian cities on one fast page.",
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
    cache: InMemoryTTLCache = Depends(_get_cache),
    waitlist: WaitlistService = Depends(_get_waitlist),
) -> Response:
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
        page_title=f"{city.name} AQI now — best outdoor time today | {settings.app_name}",
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
    cache: InMemoryTTLCache = Depends(_get_cache),
    waitlist: WaitlistService = Depends(_get_waitlist),
) -> Response:
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
        page_title=f"{city.name} — go now or wait? | {settings.app_name}",
        page_description=f"Compare current and upcoming outdoor conditions in {city.name} to decide the best time to walk, commute, or ventilate.",
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
    waitlist: WaitlistService = Depends(_get_waitlist),
) -> Response:
    selected_city = get_city(city or settings.default_city_slug) or list_cities()[0]
    context = {
        "request": request,
        "now": datetime.now(tz=settings.tz()),
        "app_name": settings.app_name,
        "selected_city": selected_city,
        "all_cities": list_cities(),
        "page_title": f"Alerts demo | {settings.app_name}",
        "page_description": "Explore the UrbanAir alerts demo for AQI-change notifications, best-time reminders, and commute-ready updates.",
        "canonical_url": build_page_url(settings, "/alerts"),
        "status": status,
        "waitlist_count": waitlist.count(),
        "disclaimer": "This demo signup flow stores entries locally for project exploration only.",
    }
    return templates.TemplateResponse(request=request, name="alerts.html", context=context)


@router.get("/guides/{guide_slug}", response_class=HTMLResponse)
async def guide_page(
    guide_slug: str,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> Response:
    guide = GUIDES.get(guide_slug)
    if guide is None:
        raise HTTPException(status_code=404, detail="Guide not found")

    return templates.TemplateResponse(
        request=request,
        name="guide.html",
        context={
            "request": request,
            "now": datetime.now(tz=settings.tz()),
            "app_name": settings.app_name,
            "guide": guide,
            "guide_slug": guide_slug,
            "page_title": f"{guide['title']} | {settings.app_name}",
            "page_description": guide["description"],
            "canonical_url": build_page_url(settings, f"/guides/{guide_slug}"),
            "all_cities": list_cities(),
            "all_guides": [
                {"slug": s, "title": g["title"]} for s, g in GUIDES.items() if s != guide_slug
            ],
        },
    )


@router.get("/sitemap.xml")
async def sitemap(settings: Settings = Depends(get_settings)) -> Response:
    urls = ["/", "/alerts"]
    urls.extend(f"/cities/{city.slug}" for city in list_cities())
    urls.extend(f"/compare/{city.slug}" for city in list_cities())
    urls.extend(f"/guides/{slug}" for slug in GUIDES)
    body = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for path in urls:
        loc = escape(build_page_url(settings, path))
        body.append(f"<url><loc>{loc}</loc></url>")
    body.append("</urlset>")
    return Response("\n".join(body), media_type="application/xml")


@router.get("/robots.txt")
async def robots(settings: Settings = Depends(get_settings)) -> Response:
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {build_page_url(settings, '/sitemap.xml')}\n"
    )
    return PlainTextResponse(content)
