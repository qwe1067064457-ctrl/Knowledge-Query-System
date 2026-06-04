from __future__ import annotations

from monitoring.core.types import MetricSnapshot, MonitoringReport, RequestTimeline


def finalize_report(
    *,
    timelines: list[RequestTimeline],
    metrics: MetricSnapshot,
    failures: dict[str, int],
) -> MonitoringReport:
    return MonitoringReport(timelines=timelines, metrics=metrics, failures=failures)
