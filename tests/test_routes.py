"""Integration tests for UrbanAir page and API routes."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from urbanair.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client: TestClient) -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_api_health(client: TestClient) -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "version" in data
    assert "cache_size" in data
    assert "uptime_seconds" in data


def test_api_cities_list(client: TestClient) -> None:
    resp = client.get("/api/cities")
    assert resp.status_code == 200
    cities = resp.json()
    assert isinstance(cities, list)
    assert len(cities) >= 20
    assert all("slug" in c and "name" in c and "state" in c for c in cities)


def test_api_events_standard_payload(client: TestClient) -> None:
    resp = client.post("/api/events", json={"event_name": "test_click", "city_slug": "mumbai"})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_api_events_alias_payload(client: TestClient) -> None:
    resp = client.post("/api/events", json={"event": "page_view", "city": "delhi"})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_api_alerts_valid_signup(client: TestClient) -> None:
    resp = client.post("/api/alerts", json={"email": "commuter@example.com", "city_slug": "mumbai"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["city"] == "mumbai"
    assert "waitlist_count" in data


def test_api_alerts_invalid_email(client: TestClient) -> None:
    resp = client.post("/api/alerts", json={"email": "not-an-email", "city_slug": "mumbai"})
    assert resp.status_code == 422


def test_api_alerts_invalid_city(client: TestClient) -> None:
    resp = client.post("/api/alerts", json={"email": "user@example.com", "city_slug": "atlantis"})
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/json")


def test_api_city_summary_not_found_returns_json(client: TestClient) -> None:
    resp = client.get("/api/cities/nonexistent-city/summary")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/json")
    data = resp.json()
    assert "detail" in data


def test_sitemap(client: TestClient) -> None:
    resp = client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "<urlset" in resp.text
    assert "/cities/mumbai" in resp.text


def test_robots(client: TestClient) -> None:
    resp = client.get("/robots.txt")
    assert resp.status_code == 200
    assert "User-agent" in resp.text
    assert "Sitemap:" in resp.text


def test_404_on_unknown_web_city_returns_html(client: TestClient) -> None:
    resp = client.get("/cities/this-city-does-not-exist")
    assert resp.status_code == 404
    assert "text/html" in resp.headers["content-type"]
    assert "Page not found" in resp.text


def test_404_on_unknown_guide(client: TestClient) -> None:
    resp = client.get("/guides/nonexistent-guide")
    assert resp.status_code == 404
    assert "text/html" in resp.headers["content-type"]


def test_surat_page_renders_successfully(client: TestClient) -> None:
    resp = client.get("/cities/surat")
    assert resp.status_code == 200
    assert "Surat" in resp.text
