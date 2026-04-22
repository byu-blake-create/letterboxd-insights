from pathlib import Path

from letterboxd_insights.ingest import load_letterboxd_exports, parse_rating


def test_parse_rating_variants() -> None:
    assert parse_rating("4.5") == 4.5
    assert parse_rating("4/5") == 4.0
    assert parse_rating("★★★★½") == 4.5
    assert parse_rating("") is None


def test_load_letterboxd_exports_merges_files() -> None:
    fixture_dir = Path(__file__).parent / "fixtures"
    records = load_letterboxd_exports(fixture_dir)

    assert len(records) == 2
    interstellar = records["interstellar"]
    assert interstellar.title == "Interstellar"
    assert interstellar.watch_count == 2
    assert interstellar.average_rating == 4.5

    dark_knight = records["the-dark-knight"]
    assert dark_knight.watch_count == 1
    assert dark_knight.average_rating == 4.5
