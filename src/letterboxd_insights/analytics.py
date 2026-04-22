from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from statistics import mean

from .models import FilmRecord


def compute_insights(records: dict[str, FilmRecord]) -> dict:
    films = list(records.values())

    total_films = len(films)
    total_watches = sum(f.watch_count for f in films)

    all_ratings = [r for f in films for r in f.ratings]
    avg_rating = round(mean(all_ratings), 3) if all_ratings else None

    rating_distribution = Counter(round(r * 2) / 2 for r in all_ratings)

    genre_counter = Counter()
    actor_counter = Counter()
    director_counter = Counter()
    yearly_counter = Counter()
    monthly_counter = Counter()
    decade_counter = Counter()

    total_runtime_minutes = 0
    runtime_films: list[tuple[str, int]] = []

    for film in films:
        weight = film.watch_count

        for genre in film.metadata.get("genres", []):
            genre_counter[genre] += weight
        for actor in film.metadata.get("actors", []):
            actor_counter[actor] += weight
        for director in film.metadata.get("directors", []):
            director_counter[director] += weight

        for event in film.watch_events:
            if isinstance(event.watched_on, date):
                yearly_counter[event.watched_on.year] += 1
                monthly_counter[event.watched_on.strftime("%Y-%m")] += 1

        if film.year:
            decade_counter[(film.year // 10) * 10] += 1

        runtime = film.metadata.get("runtime_minutes")
        if isinstance(runtime, int) and runtime > 0:
            total_runtime_minutes += runtime * weight
            runtime_films.append((film.title, runtime))

    longest = max(runtime_films, key=lambda x: x[1]) if runtime_films else None
    shortest = min(runtime_films, key=lambda x: x[1]) if runtime_films else None

    rewatch_counts = sorted(
        [
            {"title": f.title, "year": f.year, "watch_count": f.watch_count}
            for f in films
            if f.watch_count > 1
        ],
        key=lambda x: x["watch_count"],
        reverse=True,
    )

    top_rated = sorted(
        [
            {
                "title": f.title,
                "year": f.year,
                "average_rating": round(f.average_rating or 0.0, 3),
                "ratings_count": len(f.ratings),
            }
            for f in films
            if f.average_rating is not None
        ],
        key=lambda x: (x["average_rating"], x["ratings_count"]),
        reverse=True,
    )[:10]

    return {
        "summary": {
            "total_films": total_films,
            "total_watches": total_watches,
            "total_ratings": len(all_ratings),
            "average_rating": avg_rating,
            "total_runtime_minutes": total_runtime_minutes,
            "total_runtime_hours": round(total_runtime_minutes / 60, 2),
        },
        "top_genres": _counter_to_ranked(genre_counter, limit=15),
        "top_actors": _counter_to_ranked(actor_counter, limit=20),
        "top_directors": _counter_to_ranked(director_counter, limit=20),
        "yearly_watch_breakdown": _counter_to_ranked(yearly_counter),
        "monthly_watch_breakdown": _counter_to_ranked(monthly_counter),
        "decade_library_breakdown": _counter_to_ranked(decade_counter),
        "rating_distribution": _counter_to_ranked(rating_distribution),
        "top_rated_films": top_rated,
        "most_rewatched_films": rewatch_counts[:10],
        "runtime_extremes": {
            "longest_film": {"title": longest[0], "runtime_minutes": longest[1]} if longest else None,
            "shortest_film": {"title": shortest[0], "runtime_minutes": shortest[1]} if shortest else None,
        },
    }


def _counter_to_ranked(counter: Counter, limit: int | None = None) -> list[dict]:
    items = counter.most_common(limit)
    return [{"name": str(name), "count": count} for name, count in items]
