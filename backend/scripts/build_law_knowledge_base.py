from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from legal_crawler import build_law_knowledge_base


DEFAULT_SOURCE_DIR = Path("storage") / "knowledge" / "legal_corpus" / "documents_by_category"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the law group knowledge-base folder from categorized local legal documents."
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=DEFAULT_SOURCE_DIR,
        help="Categorized source directory, relative to backend/ when not absolute.",
    )
    parser.add_argument(
        "--group-id",
        default="law",
        help="Target group id. Defaults to law.",
    )
    return parser.parse_args()


def resolve_backend_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return BACKEND_DIR / path


def main() -> int:
    args = parse_args()
    summary = build_law_knowledge_base(
        backend_dir=BACKEND_DIR,
        source_dir=resolve_backend_path(args.source_dir),
        group_id=args.group_id,
    )

    print(f"Source: {summary.source_dir}")
    print(f"Law root: {summary.law_root}")
    print(f"eCFR root: {summary.ecfr_root}")
    print(f"Copied: {summary.copied}")
    print(f"Manifest: {summary.manifest_path}")
    print("Categories:")
    for category, count in sorted(summary.category_counts.items()):
        print(f"  {category}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
