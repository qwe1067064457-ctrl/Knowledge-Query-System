from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from legal_crawler import CourtListenerConfig, crawl_courtlistener_opinions


DEFAULT_OUTPUT_PATH = Path("storage") / "knowledge" / "legal_corpus" / "courtlistener_legal_docs.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect public legal opinions from CourtListener into a JSONL corpus."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Output JSONL path, relative to backend/ when not absolute.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10_000,
        help="Maximum number of API results to inspect.",
    )
    parser.add_argument(
        "--court",
        default=None,
        help="Optional CourtListener court code, for example scotus. Omit to collect across all courts.",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=100,
        help="Requested API page size. Values over 100 are capped to 100.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=75.0,
        help="Delay between API pages. Keep this conservative for public APIs.",
    )
    parser.add_argument(
        "--token-env",
        default="COURTLISTENER_TOKEN",
        help="Environment variable that stores an optional CourtListener API token.",
    )
    parser.add_argument(
        "--include-raw",
        action="store_true",
        help="Also store the raw CourtListener API object. This makes output much larger.",
    )
    parser.add_argument(
        "--split-by-category",
        action="store_true",
        help="Also write one JSONL file per lightweight legal category under by_category/.",
    )
    parser.add_argument(
        "--trust-env",
        action="store_true",
        help="Use proxy and SSL settings from environment variables. Disabled by default.",
    )
    return parser.parse_args()


def resolve_output_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    backend_dir = Path(__file__).resolve().parents[1]
    return backend_dir / path


def main() -> int:
    args = parse_args()
    output_path = resolve_output_path(args.output)

    config = CourtListenerConfig(
        output_path=output_path,
        limit=args.limit,
        court=args.court,
        page_size=args.page_size,
        sleep_seconds=args.sleep_seconds,
        token=os.getenv(args.token_env) or None,
        include_raw=args.include_raw,
        split_by_category=args.split_by_category,
        trust_env=args.trust_env,
    )
    summary = crawl_courtlistener_opinions(config)

    print(f"Output: {summary.output_path}")
    print(f"Fetched: {summary.fetched}")
    print(f"Written: {summary.written}")
    print(f"Skipped duplicate: {summary.skipped_duplicate}")
    print(f"Skipped empty: {summary.skipped_empty}")
    if summary.category_counts:
        print("Categories:")
        for category, count in sorted(summary.category_counts.items()):
            print(f"  {category}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
