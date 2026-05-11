from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from legal_crawler import FlkCrawlConfig, crawl_china_flk
from legal_crawler.china_flk import with_limit_per_category


DEFAULT_OUTPUT_ROOT = Path("knowledge") / "groups" / "law" / "documents" / "cn" / "flk"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect Chinese legal documents from the official National Laws and Regulations Database."
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Output root, relative to backend/ when not absolute.",
    )
    parser.add_argument("--page-size", type=int, default=20)
    parser.add_argument("--sleep-seconds", type=float, default=0.2)
    parser.add_argument("--related-limit", type=int, default=100)
    parser.add_argument(
        "--limit-per-category",
        type=int,
        default=None,
        help="Override each category limit. Useful for smoke tests.",
    )
    parser.add_argument("--no-docx", action="store_true")
    parser.add_argument("--no-pdf", action="store_true")
    parser.add_argument("--no-related", action="store_true")
    parser.add_argument("--skip-details", action="store_true")
    parser.add_argument("--trust-env", action="store_true")
    return parser.parse_args()


def resolve_backend_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return BACKEND_DIR / path


def main() -> int:
    args = parse_args()
    config = FlkCrawlConfig(
            output_root=resolve_backend_path(args.output_root),
            page_size=args.page_size,
            sleep_seconds=args.sleep_seconds,
            related_limit=args.related_limit,
            download_docx=not args.no_docx,
            download_pdf=not args.no_pdf,
            download_related=not args.no_related,
            fetch_details=not args.skip_details,
            trust_env=args.trust_env,
    )
    summary = crawl_china_flk(with_limit_per_category(config, args.limit_per_category))

    print(f"Output root: {summary.output_root}")
    print(f"Records seen: {summary.records_seen}")
    print(f"Records written: {summary.records_written}")
    print(f"Assets downloaded: {summary.assets_downloaded}")
    print(f"Related downloaded: {summary.related_downloaded}")
    print(f"Skipped existing assets: {summary.skipped_existing_assets}")
    print(f"Skipped errors: {summary.skipped_errors}")
    print(f"Detail fallbacks: {summary.detail_fallbacks}")
    print(f"Manifest: {summary.manifest_path}")
    print("Categories:")
    for category, count in sorted(summary.category_counts.items()):
        print(f"  {category}: {count}")
    print("Assets:")
    for asset_type, count in sorted(summary.asset_counts.items()):
        print(f"  {asset_type}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
