"""Pydantic response and request models for the UrbanAir API."""
from __future__ import annotations

from datetime import datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class HourlyPoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    time: datetime
    aqi: float
    temperature: float
    humidity: float
    wind_speed: float
    score: float
    outdoor_score: float


class ActivityRecommendation(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    icon: str  # emoji icon for the frontend
    status: str  # "Recommended" | "Okay" | "Avoid"
    note: str


class TwoHourWindow(BaseModel):
    model_config = ConfigDict(frozen=True)

    start: datetime
    end: datetime
    average_score: float = Field(ge=0)


class DailySummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    city: str
    generated_at: datetime
    current_aqi: float
    current_outdoor_score: float
    current_temperature: float = 0.0
    current_humidity: float = 0.0
    current_wind_speed: float = 0.0
    timeline: list[HourlyPoint]
    best_window: TwoHourWindow
    worst_window: TwoHourWindow
    insight: str
    activities: list[ActivityRecommendation]


class CityListItem(BaseModel):
    """Lightweight city summary for the /api/cities list endpoint."""
    model_config = ConfigDict(frozen=True)

    slug: str
    name: str
    state: str
    lat: float
    lon: float


class HealthResponse(BaseModel):
    """Structured health-check response."""
    ok: bool
    app: str
    version: str
    cache_size: int
    uptime_seconds: float


class AlertSignupRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    city_slug: str = Field(min_length=2, max_length=64)


class AnalyticsEventRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event_name: str = Field(
        validation_alias=AliasChoices("event_name", "event"),
        min_length=1,
        max_length=64,
    )
    city_slug: str | None = Field(
        default=None,
        validation_alias=AliasChoices("city_slug", "city"),
        max_length=64,
    )
