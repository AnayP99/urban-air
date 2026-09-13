"""Unit tests for WeatherService interpolation and parsing."""
from datetime import datetime, timezone

from urbanair.config import Settings
from urbanair.services.weather_service import WeatherService


def test_expand_3h_to_hourly_empty() -> None:
    assert WeatherService._expand_3h_to_hourly([]) == []


def test_expand_3h_to_hourly_single_point() -> None:
    base = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    point = {"time": base, "temperature": 25.0, "humidity": 60.0, "wind_speed": 3.0}
    expanded = WeatherService._expand_3h_to_hourly([point])
    assert len(expanded) == 3
    assert expanded[0]["temperature"] == 25.0
    assert expanded[1]["time"] == base.replace(hour=13)


def test_expand_3h_to_hourly_multiple_points() -> None:
    base = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    p1 = {"time": base, "temperature": 20.0, "humidity": 50.0, "wind_speed": 2.0}
    p2 = {"time": base.replace(hour=15), "temperature": 26.0, "humidity": 65.0, "wind_speed": 5.0}

    expanded = WeatherService._expand_3h_to_hourly([p1, p2])
    # 3 intermediate steps + 1 final anchor = 4 points total
    assert len(expanded) == 4
    assert expanded[0]["temperature"] == 20.0
    assert expanded[0]["time"] == base
    assert expanded[1]["time"] == base.replace(hour=13)
    assert 20.0 < expanded[1]["temperature"] < 26.0
    assert expanded[-1]["temperature"] == 26.0
    assert expanded[-1]["time"] == base.replace(hour=15)


def test_parse_onecall_hourly() -> None:
    settings = Settings()
    svc = WeatherService(settings)
    payload = {
        "hourly": [
            {
                "dt": 1770000000,
                "temp": 28.5,
                "humidity": 55.0,
                "wind_speed": 4.2,
            }
        ]
    }
    parsed = svc._parse_onecall_hourly(payload, settings.tz())
    assert len(parsed) == 1
    assert parsed[0]["temperature"] == 28.5
    assert parsed[0]["humidity"] == 55.0
    assert parsed[0]["wind_speed"] == 4.2

