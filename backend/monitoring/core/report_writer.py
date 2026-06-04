from __future__ import annotations

from monitoring.core.types import MonitoringReport


def report_to_dict(report: MonitoringReport) -> dict[str, object]:
    return report.to_dict()
