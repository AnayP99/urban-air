"""Application settings loaded from environment variables and .env."""
from __future__ import annotations

from datetime import timedelta, timezone, tzinfo
from functools import lru_cache
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    app_name: str = Field(default="UrbanAir", alias="APP_NAME")
    app_version: str = "0.2.0"
    debug: bool = Field(default=False, alias="APP_DEBUG")

    @field_validator("debug", mode="before")
    @classmethod
    def _parse_debug(cls, v: Any) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in ("true", "1", "yes", "on", "debug")
        return bool(v)
    site_url: str = Field(default="http://127.0.0.1:8000", alias="SITE_URL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    waqi_api_key: str = Field(default="", alias="WAQI_API_KEY")
    openweather_api_key: str = Field(default="", alias="OPENWEATHER_API_KEY")

    waqi_base_url: str = "https://api.waqi.info"
    openweather_base_url: str = "https://api.openweathermap.org"

    # Mumbai defaults; city config is driven by cities.yaml.
    default_city_name: str = "Mumbai"
    default_city_slug: str = "mumbai"
    default_city_lat: float = 19.0760
    default_city_lon: float = 72.8777
    timezone: str = "Asia/Kolkata"
    featured_city_count: int = 20
    storage_path: str = Field(default="data/urbanair.db", alias="APP_STORAGE_PATH")

    cache_ttl_seconds: int = 3600

    model_config = SettingsConfigDict(
        env_file=str(_DEFAULT_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        populate_by_name=True,
        extra="ignore",
    )

    def tz(self) -> tzinfo:
        """Return the configured timezone, falling back to IST (+05:30) if IANA data is missing."""
        try:
            return ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError:
            return timezone(timedelta(hours=5, minutes=30))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    return Settings()
