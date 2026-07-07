"use client";

import { ShieldAlert } from "lucide-react";

import { CASE_LEVEL_LABELS, type EvidenceQualityReport } from "@/lib/api";
import { TraceDisclosure } from "@/components/trace/TraceDisclosure";

function ListBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-2xl bg-white/68 p-3">
      <div className="text-sm font-medium text-[var(--color-ink)]">{title}</div>
      <div className="mt-2 text-sm leading-6 text-[var(--color-ink-soft)]">
        {items.length ? items.join(" / ") : "无"}
      </div>
    </div>
  );
}

export function GateSummary({ qualityReport }: { qualityReport: EvidenceQualityReport }) {
  return (
    <TraceDisclosure
      accentClassName="text-[rgb(53,96,125)]"
      className="mb-4 rounded-3xl border border-[rgba(69,123,157,0.18)] bg-[rgba(69,123,157,0.08)] p-4"
      description="Gate 负责判断这个 case 是否已经足够自动收敛，还是需要澄清、裁决或能力边界保护。"
      icon={ShieldAlert}
      title="Gate Summary"
    >
      <div className="grid gap-3 md:grid-cols-2">
        <div className="rounded-2xl bg-white/72 p-3">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--color-ink-soft)]">
            Case Level
          </div>
          <div className="mt-1 text-sm font-medium text-[var(--color-ink)]">
            {CASE_LEVEL_LABELS[qualityReport.case_level]}
          </div>
        </div>
        <div className="rounded-2xl bg-white/72 p-3">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--color-ink-soft)]">
            Case Reason
          </div>
          <div className="mt-1 text-sm leading-6 text-[var(--color-ink)]">
            {qualityReport.case_reason || "未提供"}
          </div>
        </div>
      </div>

      <div className="mt-3 grid gap-3 md:grid-cols-3">
        <ListBlock items={qualityReport.conflicts} title="Conflicts" />
        <ListBlock items={qualityReport.ambiguities} title="Ambiguities" />
        <ListBlock items={qualityReport.missing_prerequisites} title="Missing Prerequisites" />
      </div>
    </TraceDisclosure>
  );
}
