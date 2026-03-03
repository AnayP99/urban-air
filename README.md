# UrbanAir MVP

UrbanAir helps people in Mumbai pick the best 2-hour window today to step outside, using:
- AQI (WAQI)
- Temperature (OpenWeather)
- Humidity (OpenWeather)

The interface is designed for simple interpretation: clear "best time", "avoid time", and a visual comfort trend.

## Highlights
- FastAPI backend with Jinja2 templates
- Dark, high-contrast, mobile-friendly UI
- Hourly in-memory caching (no database)
- Simple architecture for future multi-city expansion
- Automatic OpenWeather fallback:
  - Try `3.0/onecall`
  - Fall back to `2.5/forecast` for free-tier keys

## How decision logic works
UrbanAir calculates an hourly stress score:

`score = (normalized_AQI * 0.6) + (temperature_stress * 0.2) + (humidity_stress * 0.2)`

Lower score is better. The app computes rolling 2-hour windows and shows:
- Best 2-hour window (lowest average score)
- Worst 2-hour window (highest average score)

The UI emphasizes user-friendly labels and comfort percentage instead of raw math details.

## Project structure
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
|   `-- insight_service.py
|-- cache/
|   `-- cache_manager.py
|-- models/
|   `-- response_models.py
`-- templates/
    `-- index.html
```

## Setup (Windows PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env`:
```env
WAQI_API_KEY=your_waqi_token
OPENWEATHER_API_KEY=your_openweather_api_key
APP_NAME=UrbanAir
APP_DEBUG=false
```

Run:
```powershell
uvicorn urbanair.main:app --host 127.0.0.1 --port 8000
```

Open:
- `http://127.0.0.1:8000`

## Notes
- Default city is Mumbai (`config.py`).
- No database is used in MVP.
- Cache is per-process memory with 1-hour TTL.
