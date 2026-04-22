from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class WatchEvent:
    watched_on: date | None = None
    rewatch: bool = False


@dataclass
class FilmRecord:
    film_id: str
    title: str
    year: int | None = None
    letterboxd_uri: str | None = None
    ratings: list[float] = field(default_factory=list)
    watch_events: list[WatchEvent] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def watch_count(self) -> int:
        return len(self.watch_events) if self.watch_events else 1

    @property
    def average_rating(self) -> float | None:
        if not self.ratings:
            return None
        return sum(self.ratings) / len(self.ratings)

    def as_export_row(self) -> dict[str, Any]:
        return {
            "film_id": self.film_id,
            "title": self.title,
            "year": self.year,
            "letterboxd_uri": self.letterboxd_uri,
            "watch_count": self.watch_count,
            "ratings_count": len(self.ratings),
            "average_rating": round(self.average_rating, 3) if self.average_rating is not None else None,
            "genres": ", ".join(self.metadata.get("genres", [])),
            "directors": ", ".join(self.metadata.get("directors", [])),
            "actors": ", ".join(self.metadata.get("actors", [])),
            "runtime_minutes": self.metadata.get("runtime_minutes"),
            "imdb_id": self.metadata.get("imdb_id"),
        }
