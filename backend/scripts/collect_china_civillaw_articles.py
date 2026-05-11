from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from legal_crawler.china_civillaw import DEFAULT_LIST_URLS, CivilLawConfig, crawl_civillaw_articles


DEFAULT_OUTPUT_ROOT = Path("knowledge") / "groups" / "law" / "documents" / "cn" / "civillaw"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect raw HTML articles from Chinese Civil and Commercial Law website.")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--max-records", type=int, default=120)
    parser.add_argument("--min-year", type=int, default=2022)
    parser.add_argument("--sleep-seconds", type=float, default=0.1)
    parser.add_argument("--trust-env", action="store_true")
    return parser.parse_args()


def resolve_backend_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return BACKEND_DIR / path


def main() -> int:
    args = parse_args()
    config = CivilLawConfig(
        output_root=resolve_backend_path(args.output_root),
        list_urls=list(DEFAULT_LIST_URLS),
        max_records=args.max_records,
        min_year=args.min_year,
        sleep_seconds=args.sleep_seconds,
        trust_env=args.trust_env,
    )
    summary = crawl_civillaw_articles(config)
    print(f"Output root: {summary.output_root}")
    print(f"Articles seen: {summary.articles_seen}")
    print(f"Articles written: {summary.articles_written}")
    print(f"Skipped existing: {summary.skipped_existing}")
    print(f"Skipped year: {summary.skipped_year}")
    print(f"Skipped errors: {summary.skipped_errors}")
    print(f"Manifest: {summary.manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
