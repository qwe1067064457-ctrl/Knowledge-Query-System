"use client";

import { Gavel } from "lucide-react";

import { CASE_LEVEL_LABELS, type AdjudicationResult, type TypedEvidence } from "@/lib/api";
import { TraceDisclosure } from "@/components/trace/TraceDisclosure";

function EvidenceNames({ items }: { items: TypedEvidence[] }) {
  return (
    <div className="rounded-2xl bg-white/70 p-3">
      {items.length ? (
        <div className="flex flex-wrap gap-2">
          {items.map((item, index) => (
            <span
              className="rounded-full bg-[rgba(13,37,48,0.08)] px-2 py-1 text-[11px] text-[var(--color-ink-soft)]"
              key={`${item.signal}-${index}`}
            >
              {item.signal}
            </span>
          ))}
        </div>
      ) : (
        <div className="text-sm text-[var(--color-ink-soft)]">无</div>
      )}
    </div>
  );
}

export function AdjudicationCard({ result }: { result: AdjudicationResult }) {
  return (
    <TraceDisclosure
      accentClassName="text-[var(--color-ember)]"
      className="mb-4 rounded-3xl border border-[rgba(212,106,74,0.18)] bg-[rgba(212,106,74,0.08)] p-4"
      description="LLM 只负责裁决冲突或含糊证据，最终执行仍由 resolver / control signal 决定。"
      icon={Gavel}
      title="争议证据裁决"
    >
      <div className="grid gap-3 md:grid-cols-3">
        <div>
          <div className="mb-2 text-sm font-medium text-[var(--color-ink)]">Accepted</div>
          <EvidenceNames items={result.accepted_evidence} />
        </div>
        <div>
          <div className="mb-2 text-sm font-medium text-[var(--color-ink)]">Corrected</div>
          <EvidenceNames items={result.corrected_evidence} />
        </div>
        <div>
          <div className="mb-2 text-sm font-medium text-[var(--color-ink)]">Rejected</div>
          <EvidenceNames items={result.rejected_evidence} />
        </div>
      </div>

      <div className="mt-3 grid gap-3 md:grid-cols-3">
        <div className="rounded-2xl bg-white/70 p-3">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--color-ink-soft)]">
            Clarified Ambiguity
          </div>
          <div className="mt-1 text-sm text-[var(--color-ink)]">
            {result.clarified_ambiguity_type || "未提供"}
          </div>
        </div>
        <div className="rounded-2xl bg-white/70 p-3">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--color-ink-soft)]">
            Fallback Recommendation
          </div>
          <div className="mt-1 text-sm text-[var(--color-ink)]">
            {result.fallback_recommendation
              ? CASE_LEVEL_LABELS[result.fallback_recommendation]
              : "未提供"}
          </div>
        </div>
        <div className="rounded-2xl bg-white/70 p-3">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--color-ink-soft)]">
            Reason
          </div>
          <div className="mt-1 text-sm leading-6 text-[var(--color-ink)]">
            {result.reason || "未提供"}
          </div>
        </div>
      </div>
    </TraceDisclosure>
  );
}
