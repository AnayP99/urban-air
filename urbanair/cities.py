"""City registry — configuration and lookup for all supported Indian cities.

City data is stored in cities.yaml (sibling of this file) and loaded once at
import time.  Adding a new city requires only a YAML entry; no Python changes.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_CITIES_YAML = Path(__file__).parent / "cities.yaml"


@dataclass(frozen=True)
class CityFAQ:
    question: str
    answer: str


@dataclass(frozen=True)
class CityConfig:
    slug: str
    name: str
    state: str
    lat: float
    lon: float
    timezone: str
    hero_title: str
    meta_description: str
    intro: str
    commuter_tip: str
    sensitive_tip: str
    affiliate_focus: str
    related_slugs: tuple[str, ...]
    faqs: tuple[CityFAQ, ...]


def _load_registry() -> dict[str, CityConfig]:
    """Parse cities.yaml and return a slug-keyed dict of CityConfig objects."""
    with _CITIES_YAML.open(encoding="utf-8") as fh:
        data: dict[str, Any] = yaml.safe_load(fh)

    registry: dict[str, CityConfig] = {}
    for entry in data.get("cities", []):
        faqs = tuple(
            CityFAQ(question=faq["question"], answer=faq["answer"])
            for faq in entry.get("faqs", [])
        )
        city = CityConfig(
            slug=entry["slug"],
            name=entry["name"],
            state=entry["state"],
            lat=float(entry["lat"]),
            lon=float(entry["lon"]),
            timezone=entry["timezone"],
            hero_title=entry["hero_title"],
            meta_description=entry["meta_description"],
            intro=entry["intro"],
            commuter_tip=entry["commuter_tip"],
            sensitive_tip=entry["sensitive_tip"],
            affiliate_focus=entry.get("affiliate_focus", ""),
            related_slugs=tuple(str(s) for s in entry.get("related_slugs", [])),
            faqs=faqs,
        )
        registry[city.slug] = city
    return registry


CITY_REGISTRY: dict[str, CityConfig] = _load_registry()


def list_cities() -> list[CityConfig]:
    """Return all cities sorted alphabetically by name."""
    return sorted(CITY_REGISTRY.values(), key=lambda c: c.name)


def get_city(slug: str) -> CityConfig | None:
    """Look up a city by its URL slug. Returns None if not found."""
    return CITY_REGISTRY.get(slug.lower())
