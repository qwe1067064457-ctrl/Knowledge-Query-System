"use client";

import { Scale } from "lucide-react";

import { EVIDENCE_SOURCE_LABELS, type EvidenceQualityReport, type TypedEvidence } from "@/lib/api";
import { TraceDisclosure } from "@/components/trace/TraceDisclosure";

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <span className="rounded-full bg-[rgba(13,37,48,0.06)] px-2 py-1 text-[11px] text-[var(--color-ink-soft)]">
      {label}: {value}
    </span>
  );
}

function formatValue(value: unknown) {
  if (value === null || value === undefined || value === "") {
    return "未提供";
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return String(value);
}

function EvidenceItem({ evidence }: { evidence: TypedEvidence }) {
  return (
    <div className="rounded-2xl bg-white/72 p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-medium text-[var(--color-ink)]">{evidence.signal}</div>
          <div className="mt-1 text-sm leading-6 text-[var(--color-ink-soft)]">
            {formatValue(evidence.value)}
          </div>
        </div>
        <span className="rounded-full bg-[rgba(15,139,141,0.1)] px-2 py-1 text-[11px] text-[var(--color-ocean)]">
          {EVIDENCE_SOURCE_LABELS[evidence.source]}
        </span>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        <Metric label="score" value={evidence.score === null ? "null" : evidence.score.toFixed(3)} />
        <Metric
          label="threshold"
          value={evidence.threshold === null ? "null" : evidence.threshold.toFixed(3)}
        />
        <Metric label="margin" value={evidence.margin === null ? "null" : evidence.margin.toFixed(3)} />
        <Metric label="criticality" value={evidence.criticality} />
        <Metric label="source" value={evidence.source} />
      </div>

      <div className="mt-3 space-y-2 text-sm leading-6 text-[var(--color-ink-soft)]">
        <div>
          <span className="font-medium text-[var(--color-ink)]">rationale：</span>
          {evidence.rationale || "未提供"}
        </div>
        <div>
          <span className="font-medium text-[var(--color-ink)]">calibration：</span>
          {evidence.calibration_quality}
        </div>
        <div>
          <span className="font-medium text-[var(--color-ink)]">prerequisites：</span>
          {evidence.prerequisites.length ? evidence.prerequisites.join(" / ") : "无"}
        </div>
        <div>
          <span className="font-medium text-[var(--color-ink)]">missing：</span>
          {evidence.missing_prerequisites.length
            ? evidence.missing_prerequisites.join(" / ")
            : "无"}
        </div>
      </div>
    </div>
  );
}

function Column({
  title,
  subtitle,
  tone,
  items
}: {
  title: string;
  subtitle: string;
  tone: string;
  items: TypedEvidence[];
}) {
  return (
    <section className={`rounded-3xl border p-4 ${tone}`}>
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-sm font-medium text-[var(--color-ink)]">{title}</div>
          <div className="text-xs text-[var(--color-ink-soft)]">{subtitle}</div>
        </div>
        <span className="rounded-full bg-white/70 px-2 py-1 text-[11px] text-[var(--color-ink-soft)]">
          {items.length} 条
        </span>
      </div>

      <div className="mt-3 space-y-3">
        {items.length ? (
          items.map((evidence, index) => (
            <EvidenceItem
              evidence={evidence}
              key={`${title}-${evidence.signal}-${index}-${evidence.source}`}
            />
          ))
        ) : (
          <div className="rounded-2xl bg-white/60 p-3 text-sm text-[var(--color-ink-soft)]">
            当前无内容。
          </div>
        )}
      </div>
    </section>
  );
}

export function EvidenceBoard({ qualityReport }: { qualityReport: EvidenceQualityReport }) {
  const total =
    qualityReport.accepted_evidence.length +
    qualityReport.downgraded_evidence.length +
    qualityReport.rejected_evidence.length;

  if (!total) {
    return null;
  }

  return (
    <TraceDisclosure
      accentClassName="text-[var(--color-ink)]"
      className="mb-4 rounded-3xl border border-[rgba(13,37,48,0.1)] bg-[rgba(255,255,255,0.58)] p-4"
      description="证据默认折叠，展开后可查看已采信、弱证据和未用于本次决策的完整结构。"
      icon={Scale}
      title="Evidence Board"
      trailing={
        <span className="rounded-full bg-white/70 px-2 py-1 text-[11px] text-[var(--color-ink-soft)]">
          {total} 条
        </span>
      }
    >
      <div className="grid gap-3 xl:grid-cols-3">
        <Column
          items={qualityReport.accepted_evidence}
          subtitle="本次已经采信"
          title="Accepted"
          tone="border-[rgba(15,139,141,0.18)] bg-[rgba(15,139,141,0.06)]"
        />
        <Column
          items={qualityReport.downgraded_evidence}
          subtitle="仅作提示，不单独决定 route"
          title="Downgraded"
          tone="border-[rgba(219,158,54,0.18)] bg-[rgba(219,158,54,0.08)]"
        />
        <Column
          items={qualityReport.rejected_evidence}
          subtitle="未用于本次决策"
          title="Rejected"
          tone="border-[rgba(13,37,48,0.12)] bg-[rgba(13,37,48,0.04)]"
        />
      </div>
    </TraceDisclosure>
  );
}
