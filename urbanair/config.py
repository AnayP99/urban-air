from functools import lru_cache
from datetime import timedelta, timezone, tzinfo
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class Settings(BaseSettings):
    app_name: str = Field(default="UrbanAir", alias="APP_NAME")
    debug: bool = Field(default=False, alias="APP_DEBUG")
    site_url: str = Field(default="http://127.0.0.1:8000", alias="SITE_URL")

    waqi_api_key: str = Field(default="", alias="WAQI_API_KEY")
    openweather_api_key: str = Field(default="", alias="OPENWEATHER_API_KEY")

    waqi_base_url: str = "https://api.waqi.info"
    openweather_base_url: str = "https://api.openweathermap.org"

    # Mumbai defaults; structured so city config can be externalized later.
    default_city_name: str = "Mumbai"
    default_city_slug: str = "mumbai"
    default_city_lat: float = 19.0760
    default_city_lon: float = 72.8777
    timezone: str = "Asia/Kolkata"
    featured_city_count: int = 20
    storage_path: str = Field(default="data/urbanair.db", alias="APP_STORAGE_PATH")

    cache_ttl_seconds: int = 3600

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        populate_by_name=True,
        extra="ignore",
    )

    def tz(self) -> tzinfo:
        try:
            return ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError:
            # Fallback for hosts without IANA tz database.
            return timezone(timedelta(hours=5, minutes=30))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
