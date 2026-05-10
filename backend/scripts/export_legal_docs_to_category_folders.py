from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from legal_crawler import export_jsonl_to_category_folders


DEFAULT_INPUT_PATH = Path("storage") / "knowledge" / "legal_corpus" / "ecfr_legal_docs.jsonl"
DEFAULT_OUTPUT_DIR = Path("storage") / "knowledge" / "legal_corpus" / "documents_by_category"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a legal JSONL corpus into one Markdown file per document, grouped by category folders."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help="Input JSONL path, relative to backend/ when not absolute.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory, relative to backend/ when not absolute.",
    )
    return parser.parse_args()


def resolve_backend_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return BACKEND_DIR / path


def main() -> int:
    args = parse_args()
    summary = export_jsonl_to_category_folders(
        resolve_backend_path(args.input),
        resolve_backend_path(args.output_dir),
    )

    print(f"Input: {summary.input_path}")
    print(f"Output directory: {summary.output_dir}")
    print(f"Read: {summary.read}")
    print(f"Written: {summary.written}")
    print(f"Skipped invalid: {summary.skipped_invalid}")
    print(f"Manifest: {summary.manifest_path}")
    if summary.category_counts:
        print("Categories:")
        for category, count in sorted(summary.category_counts.items()):
            print(f"  {category}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
