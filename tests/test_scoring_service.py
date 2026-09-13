"""Unit tests for the ScoringService."""
import pytest
from urbanair.services.scoring_service import ScoringService


@pytest.fixture
def svc() -> ScoringService:
    return ScoringService()


def test_normalize_aqi_clamps(svc: ScoringService) -> None:
    assert svc.normalize_aqi(0) == 0.0
    assert svc.normalize_aqi(300) == 1.0
    assert svc.normalize_aqi(600) == 1.0  # clamped


def test_ideal_conditions_give_high_score(svc: ScoringService) -> None:
    # AQI=20, temp=24°C, humidity=50%, light wind
    raw = svc.combined_score(aqi=20, temp_c=24.0, humidity=50.0, wind_speed_ms=0.0)
    score = svc.outdoor_score(raw)
    assert score >= 8.5, f"Expected high outdoor score, got {score}"


def test_very_bad_conditions_give_low_score(svc: ScoringService) -> None:
    # AQI=250, temp=42°C, humidity=85%, no wind
    raw = svc.combined_score(aqi=250, temp_c=42.0, humidity=85.0, wind_speed_ms=0.0)
    score = svc.outdoor_score(raw)
    assert score <= 3.0, f"Expected low outdoor score, got {score}"


def test_wind_relief_improves_score(svc: ScoringService) -> None:
    raw_calm = svc.combined_score(aqi=150, temp_c=30.0, humidity=60.0, wind_speed_ms=0.0)
    raw_breezy = svc.combined_score(aqi=150, temp_c=30.0, humidity=60.0, wind_speed_ms=7.0)
    assert raw_breezy < raw_calm, "Breezy should have lower (better) stress score"


def test_aqi_labels(svc: ScoringService) -> None:
    assert svc.aqi_label(25) == "Good"
    assert svc.aqi_label(75) == "Moderate"
    assert svc.aqi_label(130) == "Unhealthy for Sensitive Groups"
    assert svc.aqi_label(175) == "Unhealthy"
    assert svc.aqi_label(250) == "Very Unhealthy"


def test_outdoor_label(svc: ScoringService) -> None:
    assert svc.outdoor_label(9.0) == "Good"
    assert svc.outdoor_label(6.0) == "Moderate"
    assert svc.outdoor_label(3.0) == "Poor"


def test_compute_windows_returns_best_and_worst(svc: ScoringService) -> None:
    from datetime import datetime, timezone
    from urbanair.models.response_models import HourlyPoint

    base = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)
    points = [
        HourlyPoint(time=base, aqi=50, temperature=24, humidity=50, wind_speed=2, score=0.1, outdoor_score=9.0),
        HourlyPoint(time=base.replace(hour=9), aqi=120, temperature=35, humidity=80, wind_speed=0, score=0.7, outdoor_score=3.0),
        HourlyPoint(time=base.replace(hour=10), aqi=80, temperature=28, humidity=60, wind_speed=3, score=0.3, outdoor_score=7.0),
    ]
    best, worst = svc.compute_windows(points)
    assert best.average_score < worst.average_score
