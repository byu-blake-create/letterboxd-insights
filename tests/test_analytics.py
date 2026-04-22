from letterboxd_insights.analytics import compute_insights
from letterboxd_insights.models import FilmRecord


def test_compute_insights_core_metrics() -> None:
    film1 = FilmRecord(film_id="a", title="A", year=2010, ratings=[4.0, 5.0], metadata={
        "genres": ["Sci-Fi"],
        "directors": ["Dir1"],
        "actors": ["Actor1", "Actor2"],
        "runtime_minutes": 120,
    })
    film2 = FilmRecord(film_id="b", title="B", year=2019, ratings=[3.0], metadata={
        "genres": ["Drama"],
        "directors": ["Dir2"],
        "actors": ["Actor2"],
        "runtime_minutes": 90,
    })

    insights = compute_insights({"a": film1, "b": film2})

    assert insights["summary"]["total_films"] == 2
    assert insights["summary"]["total_ratings"] == 3
    assert insights["summary"]["average_rating"] == 4.0
    assert insights["summary"]["total_runtime_minutes"] == 210

    top_genres = insights["top_genres"]
    assert top_genres[0]["name"] in {"Sci-Fi", "Drama"}
