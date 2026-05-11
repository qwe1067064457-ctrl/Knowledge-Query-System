from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from medical_crawler.pmc_ftp_pdf import PmcFtpPdfConfig, crawl_pmc_ftp_pdfs


DEFAULT_OUTPUT_ROOT = Path("knowledge") / "groups" / "medicine" / "documents" / "pmc_ftp_pdf"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect medical PDFs from PMC FTP official list.")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--csv-url", type=str, default="https://ftp.ncbi.nlm.nih.gov/pub/pmc/deprecated/oa_non_comm_use_pdf.csv")
    parser.add_argument("--max-records", type=int, default=10)
    parser.add_argument("--sleep-seconds", type=float, default=0.1)
    parser.add_argument("--trust-env", action="store_true")
    return parser.parse_args()


def resolve_backend_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return BACKEND_DIR / path


def main() -> int:
    args = parse_args()
    summary = crawl_pmc_ftp_pdfs(
        PmcFtpPdfConfig(
            output_root=resolve_backend_path(args.output_root),
            csv_url=args.csv_url,
            ftp_base_url="https://ftp.ncbi.nlm.nih.gov/pub/pmc/deprecated/",
            max_records=args.max_records,
            sleep_seconds=args.sleep_seconds,
            trust_env=args.trust_env,
        )
    )
    print(f"Output root: {summary.output_root}")
    print(f"Records seen: {summary.records_seen}")
    print(f"Records written: {summary.records_written}")
    print(f"Skipped existing: {summary.skipped_existing}")
    print(f"Skipped invalid: {summary.skipped_invalid}")
    print(f"Manifest: {summary.manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
