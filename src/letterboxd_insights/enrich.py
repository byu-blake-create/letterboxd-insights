from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from .models import FilmRecord


class MetadataProvider(ABC):
    @abstractmethod
    def fetch(self, title: str, year: int | None) -> dict[str, Any]:
        raise NotImplementedError


class NullProvider(MetadataProvider):
    def fetch(self, title: str, year: int | None) -> dict[str, Any]:
        return {}


class OMDbProvider(MetadataProvider):
    base_url = "https://www.omdbapi.com/"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def fetch(self, title: str, year: int | None) -> dict[str, Any]:
        params = {"apikey": self.api_key, "t": title, "r": "json"}
        if year:
            params["y"] = str(year)

        url = f"{self.base_url}?{urlencode(params)}"
        with urlopen(url, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))

        if payload.get("Response") == "False":
            return {}

        return {
            "genres": _split_csv(payload.get("Genre")),
            "directors": _split_csv(payload.get("Director")),
            "actors": _split_csv(payload.get("Actors")),
            "runtime_minutes": _parse_runtime(payload.get("Runtime")),
            "imdb_id": payload.get("imdbID"),
            "imdb_rating": _parse_float(payload.get("imdbRating")),
        }


def enrich_records(
    records: dict[str, FilmRecord],
    provider: MetadataProvider,
    cache_path: Path | None = None,
    delay_seconds: float = 0.0,
) -> None:
    cache = _load_cache(cache_path) if cache_path else {}

    for record in records.values():
        key = _cache_key(record.title, record.year)
        if key in cache:
            record.metadata.update(cache[key])
            continue

        data = provider.fetch(record.title, record.year)
        if data:
            record.metadata.update(data)
            cache[key] = data

        if delay_seconds:
            time.sleep(delay_seconds)

    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def _cache_key(title: str, year: int | None) -> str:
    return f"{title.strip().lower()}|{year or ''}"


def _load_cache(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _split_csv(raw: str | None) -> list[str]:
    if not raw or raw == "N/A":
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _parse_runtime(raw: str | None) -> int | None:
    if not raw or raw == "N/A":
        return None
    token = raw.split(" ")[0]
    try:
        return int(token)
    except ValueError:
        return None


def _parse_float(raw: str | None) -> float | None:
    if not raw or raw == "N/A":
        return None
    try:
        return float(raw)
    except ValueError:
        return None
