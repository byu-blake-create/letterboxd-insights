# Letterboxd Insights

CLI-first Python analytics tool for Letterboxd export CSV files.

It ingests one or more Letterboxd CSV exports, optionally enriches films with metadata (OMDb), computes analytics, and writes:

- human-readable HTML report
- machine-readable JSON insights
- enriched film-level CSV and JSON

## Why This Architecture

This project uses a Python pipeline instead of n8n:

- better fit for deterministic data processing and analytics
- easier local-first iteration with tests
- simple path to scheduled runs later (cron/systemd/GitHub Actions)
- provider abstraction for metadata enrichment without coupling core analytics to one API

Pipeline stages:

1. ingest (`ingest.py`)
2. enrich (`enrich.py`)
3. analytics (`analytics.py`)
4. report (`report.py`)

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Usage

### Basic run

```bash
letterboxd-insights --input /path/to/letterboxd-exports --output ./output
```

### With OMDb enrichment

```bash
export OMDB_API_KEY=your_key_here
letterboxd-insights --input /path/to/letterboxd-exports --output ./output --enrich auto
```

### Explicit no enrichment

```bash
letterboxd-insights --input /path/to/letterboxd-exports --output ./output --enrich none
```

## Example Run

A sample dataset is included in `examples/sample_export`.

```bash
letterboxd-insights --input examples/sample_export --output examples/sample_output --enrich none
```

Outputs:

- `examples/sample_output/insights.html`
- `examples/sample_output/insights.json`
- `examples/sample_output/films_enriched.csv`
- `examples/sample_output/films_enriched.json`

## Metrics Included

- top genres
- top actors
- top directors
- yearly watch breakdown
- monthly watch breakdown
- rating distribution
- top rated films
- most rewatched films
- runtime summaries and extremes
- decade library breakdown

## IMDb / Metadata Notes

Direct public IMDb API access is limited. This project avoids brittle scraping and uses a provider abstraction.

Current provider:

- OMDb API (optional)

You can add other providers later without changing ingestion/analytics logic.

## Testing

```bash
pytest
```

## Security + Reliability

- no secrets in repo (`.env` and keys are local-only)
- metadata request delay and cache support
- cache file defaults to `<output>/metadata_cache.json`

## Known Limits

- Letterboxd export formats can vary; field aliases cover common variants but may need extension.
- Without metadata enrichment, genre/actor/director insights may be sparse.
- API rate limits depend on your metadata provider key and plan.
