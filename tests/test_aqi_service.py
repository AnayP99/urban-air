"""Unit tests for AQIService and EPA PM2.5 to AQI conversion."""
import pytest
from urbanair.services.aqi_service import AQIService, pm25_to_aqi


def test_pm25_to_aqi_breakpoints() -> None:
    # Good range (0-50)
    assert pm25_to_aqi(0.0) == 0.0
    assert pm25_to_aqi(6.0) == 25.0
    assert pm25_to_aqi(12.0) == 50.0

    # Moderate range (51-100)
    assert pm25_to_aqi(23.75) == 75.5
    assert pm25_to_aqi(35.4) == 100.0

    # Unhealthy for sensitive groups (101-150)
    assert pm25_to_aqi(55.4) == 150.0

    # Unhealthy (151-200)
    assert pm25_to_aqi(150.4) == 200.0

    # Very Unhealthy (201-300)
    assert pm25_to_aqi(250.4) == 300.0

    # Hazardous (> 300)
    assert pm25_to_aqi(500.4) == 500.0
    assert pm25_to_aqi(600.0) == 500.0  # capped


def test_to_float() -> None:
    assert AQIService._to_float(45, fallback=0.0) == 45.0
    assert AQIService._to_float("52.3", fallback=0.0) == 52.3
    assert AQIService._to_float(None, fallback=10.0) == 10.0
    assert AQIService._to_float("invalid", fallback=99.0) == 99.0

