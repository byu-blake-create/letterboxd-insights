from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from .models import FilmRecord


def write_outputs(records: dict[str, FilmRecord], insights: dict, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    films_csv = output_dir / "films_enriched.csv"
    films_json = output_dir / "films_enriched.json"
    insights_json = output_dir / "insights.json"
    insights_html = output_dir / "insights.html"

    _write_films_csv(records, films_csv)
    _write_json([r.as_export_row() for r in records.values()], films_json)
    _write_json(insights, insights_json)
    insights_html.write_text(render_html(insights), encoding="utf-8")

    return {
        "films_csv": films_csv,
        "films_json": films_json,
        "insights_json": insights_json,
        "insights_html": insights_html,
    }


def _write_films_csv(records: dict[str, FilmRecord], path: Path) -> None:
    rows = [r.as_export_row() for r in records.values()]
    fieldnames = [
        "film_id",
        "title",
        "year",
        "letterboxd_uri",
        "watch_count",
        "ratings_count",
        "average_rating",
        "genres",
        "directors",
        "actors",
        "runtime_minutes",
        "imdb_id",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(data, path: Path) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def render_html(insights: dict) -> str:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def section(title: str, items: list[dict], key_name: str = "name") -> str:
        if not items:
            return f"<h3>{escape(title)}</h3><p>No data.</p>"
        li = "".join(
            f"<li><span>{escape(str(item.get(key_name, '')))}</span><strong>{escape(str(item.get('count', '')))}</strong></li>"
            for item in items
        )
        return f"<h3>{escape(title)}</h3><ul>{li}</ul>"

    summary = insights.get("summary", {})

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Letterboxd Insights</title>
  <style>
    body {{ font-family: Georgia, serif; margin: 2rem auto; max-width: 980px; padding: 0 1rem; background: #f5f2ea; color: #242424; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(220px,1fr)); gap: 0.75rem; }}
    .card {{ background: #fffdf8; border: 1px solid #d8d1c2; border-radius: 10px; padding: 0.85rem; }}
    h1,h2,h3 {{ margin: 0.5rem 0; }}
    ul {{ list-style: none; margin: 0.5rem 0 1rem 0; padding: 0; }}
    li {{ display: flex; justify-content: space-between; border-bottom: 1px dashed #e7e1d6; padding: 0.35rem 0; gap: 0.75rem; }}
    small {{ color: #666; }}
  </style>
</head>
<body>
  <h1>Letterboxd Insights</h1>
  <small>Generated {escape(generated)}</small>
  <h2>Summary</h2>
  <div class="grid">
    <div class="card"><strong>Total Films</strong><div>{summary.get('total_films', 0)}</div></div>
    <div class="card"><strong>Total Watches</strong><div>{summary.get('total_watches', 0)}</div></div>
    <div class="card"><strong>Total Ratings</strong><div>{summary.get('total_ratings', 0)}</div></div>
    <div class="card"><strong>Average Rating</strong><div>{summary.get('average_rating', 'n/a')}</div></div>
    <div class="card"><strong>Total Runtime (hours)</strong><div>{summary.get('total_runtime_hours', 0)}</div></div>
  </div>

  {section('Top Genres', insights.get('top_genres', []))}
  {section('Top Directors', insights.get('top_directors', []))}
  {section('Top Actors', insights.get('top_actors', []))}
  {section('Yearly Watch Breakdown', insights.get('yearly_watch_breakdown', []))}
  {section('Rating Distribution', insights.get('rating_distribution', []))}
</body>
</html>
"""
    return html
