# UrbanAir

UrbanAir is a lightweight single-page web app that answers three questions at a glance:

1. How bad is the air right now?
2. When is the best time to go outside today?
3. What should I do based on current conditions?

The MVP focuses on Mumbai, uses live AQI and weather data, and keeps the interface readable on one screen.

## Features

- Current AQI card with plain-language severity
- Outdoor Score on a 0-10 scale
- Prominent Best Time Today and Time To Avoid cards
- 24-hour timeline chart with good, moderate, and poor segments
- Highlighted best and worst 2-hour windows
- Rule-based Urban Insight with no AI APIs
- Dynamic activity recommendations for:
  - Walking
  - Running
  - Cycling
  - Window Ventilation
- In-memory 1-hour caching for fetched and computed results

## How Outdoor Score Works

UrbanAir computes an internal stress score using:

`(normalized_AQI * 0.6) + (temperature_stress * 0.2) + (humidity_stress * 0.2)`

That value is converted into a user-facing Outdoor Score from `0` to `10`, where:

- `8-10` means conditions are generally good
- `4.5-7.9` means conditions are moderate
- `0-4.4` means conditions are poor

AQI has the highest weight because breathing conditions matter most.

## How Urban Insight Works

Urban Insight is generated with simple rules based on:

- current AQI severity
- short-term AQI trend
- temperature discomfort
- humidity trapping pollutants
- wind helping or failing to disperse pollution

Examples include identifying when pollution is rising, when heat makes outdoor time harder, and when breezier conditions may improve air quality.

## Project Structure

```text
urbanair/
|-- main.py
|-- config.py
|-- routers/
|   `-- summary.py
|-- services/
|   |-- aqi_service.py
|   |-- weather_service.py
|   |-- scoring_service.py
|   |-- insight_service.py
|   `-- activity_service.py
|-- cache/
|   `-- cache_manager.py
|-- models/
|   `-- response_models.py
|-- templates/
|   `-- index.html
`-- static/
    |-- styles.css
    `-- chart.js
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
```

## Running Locally

```powershell
uvicorn urbanair.main:app --host 127.0.0.1 --port 8000
```

Open:

`http://127.0.0.1:8000`

## Notes

- Default city is Mumbai.
- No database is used in the MVP.
- Cache is in-process memory with a 1-hour TTL.
- OpenWeather falls back from `3.0/onecall` to `2.5/forecast` for free-tier compatibility.

## Future Roadmap

- Multi-city support with configurable routes and city metadata
- Smarter historical trend handling
- Native Android app focused on quick local notifications
