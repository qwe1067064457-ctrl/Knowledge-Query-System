"use client";

import { GitBranchPlus } from "lucide-react";

import type { ExecutionEvent, WorkflowTrace } from "@/lib/api";

import { ExecutionUnitList } from "@/components/trace/ExecutionUnitList";
import { TraceDisclosure } from "@/components/trace/TraceDisclosure";

function InlineList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-2xl bg-white/72 p-3">
      <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--color-ink-soft)]">
        {title}
      </div>
      <div className="mt-1 text-sm leading-6 text-[var(--color-ink)]">
        {items.length ? items.join(" / ") : "无"}
      </div>
    </div>
  );
}

export function WorkflowTraceCard({
  workflowTrace,
  executionEvents
}: {
  workflowTrace: WorkflowTrace;
  executionEvents: ExecutionEvent[];
}) {
  return (
    <TraceDisclosure
      accentClassName="text-[var(--color-ocean)]"
      className="mb-4 rounded-3xl border border-[rgba(15,139,141,0.18)] bg-[rgba(15,139,141,0.07)] p-4"
      description="这里展示 workflow policy / route 以及执行单元的摘要，不重写后端决策逻辑。"
      icon={GitBranchPlus}
      title="Workflow Trace"
    >
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <InlineList title="Route" items={workflowTrace.route ? [workflowTrace.route] : []} />
        <InlineList
          title="Handling Mode"
          items={workflowTrace.handling_mode ? [workflowTrace.handling_mode] : []}
        />
        <InlineList
          title="Planning Mode"
          items={workflowTrace.planning_mode ? [workflowTrace.planning_mode] : []}
        />
        <InlineList title="Policy Flags" items={workflowTrace.policy_flags} />
        <InlineList title="Enabled Powers" items={workflowTrace.enabled_powers} />
        <InlineList
          title="Fallback"
          items={
            workflowTrace.fallback_used
              ? [workflowTrace.fallback_reason || "已触发 fallback"]
              : ["未触发"]
          }
        />
      </div>

      {workflowTrace.payload_summary.length ? (
        <div className="mt-3 rounded-2xl bg-white/68 p-3">
          <div className="mb-2 text-sm font-medium text-[var(--color-ink)]">
            Workflow Payload Summary
          </div>
          <div className="grid gap-2 md:grid-cols-2">
            {workflowTrace.payload_summary.map((item, index) => (
              <div
                className="rounded-2xl bg-[rgba(13,37,48,0.04)] p-3 text-sm leading-6 text-[var(--color-ink-soft)]"
                key={`${item.label}-${index}`}
              >
                <span className="font-medium text-[var(--color-ink)]">{item.label}：</span>
                {item.value}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <ExecutionUnitList events={executionEvents} units={workflowTrace.execution_units} />
    </TraceDisclosure>
  );
}
