from datetime import datetime
from pydantic import BaseModel, Field


class HourlyPoint(BaseModel):
    time: datetime
    aqi: float
    temperature: float
    humidity: float
    wind_speed: float
    score: float
    outdoor_score: float


class ActivityRecommendation(BaseModel):
    name: str
    status: str
    note: str


class TwoHourWindow(BaseModel):
    start: datetime
    end: datetime
    average_score: float = Field(ge=0)


class DailySummary(BaseModel):
    city: str
    generated_at: datetime
    current_aqi: float
    current_outdoor_score: float
    timeline: list[HourlyPoint]
    best_window: TwoHourWindow
    worst_window: TwoHourWindow
    insight: str
    activities: list[ActivityRecommendation]


class AlertSignupRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    city_slug: str = Field(min_length=2, max_length=64)


class AnalyticsEventRequest(BaseModel):
    event_name: str = Field(min_length=2, max_length=64)
    city_slug: str | None = Field(default=None, max_length=64)
