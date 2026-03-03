from datetime import datetime
from pydantic import BaseModel, Field


class HourlyPoint(BaseModel):
    time: datetime
    aqi: float
    temperature: float
    humidity: float
    score: float


class TwoHourWindow(BaseModel):
    start: datetime
    end: datetime
    average_score: float = Field(ge=0)


class DailySummary(BaseModel):
    city: str
    generated_at: datetime
    current_aqi: float
    timeline: list[HourlyPoint]
    best_window: TwoHourWindow
    worst_window: TwoHourWindow
    insight: str
