"""JSON API routes for the UrbanAir application."""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from urbanair.cache.cache_manager import InMemoryTTLCache
from urbanair.cities import get_city, list_cities
from urbanair.config import Settings, get_settings
from urbanair.models.response_models import (
    AlertSignupRequest,
    AnalyticsEventRequest,
    CityListItem,
    HealthResponse,
)
from urbanair.routers._context import load_city_summary
from urbanair.services.analytics_service import AnalyticsService
from urbanair.services.waitlist_service import WaitlistService
from urbanair.storage import Storage

router = APIRouter(prefix="/api", tags=["api"])

_start_time = time.monotonic()


def _get_cache(request: Request) -> InMemoryTTLCache:
    return request.app.state.cache


def _get_storage(request: Request) -> Storage:
    return request.app.state.storage


def _get_analytics(request: Request) -> AnalyticsService:
    return request.app.state.analytics_service


def _get_waitlist(request: Request) -> WaitlistService:
    return request.app.state.waitlist_service


@router.get("/health", response_model=HealthResponse)
async def health(
    settings: Settings = Depends(get_settings),
    cache: InMemoryTTLCache = Depends(_get_cache),
) -> HealthResponse:
    """Structured health-check endpoint."""
    return HealthResponse(
        ok=True,
        app=settings.app_name,
        version=settings.app_version,
        cache_size=cache.size(),
        uptime_seconds=round(time.monotonic() - _start_time, 1),
    )


@router.get("/cities", response_model=list[CityListItem])
async def list_cities_api() -> list[CityListItem]:
    """Return metadata for all supported cities."""
    return [
        CityListItem(slug=c.slug, name=c.name, state=c.state, lat=c.lat, lon=c.lon)
        for c in list_cities()
    ]


@router.get("/cities/{city_slug}/summary")
async def city_summary_api(
    city_slug: str,
    settings: Settings = Depends(get_settings),
    cache: InMemoryTTLCache = Depends(_get_cache),
) -> JSONResponse:
    """Return the full DailySummary JSON for a city."""
    city = get_city(city_slug)
    if city is None:
        raise HTTPException(status_code=404, detail="City not found")
    summary, error_message = await load_city_summary(city, settings, cache)
    if summary is None:
        return JSONResponse(status_code=503, content={"city": city.slug, "error": error_message})
    return JSONResponse({
        "city": city.slug,
        "name": city.name,
        "state": city.state,
        "summary": summary.model_dump(mode="json"),
    })


@router.post("/events")
async def track_event(
    payload: AnalyticsEventRequest,
    service: AnalyticsService = Depends(_get_analytics),
) -> dict:
    """Record a client-side analytics event."""
    service.track(payload.event_name, payload.city_slug)
    return {"ok": True}


@router.post("/alerts")
async def signup_alert(
    payload: AlertSignupRequest,
    service: WaitlistService = Depends(_get_waitlist),
    analytics: AnalyticsService = Depends(_get_analytics),
) -> dict:
    """Sign up an email address for AQI alerts for a given city."""
    city = get_city(payload.city_slug)
    if city is None:
        raise HTTPException(status_code=404, detail="City not found")
    email = payload.email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    service.add(email, city.slug)
    analytics.track("alert_signup", city.slug)
    return {"ok": True, "city": city.slug, "waitlist_count": service.count()}
