from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from legal_crawler import EcfrConfig, crawl_ecfr_sections


DEFAULT_OUTPUT_PATH = Path("storage") / "knowledge" / "legal_corpus" / "ecfr_legal_docs.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect public legal/regulatory sections from the official eCFR API into JSONL."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Output JSONL path, relative to backend/ when not absolute.",
    )
    parser.add_argument("--limit", type=int, default=10_000, help="Maximum number of sections to write.")
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=1.0,
        help="Delay between eCFR title downloads.",
    )
    parser.add_argument(
        "--no-split-by-category",
        action="store_true",
        help="Disable per-category JSONL files.",
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
    return BACKEND_DIR / path


def main() -> int:
    args = parse_args()
    config = EcfrConfig(
        output_path=resolve_output_path(args.output),
        limit=args.limit,
        sleep_seconds=args.sleep_seconds,
        split_by_category=not args.no_split_by_category,
        trust_env=args.trust_env,
    )
    summary = crawl_ecfr_sections(config)

    print(f"Output: {summary.output_path}")
    print(f"Titles fetched: {summary.titles_fetched}")
    print(f"Sections seen: {summary.sections_seen}")
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
