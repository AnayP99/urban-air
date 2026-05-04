# UrbanAir

UrbanAir is a lightweight FastAPI app built to help Indian city residents answer one practical question fast: should I go outside now, or wait for a better window later today?

This repository is a public portfolio project and technical demo.

The current codebase turns the original Mumbai-only MVP into a multi-city utility with:

- dedicated city pages such as `/cities/mumbai` and `/cities/delhi`
- compare pages such as `/compare/mumbai`
- an alerts demo page at `/alerts`
- sitemap and robots routes for search indexing
- a JSON summary endpoint at `/api/cities/{slug}/summary`
- SQLite-backed starter analytics event capture and demo signup capture
- mobile-first pages, trust copy, and FAQ content

## Core Features

- Current AQI card with plain-language severity
- Outdoor Score on a `0-10` scale
- Best time today and time to avoid
- 24-hour outdoor timeline chart
- Rule-based Urban Insight with no paid AI dependency
- Activity recommendations for walking, running, cycling, and window ventilation
- Multi-city support driven by a city registry
- Internal links, canonical tags, FAQ markup, `sitemap.xml`, and `robots.txt`
- Feedback and local UX experiments built into the UI

## Project Structure

```text
urbanair/
|-- cities.py
|-- main.py
|-- config.py
|-- storage.py
|-- routers/
|   `-- summary.py
|-- services/
|   |-- activity_service.py
|   |-- analytics_service.py
|   |-- aqi_service.py
|   |-- insight_service.py
|   |-- scoring_service.py
|   |-- summary_service.py
|   |-- waitlist_service.py
|   `-- weather_service.py
|-- cache/
|   `-- cache_manager.py
|-- models/
|   `-- response_models.py
|-- templates/
|   |-- _city_dashboard.html
|   |-- alerts.html
|   |-- base.html
|   |-- city.html
|   |-- compare.html
|   |-- guide.html
|   `-- index.html
`-- static/
    |-- app.js
    |-- chart.js
    `-- styles.css
```

## Setup

### 1. Create and activate a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure environment variables

Create `.env` from `.env.example` and set:

```env
WAQI_API_KEY=your_waqi_token
OPENWEATHER_API_KEY=your_openweather_api_key
APP_NAME=UrbanAir
APP_DEBUG=false
SITE_URL=http://127.0.0.1:8000
APP_STORAGE_PATH=data/urbanair.db
```

## Running Locally

```powershell
uvicorn urbanair.main:app --host 127.0.0.1 --port 8000
```

This is the recommended way to use the project.

Main routes:

- `/`
- `/cities/mumbai`
- `/cities/delhi`
- `/compare/mumbai`
- `/alerts`
- `/guides/understanding-aqi`
- `/api/cities/mumbai/summary`
- `/healthz`
- `/sitemap.xml`
- `/robots.txt`

## Product Notes

- UrbanAir is a local-first code sample built for demonstration and portfolio use.
- A local SQLite file stores demo signups and analytics events when you run the app yourself.
- Cache is still in-process memory with a 1-hour TTL.
- Set `APP_STORAGE_PATH` if you want the SQLite file somewhere specific.
- OpenWeather falls back from `3.0/onecall` to `2.5/forecast` for free-tier compatibility.

## Usage Notes

- The app is intended for local exploration and code review for now.
- There is no deployment configuration included in this repository.

## What To Build Next

- Replace SQLite demo storage with a more durable data layer if needed.
- Add alert workers and scheduled digest jobs if you want to expand the alerts feature set.
- Add historical comparisons for richer city-level trend views.
