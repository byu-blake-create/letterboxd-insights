from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path

from .models import FilmRecord, WatchEvent

FIELD_ALIASES = {
    "title": {"name", "title", "film", "film_name", "movie"},
    "year": {"year", "release_year", "releaseyear"},
    "rating": {"rating", "your_rating", "stars", "star_rating"},
    "date": {"date", "watched_date", "watched", "diary_date", "watched_on"},
    "uri": {"letterboxd_uri", "letterboxd_url", "uri", "url", "link"},
    "rewatch": {"rewatch", "rewatched"},
}

STAR_MAP = {
    "★": 1.0,
    "½": 0.5,
}


class IngestError(RuntimeError):
    pass


def discover_csv_files(input_path: Path) -> list[Path]:
    if input_path.is_file() and input_path.suffix.lower() == ".csv":
        return [input_path]
    if not input_path.exists():
        raise IngestError(f"Input path does not exist: {input_path}")
    return sorted(p for p in input_path.rglob("*.csv") if p.is_file())


def load_letterboxd_exports(input_path: Path) -> dict[str, FilmRecord]:
    files = discover_csv_files(input_path)
    if not files:
        raise IngestError(f"No CSV files found under: {input_path}")

    records: dict[str, FilmRecord] = {}

    for csv_file in files:
        with csv_file.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                continue

            normalized_keys = {k: _normalize_key(k) for k in reader.fieldnames}

            for row in reader:
                normalized_row = {
                    normalized_keys.get(k, _normalize_key(k)): (v or "").strip() for k, v in row.items() if k
                }

                title = _first_value(normalized_row, FIELD_ALIASES["title"])
                year = _parse_int(_first_value(normalized_row, FIELD_ALIASES["year"]))
                uri = _first_value(normalized_row, FIELD_ALIASES["uri"])

                if not title and not uri:
                    continue

                film_id = _build_film_id(uri, title, year)
                if film_id not in records:
                    records[film_id] = FilmRecord(
                        film_id=film_id,
                        title=title or "Unknown",
                        year=year,
                        letterboxd_uri=uri,
                    )

                record = records[film_id]
                if title and record.title == "Unknown":
                    record.title = title
                if year and record.year is None:
                    record.year = year
                if uri and not record.letterboxd_uri:
                    record.letterboxd_uri = uri

                rating_raw = _first_value(normalized_row, FIELD_ALIASES["rating"])
                rating = parse_rating(rating_raw)
                if rating is not None:
                    record.ratings.append(rating)

                date_raw = _first_value(normalized_row, FIELD_ALIASES["date"])
                rewatch_raw = _first_value(normalized_row, FIELD_ALIASES["rewatch"])
                watched_on = _parse_date(date_raw)
                rewatch = _parse_bool(rewatch_raw)

                if watched_on is not None or rewatch:
                    record.watch_events.append(WatchEvent(watched_on=watched_on, rewatch=rewatch))

    return records


def parse_rating(raw: str | None) -> float | None:
    if not raw:
        return None
    raw = raw.strip()

    # Numeric ratings like 4.5, 3, 2/5
    if re.fullmatch(r"\d+(\.\d+)?", raw):
        return float(raw)
    if re.fullmatch(r"\d+(\.\d+)?\s*/\s*5", raw):
        return float(raw.split("/")[0].strip())

    # Star glyph ratings like ★★★★½
    if set(raw).issubset({"★", "½"}):
        total = 0.0
        for ch in raw:
            total += STAR_MAP.get(ch, 0.0)
        return total

    return None


def _normalize_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", key.strip().lower()).strip("_")


def _first_value(row: dict[str, str], aliases: set[str]) -> str | None:
    for alias in aliases:
        if alias in row and row[alias]:
            return row[alias]
    return None


def _parse_int(raw: str | None) -> int | None:
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _parse_bool(raw: str | None) -> bool:
    if not raw:
        return False
    return raw.strip().lower() in {"true", "yes", "y", "1", "rewatch", "rewatched"}


def _parse_date(raw: str | None):
    if not raw:
        return None
    raw = raw.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%b %d %Y", "%d %b %Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _build_film_id(uri: str | None, title: str | None, year: int | None) -> str:
    if uri:
        m = re.search(r"/film/([^/]+)/?", uri)
        if m:
            return m.group(1)
        return _slugify(uri)

    safe_title = _slugify(title or "unknown")
    return f"{safe_title}-{year}" if year else safe_title
