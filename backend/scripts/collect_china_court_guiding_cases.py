from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from legal_crawler.china_court import CourtGuidingCaseConfig, crawl_court_guiding_cases


DEFAULT_OUTPUT_ROOT = Path("knowledge") / "groups" / "law" / "documents" / "cn" / "guiding_cases"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect guiding cases from the Supreme People's Court website.")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Output root, relative to backend/ when not absolute.",
    )
    parser.add_argument("--pages", type=int, default=12)
    parser.add_argument("--max-records", type=int, default=None)
    parser.add_argument("--sleep-seconds", type=float, default=0.2)
    parser.add_argument("--trust-env", action="store_true")
    return parser.parse_args()


def resolve_backend_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return BACKEND_DIR / path


def main() -> int:
    args = parse_args()
    config = CourtGuidingCaseConfig(
        output_root=resolve_backend_path(args.output_root),
        pages=args.pages,
        max_records=args.max_records,
        sleep_seconds=args.sleep_seconds,
        trust_env=args.trust_env,
    )
    summary = crawl_court_guiding_cases(config)

    print(f"Output root: {summary.output_root}")
    print(f"Records seen: {summary.records_seen}")
    print(f"Records written: {summary.records_written}")
    print(f"Skipped existing: {summary.skipped_existing}")
    print(f"Skipped errors: {summary.skipped_errors}")
    print(f"Manifest: {summary.manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
