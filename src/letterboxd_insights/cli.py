from __future__ import annotations

import argparse
import os
from pathlib import Path

from .analytics import compute_insights
from .enrich import NullProvider, OMDbProvider, enrich_records
from .ingest import IngestError, load_letterboxd_exports
from .report import write_outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze Letterboxd CSV exports and generate insights.")
    parser.add_argument("--input", required=True, help="Path to a CSV file or directory containing Letterboxd exports")
    parser.add_argument("--output", default="output", help="Output directory for reports")
    parser.add_argument(
        "--enrich",
        choices=["none", "omdb", "auto"],
        default="auto",
        help="Metadata enrichment strategy (default: auto)",
    )
    parser.add_argument("--omdb-api-key", default=None, help="OMDb API key override (or use OMDB_API_KEY env var)")
    parser.add_argument(
        "--cache",
        default=None,
        help="Cache path for enrichment results (default: <output>/metadata_cache.json)",
    )
    parser.add_argument(
        "--request-delay",
        default=0.2,
        type=float,
        help="Delay in seconds between metadata requests (default: 0.2)",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output).expanduser().resolve()

    try:
        records = load_letterboxd_exports(input_path)
    except IngestError as exc:
        parser.error(str(exc))
        return 2

    provider = NullProvider()
    omdb_key = args.omdb_api_key or os.getenv("OMDB_API_KEY")
    enrich_mode = args.enrich

    if enrich_mode == "omdb":
        if not omdb_key:
            parser.error("--enrich omdb requires --omdb-api-key or OMDB_API_KEY")
            return 2
        provider = OMDbProvider(omdb_key)
    elif enrich_mode == "auto" and omdb_key:
        provider = OMDbProvider(omdb_key)

    cache_path = Path(args.cache).expanduser().resolve() if args.cache else output_dir / "metadata_cache.json"
    enrich_records(records, provider, cache_path=cache_path, delay_seconds=max(args.request_delay, 0.0))

    insights = compute_insights(records)
    output_files = write_outputs(records, insights, output_dir)

    print("Analysis complete.")
    print(f"Films processed: {len(records)}")
    for label, path in output_files.items():
        print(f"{label}: {path}")
    if isinstance(provider, OMDbProvider):
        print("Metadata provider: OMDb")
    else:
        print("Metadata provider: none")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
