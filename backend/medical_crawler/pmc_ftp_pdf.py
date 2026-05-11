from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urljoin

import httpx


DEFAULT_CSV_URL = "https://ftp.ncbi.nlm.nih.gov/pub/pmc/deprecated/oa_non_comm_use_pdf.csv"
DEFAULT_FTP_BASE_URL = "https://ftp.ncbi.nlm.nih.gov/pub/pmc/deprecated/"


@dataclass(frozen=True)
class PmcFtpPdfConfig:
    output_root: Path
    csv_url: str = DEFAULT_CSV_URL
    ftp_base_url: str = DEFAULT_FTP_BASE_URL
    max_records: int = 10
    sleep_seconds: float = 0.1
    timeout_seconds: float = 60.0
    trust_env: bool = False

    def normalized(self) -> "PmcFtpPdfConfig":
        if self.max_records < 1:
            raise ValueError("max_records must be at least 1")
        if self.sleep_seconds < 0:
            raise ValueError("sleep_seconds cannot be negative")
        return self


@dataclass(frozen=True)
class PmcFtpPdfSummary:
    output_root: Path
    records_seen: int
    records_written: int
    skipped_existing: int
    skipped_invalid: int
    manifest_path: Path


class PmcFtpApi(Protocol):
    def get_bytes(self, url: str) -> bytes:
        ...

    def iter_csv_rows(self, url: str, *, row_limit: int) -> list[dict[str, str]]:
        ...


class PmcFtpHttpApi:
    def __init__(self, config: PmcFtpPdfConfig) -> None:
        self.client = httpx.Client(
            timeout=config.timeout_seconds,
            follow_redirects=True,
            trust_env=config.trust_env,
            headers={"User-Agent": "Skill-First-Hybrid-RAG pmc ftp pdf crawler/1.0"},
        )

    def close(self) -> None:
        self.client.close()

    def get_bytes(self, url: str) -> bytes:
        response = self.client.get(url)
        response.raise_for_status()
        return response.content

    def iter_csv_rows(self, url: str, *, row_limit: int) -> list[dict[str, str]]:
        with self.client.stream("GET", url) as response:
            response.raise_for_status()
            lines = response.iter_lines()
            try:
                header = next(lines)
            except StopIteration:
                return []
            header_text = header.decode("utf-8") if isinstance(header, bytes) else header
            fieldnames = next(csv.reader([header_text]))
            rows: list[dict[str, str]] = []
            for line in lines:
                if len(rows) >= row_limit:
                    break
                line_text = line.decode("utf-8") if isinstance(line, bytes) else line
                if not line_text.strip():
                    continue
                values = next(csv.reader([line_text]))
                row = {fieldnames[index]: values[index] if index < len(values) else "" for index in range(len(fieldnames))}
                rows.append(row)
            return rows


def safe_filename(value: str, *, fallback: str = "document", max_length: int = 72) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", value)
    cleaned = re.sub(r"\s+", "_", cleaned).strip("._ ")
    cleaned = cleaned or fallback
    return cleaned[:max_length]


def normalize_text(value: str) -> str:
    value = value or ""
    return re.sub(r"\s+", " ", value).strip()


def extract_year_from_citation(citation: str) -> int | None:
    years = re.findall(r"(19\d{2}|20\d{2})", citation or "")
    if not years:
        return None
    return int(years[-1])


def parse_csv_rows(rows_input: list[dict[str, str]] | str, *, ftp_base_url: str) -> list[dict[str, Any]]:
    if isinstance(rows_input, str):
        reader = csv.DictReader(io.StringIO(rows_input))
    else:
        reader = rows_input
    rows: list[dict[str, Any]] = []
    for row in reader:
        file_path = (row.get("File") or "").strip()
        accession_id = (row.get("Accession ID") or "").strip()
        citation = normalize_text(row.get("Article Citation") or "")
        if not file_path.lower().endswith(".pdf"):
            continue
        if not accession_id or not citation:
            continue
        rows.append(
            {
                "pmcid": accession_id,
                "citation": citation,
                "title": citation,
                "year": extract_year_from_citation(citation),
                "pdf_url": urljoin(ftp_base_url, file_path),
                "file_path": file_path,
                "last_updated": (row.get("Last Updated (YYYY-MM-DD HH:MM:SS)") or "").strip(),
                "pmid": (row.get("PMID") or "").strip(),
                "license": (row.get("License") or "").strip(),
            }
        )
    return rows


def record_dir(output_root: Path, record: dict[str, Any]) -> Path:
    title = safe_filename(record.get("title") or record.get("pmcid") or "pmc_pdf")
    digest_source = record.get("pmcid") or record.get("pdf_url") or title
    digest = hashlib.sha1(str(digest_source).encode("utf-8")).hexdigest()[:10]
    prefix = str(record.get("year") or "undated")
    return output_root / f"{prefix}_{digest}_{title}"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8-sig")


def write_binary(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def render_index(manifest: dict[str, Any]) -> str:
    return f"""# PMC FTP 医学 PDF 样本

来源：PMC Open Access Subset / FTP Service

资料类型：原始 PDF

## 统计

- `total_pdf_documents`：{manifest.get("total_pdf_documents", 0)}
- `records_written_this_run`：{manifest.get("records_written", 0)}
- `skipped_existing`：{manifest.get("skipped_existing", 0)}
- `skipped_invalid`：{manifest.get("skipped_invalid", 0)}

## 说明

- 仅保留 PMC FTP 官方清单里可直接下载成功的原始 PDF
- 这些 PDF 是完整论文正文，不是门面页
"""


def crawl_pmc_ftp_pdfs(config: PmcFtpPdfConfig, *, api: PmcFtpApi | None = None) -> PmcFtpPdfSummary:
    config = config.normalized()
    config.output_root.mkdir(parents=True, exist_ok=True)
    own_api = PmcFtpHttpApi(config) if api is None else None
    pmc_api = api or own_api
    assert pmc_api is not None

    records_seen = 0
    records_written = 0
    skipped_existing = 0
    skipped_invalid = 0

    try:
        csv_rows = pmc_api.iter_csv_rows(config.csv_url, row_limit=config.max_records)
        records = parse_csv_rows(csv_rows, ftp_base_url=config.ftp_base_url)
        for record in records:
            if records_seen >= config.max_records:
                break
            records_seen += 1
            target_dir = record_dir(config.output_root, record)
            pdf_path = target_dir / "source.pdf"
            if pdf_path.exists():
                skipped_existing += 1
                continue
            try:
                payload = pmc_api.get_bytes(record["pdf_url"])
            except Exception:
                skipped_invalid += 1
                continue
            if not payload.startswith(b"%PDF"):
                skipped_invalid += 1
                continue
            metadata = {
                "source": "PMC Open Access Subset / FTP Service",
                "pmcid": record["pmcid"],
                "pmid": record["pmid"],
                "title": record["title"],
                "citation": record["citation"],
                "year": record["year"],
                "pdf_url": record["pdf_url"],
                "file_path": record["file_path"],
                "last_updated": record["last_updated"],
                "license": record["license"],
            }
            write_binary(pdf_path, payload)
            write_json(target_dir / "metadata.json", metadata)
            records_written += 1
            if config.sleep_seconds:
                time.sleep(config.sleep_seconds)
    finally:
        if own_api is not None:
            own_api.close()

    manifest_path = config.output_root / "manifest.json"
    total_pdf_documents = len(list(config.output_root.rglob("source.pdf")))
    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": {
            "name": "PMC Open Access Subset / FTP Service",
            "csv_url": config.csv_url,
            "ftp_base_url": config.ftp_base_url,
        },
        "total_pdf_documents": total_pdf_documents,
        "records_seen": records_seen,
        "records_written": records_written,
        "skipped_existing": skipped_existing,
        "skipped_invalid": skipped_invalid,
    }
    write_json(manifest_path, manifest)
    write_text(config.output_root / "index.md", render_index(manifest))
    return PmcFtpPdfSummary(
        output_root=config.output_root,
        records_seen=records_seen,
        records_written=records_written,
        skipped_existing=skipped_existing,
        skipped_invalid=skipped_invalid,
        manifest_path=manifest_path,
    )
