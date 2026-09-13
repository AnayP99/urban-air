# UrbanAir 🌿

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.118-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen?logo=pytest&logoColor=white)](tests/)
[![Code Style](https://img.shields.io/badge/Code%20Style-Ruff-black)](https://github.com/astral-sh/ruff)

> **Smart outdoor timing advisor for Indian cities.**  
> Answers the single practical question commuters, runners, and families ask every day:  
> **"Should I step out now, or wait for a better window later today?"**

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Outdoor Score Methodology](#outdoor-score-methodology)
- [Tech Stack](#tech-stack)
- [Project Architecture](#project-architecture)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Running the App](#running-the-app)
- [API Reference](#api-reference)
  - [Health Check](#get-apihealth)
  - [City List](#get-apicities)
  - [City Daily Summary](#get-apicitiescity_slugsummary)
  - [Analytics Events](#post-apievents)
  - [Alerts / Waitlist Signup](#post-apialerts)
- [Adding Cities](#adding-cities)
- [Development & Testing](#development--testing)
- [Disclaimer](#disclaimer)

---

## Overview

Most air-quality applications display raw AQI metrics, complex pollutant breakdown tables, or daily historical averages. However, in major urban hubs across India, air quality, heat, and humidity vary dramatically hour-by-hour.

**UrbanAir** synthesizes real-time and forecasted air quality (WAQI) with meteorological conditions (OpenWeather) to produce an actionable **0–10 Outdoor Score**, highlights the **optimal 2-hour window** of the day, and provides context-aware guidance for daily activities: walking, running, cycling, commuting, and home ventilation.

---

## Key Features

- **⚡ 0–10 Outdoor Score**: Weighted formula factoring in particulate pollution, temperature stress, humidity stress, and wind relief.
- **🕒 Optimal & Avoid Windows**: Pinpoints the best 2-hour block for outdoor errands and flags the most hazardous period in the upcoming 24 hours.
- **📊 24-Hour Interactive Timeline**: Visual bar chart color-coded by EPA AQI tiers with dynamic light/dark mode support and threshold markers.
- **🚶 Activity-Specific Guidance**: Tailored recommendations for walking, running, cycling, public transit commuting, and window ventilation.
- **🧠 Rule-Based Urban Insights**: Deterministic, zero-AI-latency contextual analysis factoring in morning/evening transitions, seasonal inversion traps, and wind dispersion.
- **🌆 20+ Major Indian Cities**: Configured via a clean, decoupled `cities.yaml` registry requiring zero code changes to scale.
- **🌗 Automatic Dark Mode**: First-class responsive CSS design system that respects system `prefers-color-scheme`.
- **🔍 Quick City Autocomplete**: Header search with keyboard navigation and `<datalist>` instant filtering.
- **💾 Local Saved Cities**: Lightweight client-side storage for instant access across sessions.
- **🚀 REST API & SEO Ready**: Structured JSON endpoints, XML sitemap (`/sitemap.xml`), `robots.txt`, and schema.org FAQ markup.

---

## Outdoor Score Methodology

The internal stress score combines environmental stressors into a normalized `[0, 1]` index, inverted to yield a user-friendly `0–10` outdoor rating:

$$\text{Stress} = (W_{\text{aqi}} \cdot S_{\text{aqi}}) + (W_{\text{temp}} \cdot S_{\text{temp}}) + (W_{\text{hum}} \cdot S_{\text{hum}}) - (W_{\text{wind}} \cdot R_{\text{wind}})$$

$$\text{Outdoor Score} = (1 - \text{Stress}) \times 10$$

### Stress Components

| Component | Weight | Target / Benchmark | Formula / Behavior |
|---|:---:|---|---|
| **AQI Stress** | **55%** | Baseline: 0 AQI, Cap: 300 AQI | $S_{\text{aqi}} = \min(1.0, \frac{\text{AQI}}{300})$ |
| **Temperature Stress** | **20%** | Ideal: $24^\circ\text{C}$, Range: $\pm 14^\circ\text{C}$ | $S_{\text{temp}} = \min(1.0, \frac{\|\text{Temp} - 24\|}{14})$ |
| **Humidity Stress** | **18%** | Ideal: $50\%$, Range: $\pm 40\%$ | $S_{\text{hum}} = \min(1.0, \frac{\|\text{Humidity} - 50\|}{40})$ |
| **Wind Relief** | **7%** | Relief threshold: $\ge 5.0\text{ m/s}$ | Provides stress reduction only when $\text{AQI} \ge 50$. |

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python 3.12+, FastAPI, Pydantic v2, Pydantic-Settings, Uvicorn |
| **Templating** | Jinja2 with HTML5 semantic components |
| **Data & Storage** | PyYAML (City Registry), SQLite with WAL journal mode, In-Memory TTL Cache |
| **Frontend** | Vanilla ES Modules (zero external build pipeline), CSS Custom Properties, Chart.js v4 |
| **Testing & Quality** | Pytest, Pytest-Asyncio, HTTPX TestClient, Ruff |

---

## Project Architecture

```text
urban-air/
├── urbanair/
│   ├── cities.yaml              # City metadata & FAQ configuration registry
│   ├── cities.py                # YAML loader with frozen dataclass registry
│   ├── config.py                # Environment-backed Pydantic Settings
│   ├── main.py                  # FastAPI app factory, lifespan DI & error handlers
│   ├── storage.py               # SQLite wrapper with context-managed sessions
│   ├── cache/
│   │   └── cache_manager.py     # Thread-safe in-memory TTL cache
│   ├── models/
│   │   └── response_models.py   # Immutable Pydantic response & request schemas
│   ├── routers/
│   │   ├── _context.py          # Shared presentation & summary context builders
│   │   ├── pages.py             # SSR web views (/, /cities, /compare, /alerts, /guides)
│   │   └── api.py               # REST API endpoints (/api/cities, /api/health, etc.)
│   ├── services/
│   │   ├── aqi_service.py       # WAQI API client with retry & exponential back-off
│   │   ├── weather_service.py   # OpenWeather client with 3h interpolation & fallback
│   │   ├── scoring_service.py   # Mathematical outdoor scoring engine
│   │   ├── insight_service.py   # Rule-based urban insight generator
│   │   ├── activity_service.py  # Recommendation engine for 5 urban activities
│   │   ├── summary_service.py   # Cache-aside orchestrator for daily summaries
│   │   ├── analytics_service.py # Telemetry event tracking & aggregation
│   │   └── waitlist_service.py  # Local demo subscriber & alert management
│   ├── static/
│   │   ├── app.js               # ES module: saved cities, search, form handling
│   │   ├── chart.js             # ES module: Chart.js rendering & dark-mode listener
│   │   └── styles.css           # Responsive design system with dark mode
│   └── templates/               # Jinja2 HTML templates & partials
├── tests/
│   ├── test_scoring_service.py  # Unit tests for scoring calculations
│   ├── test_weather_service.py  # Unit tests for weather parsing & interpolation
│   └── test_routes.py           # Integration tests for web and API routes
├── pyproject.toml               # Project packaging & tooling configuration
├── requirements.txt             # Production dependency manifest
└── README.md                    # Project documentation
```

---

## Getting Started

### Prerequisites

- Python 3.12 or higher
- Git

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/AnayP99/urban-air.git
   cd urban-air
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # Linux / macOS
   python3 -m venv .venv
   source .venv/bin/activate

   # Windows (PowerShell)
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Configuration

Copy `.env.example` to `.env` and configure your API tokens:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# API Keys (Required for live data, optional for dev mode)
WAQI_API_KEY=your_waqi_api_token
OPENWEATHER_API_KEY=your_openweather_api_key

# Application Settings
APP_NAME=UrbanAir
APP_DEBUG=true
SITE_URL=http://127.0.0.1:8000
LOG_LEVEL=INFO
APP_STORAGE_PATH=data/urbanair.db
```

> **Note:** Free API keys can be obtained from:
> - WAQI: [https://aqicn.org/data-platform/token/](https://aqicn.org/data-platform/token/)
> - OpenWeather: [https://openweathermap.org/api](https://openweathermap.org/api)

### Running the App

Start the development server with live reload:

```bash
uvicorn urbanair.main:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser at `http://127.0.0.1:8000`.

---

## API Reference

### `GET /api/health`
Structured health-check reporting uptime, app version, and cache volume.

**Response (`200 OK`):**
```json
{
  "ok": true,
  "app": "UrbanAir",
  "version": "0.2.0",
  "cache_size": 4,
  "uptime_seconds": 128.4
}
```

---

### `GET /api/cities`
Returns an array of all registered Indian cities.

**Response (`200 OK`):**
```json
[
  {
    "slug": "mumbai",
    "name": "Mumbai",
    "state": "Maharashtra",
    "lat": 19.0760,
    "lon": 72.8777
  },
  {
    "slug": "delhi",
    "name": "Delhi",
    "state": "Delhi",
    "lat": 28.6139,
    "lon": 77.2090
  }
]
```

---

### `GET /api/cities/{city_slug}/summary`
Fetches the full daily summary, hourly timeline forecast, score breakdown, and activity guidance.

**Example Request:**
```bash
curl -X GET "http://127.0.0.1:8000/api/cities/mumbai/summary"
```

**Response (`200 OK`):**
```json
{
  "city": "mumbai",
  "name": "Mumbai",
  "state": "Maharashtra",
  "summary": {
    "city": "Mumbai",
    "generated_at": "2026-09-13T19:50:00+05:30",
    "current_aqi": 85.0,
    "current_outdoor_score": 7.4,
    "current_temperature": 28.0,
    "current_humidity": 65.0,
    "current_wind_speed": 4.5,
    "timeline": [
      {
        "time": "2026-09-13T20:00:00+05:30",
        "aqi": 85.0,
        "temperature": 28.0,
        "humidity": 65.0,
        "wind_speed": 4.5,
        "score": 0.26,
        "outdoor_score": 7.4
      }
    ],
    "best_window": {
      "start": "2026-09-13T21:00:00+05:30",
      "end": "2026-09-13T23:00:00+05:30",
      "average_score": 0.22
    },
    "worst_window": {
      "start": "2026-09-14T08:00:00+05:30",
      "end": "2026-09-14T10:00:00+05:30",
      "average_score": 0.58
    },
    "insight": "Air quality is moderate right now. Evening air looks manageable for a walk or light exercise...",
    "activities": [
      {
        "name": "Walking",
        "icon": "🚶",
        "status": "Recommended",
        "note": "Good conditions for a walk or short errand."
      }
    ]
  }
}
```

---

### `POST /api/events`
Captures client-side telemetry events.

**Request Body:**
```json
{
  "event_name": "page_view",
  "city_slug": "mumbai"
}
```

---

### `POST /api/alerts`
Registers an email address for local notification alerts.

**Request Body:**
```json
{
  "email": "commuter@example.com",
  "city_slug": "bengaluru"
}
```

---

## Adding Cities

To register a new city, append an entry to `urbanair/cities.yaml`:

```yaml
  - slug: pune
    name: Pune
    state: Maharashtra
    lat: 18.5204
    lon: 73.8567
    timezone: Asia/Kolkata
    hero_title: "Pune AQI now with today's best outdoor window"
    meta_description: "See Pune AQI, best outdoor time, and practical recommendations."
    intro: "Pune users often need a quick outdoor answer before work or evening plans."
    commuter_tip: "Short trips are often easiest during the highlighted best window."
    sensitive_tip: "If you are sensitive to pollution, check if waiting improves conditions."
    affiliate_focus: "portable air purifiers"
    related_slugs: [mumbai, hyderabad]
    faqs:
      - question: "Is Pune good for cycling today?"
        answer: "Cycling depends on both air quality and heat stress."
```

No Python code changes or database migrations are required. The city becomes active immediately.

---

## Development & Testing

UrbanAir maintains a test suite covering algorithmic scoring, weather forecast interpolation, API routing, and error contract handling.

```bash
# Run test suite
pytest -v

# Run with coverage report
pytest --cov=urbanair tests/

# Run linter
ruff check .

# Run type checker
mypy urbanair/
```

---

## Disclaimer

UrbanAir is built for informational and daily activity planning purposes only. It does not constitute medical, health, or clinical advice. Individuals with respiratory conditions, asthma, cardiovascular concerns, elderly persons, and children should consult local public health advisories and medical professionals when evaluating air pollution exposure.
