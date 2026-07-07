"use client";

import { ChevronDown, Database, FileSearch, Layers3, Search, Sparkles, type LucideIcon } from "lucide-react";
import { useMemo, useState } from "react";

import type { RetrievalStep } from "@/lib/api";

const STEP_META: Record<
  string,
  {
    label: string;
    icon: LucideIcon;
    border: string;
    badge: string;
    isStrategy?: boolean;
  }
> = {
  memory: {
    label: "Memory",
    icon: Database,
    border: "border-[rgba(15,139,141,0.16)] bg-[rgba(15,139,141,0.06)]",
    badge: "bg-[rgba(15,139,141,0.12)] text-ocean"
  },
  knowledge: {
    label: "Knowledge",
    icon: Search,
    border: "border-[rgba(13,37,48,0.1)] bg-[rgba(13,37,48,0.04)]",
    badge: "bg-[rgba(13,37,48,0.08)] text-[var(--color-ink)]"
  },
  skill: {
    label: "Skill",
    icon: Search,
    border: "border-[rgba(13,37,48,0.1)] bg-[rgba(13,37,48,0.04)]",
    badge: "bg-[rgba(13,37,48,0.08)] text-[var(--color-ink)]"
  },
  fallback: {
    label: "策略切换",
    icon: Sparkles,
    border: "border-[rgba(212,106,74,0.18)] bg-[rgba(212,106,74,0.08)]",
    badge: "bg-[rgba(212,106,74,0.12)] text-[var(--color-ember)]",
    isStrategy: true
  },
  vector: {
    label: "Vector",
    icon: Database,
    border: "border-[rgba(15,139,141,0.16)] bg-[rgba(15,139,141,0.06)]",
    badge: "bg-[rgba(15,139,141,0.12)] text-ocean"
  },
  bm25: {
    label: "BM25",
    icon: FileSearch,
    border: "border-[rgba(13,37,48,0.1)] bg-[rgba(13,37,48,0.04)]",
    badge: "bg-[rgba(13,37,48,0.08)] text-[var(--color-ink)]"
  },
  fused: {
    label: "Fused",
    icon: Layers3,
    border: "border-[rgba(15,139,141,0.16)] bg-[rgba(15,139,141,0.06)]",
    badge: "bg-[rgba(15,139,141,0.12)] text-ocean"
  }
};

function StepSection({
  step,
  defaultOpen,
}: {
  step: RetrievalStep;
  defaultOpen: boolean;
}) {
  const meta = STEP_META[step.stage] ?? STEP_META.knowledge;
  const Icon = meta.icon;
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <section className={`rounded-2xl border p-3 ${meta.border}`}>
      <button
        className="flex w-full items-start justify-between gap-3 text-left"
        onClick={() => setIsOpen((value) => !value)}
        type="button"
      >
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className={`rounded-full px-2 py-1 text-[11px] font-medium ${meta.badge}`}>
              {meta.label}
            </span>
            <div className="flex min-w-0 items-center gap-2 text-sm font-medium text-[var(--color-ink)]">
              <Icon className="shrink-0" size={14} />
              <span className="truncate">{step.title}</span>
            </div>
          </div>
          {step.message ? (
            <p className="mt-2 text-sm leading-6 text-[var(--color-ink-soft)]">
              {step.message}
            </p>
          ) : null}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {step.results.length ? (
            <span className="rounded-full bg-white/70 px-2 py-1 text-[11px] text-[var(--color-ink-soft)]">
              {step.results.length} 条
            </span>
          ) : meta.isStrategy ? (
            <span className="rounded-full bg-white/70 px-2 py-1 text-[11px] text-[var(--color-ink-soft)]">
              说明
            </span>
          ) : null}
          <ChevronDown
            className={`transition-transform ${isOpen ? "rotate-180" : ""}`}
            size={16}
          />
        </div>
      </button>

      {isOpen && step.results.length ? (
        <div className="mt-3 space-y-2">
          {step.results.map((item, resultIndex) => (
            <div
              className="rounded-2xl bg-white/70 p-3"
              key={`${item.channel}-${item.source_path}-${item.locator}-${resultIndex}`}
            >
              <div className="mb-1 flex items-center justify-between gap-3 text-xs text-[var(--color-ink-soft)]">
                <span className="truncate">{item.source_path}</span>
                {typeof item.score === "number" ? <span>{item.score.toFixed(3)}</span> : null}
              </div>
              {item.locator ? (
                <div className="mb-2 text-xs text-[var(--color-ink-soft)]">{item.locator}</div>
              ) : null}
              <p className="text-sm leading-6 text-[var(--color-ink)]">{item.snippet}</p>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}

export function RetrievalCard({ steps }: { steps: RetrievalStep[] }) {
  const [isOpen, setIsOpen] = useState(false);
  const visibleSteps = useMemo(
    () =>
      steps.filter((step) => {
        if (step.stage === "fallback") {
          return Boolean(step.message.trim());
        }

        return Boolean(step.title.trim() || step.message.trim() || step.results.length);
      }),
    [steps]
  );

  if (!visibleSteps.length) {
    return null;
  }

  return (
    <div className="mb-4 rounded-3xl border border-[rgba(15,139,141,0.18)] bg-[rgba(15,139,141,0.08)] p-4">
      <button
        className="flex w-full items-center justify-between gap-3 text-left"
        onClick={() => setIsOpen((value) => !value)}
        type="button"
      >
        <div className="flex items-center gap-2 text-sm font-medium text-ocean">
          <Database size={16} />
          检索轨迹
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-white/70 px-2 py-1 text-[11px] text-[var(--color-ink-soft)]">
            {visibleSteps.length} 段
          </span>
          <ChevronDown
            className={`text-[var(--color-ink-soft)] transition-transform ${isOpen ? "rotate-180" : ""}`}
            size={16}
          />
        </div>
      </button>

      {isOpen ? (
        <div className="mt-3 space-y-3">
          {visibleSteps.map((step, index) => (
            <StepSection
              defaultOpen={step.stage !== "fused" && step.stage !== "vector" && step.stage !== "bm25"}
              key={`${step.kind}-${step.stage}-${index}`}
              step={step}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}
