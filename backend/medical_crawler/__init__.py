from __future__ import annotations

from .nature_medicine import NatureMedicineConfig, NatureMedicineSummary, crawl_nature_medicine
from .pmc_ftp_pdf import PmcFtpPdfConfig, PmcFtpPdfSummary, crawl_pmc_ftp_pdfs
from .yiigle_cn import YiigleCnConfig, YiigleCnSummary, crawl_yiigle_cn_articles

__all__ = [
    "NatureMedicineConfig",
    "NatureMedicineSummary",
    "crawl_nature_medicine",
    "PmcFtpPdfConfig",
    "PmcFtpPdfSummary",
    "crawl_pmc_ftp_pdfs",
    "YiigleCnConfig",
    "YiigleCnSummary",
    "crawl_yiigle_cn_articles",
]
