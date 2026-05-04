# UrbanAir

UrbanAir is a lightweight FastAPI app built to help Indian city residents answer one practical question fast: should I go outside now, or wait for a better window later today?

The application includes:

- dedicated city pages such as `/cities/mumbai` and `/cities/delhi`
- compare pages such as `/compare/mumbai`
- an alerts page at `/alerts`
- sitemap and robots routes for search indexing
- a JSON summary endpoint at `/api/cities/{slug}/summary`
- SQLite-backed analytics event capture and signup capture
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
- Feedback interactions built into the UI

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

## Running

```powershell
uvicorn urbanair.main:app --host 127.0.0.1 --port 8000
```

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

## Implementation Notes

- A SQLite file stores signup data and analytics events.
- Cache is still in-process memory with a 1-hour TTL.
- Set `APP_STORAGE_PATH` if you want the SQLite file somewhere specific.
- OpenWeather falls back from `3.0/onecall` to `2.5/forecast` for free-tier compatibility.

## Possible Extensions

- Replace SQLite storage with a more durable database layer.
- Add alert workers and scheduled digest jobs.
- Add historical comparisons for richer city-level trend views.
- Expand analytics beyond the built-in event capture flow.
