"use client";

import { Compass, Route } from "lucide-react";

import type { IntentTrace, WorkflowTrace } from "@/lib/api";
import { TraceDisclosure } from "@/components/trace/TraceDisclosure";

function readString(source: Record<string, unknown> | null | undefined, keys: string[]) {
  for (const key of keys) {
    const value = source?.[key];
    if (typeof value === "string" && value.trim()) {
      return value;
    }
  }

  return "";
}

function formatValue(value: unknown) {
  if (value === null || value === undefined || value === "") {
    return "未提供";
  }

  if (Array.isArray(value)) {
    return value.length ? value.map((entry) => String(entry)).join(" / ") : "未提供";
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return String(value);
}

function Item({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="rounded-2xl bg-white/65 p-3">
      <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--color-ink-soft)]">
        {label}
      </div>
      <div className="mt-1 text-sm leading-6 text-[var(--color-ink)]">{formatValue(value)}</div>
    </div>
  );
}

export function DecisionTraceCard({
  intentTrace,
  workflowTrace
}: {
  intentTrace: IntentTrace;
  workflowTrace?: WorkflowTrace;
}) {
  const resolved = intentTrace.resolved;
  const control = intentTrace.control;
  const mainIntent = readString(resolved, ["main_intent", "intent", "resolved_intent"]);
  const taskShape =
    readString(resolved, ["task_shape", "shape"]) ||
    readString(resolved?.task as Record<string, unknown> | null, ["shape", "complexity", "topology"]);
  const contextDependency = readString(resolved, ["context_dependency"]);
  const resolvedIntent = readString(resolved, ["resolved_intent", "intent"]) || mainIntent;
  const controlSignal =
    readString(control, ["control_signal", "signal", "route"]) ||
    workflowTrace?.route ||
    "未提供";
  const decisionReason = intentTrace.decision_reason || readString(control, ["reason"]);

  return (
    <TraceDisclosure
      accentClassName="text-[var(--color-ink)]"
      className="mb-4 rounded-3xl border border-[rgba(13,37,48,0.1)] bg-[rgba(255,255,255,0.55)] p-4"
      description="这张卡描述本次消息是如何从证据收敛到 route / control signal 的。"
      icon={Compass}
      title="Decision Trace"
    >
      <div className="grid gap-3 md:grid-cols-2">
        <Item label="Main Intent" value={mainIntent || "未提供"} />
        <Item label="Task Shape" value={taskShape || "未提供"} />
        <Item label="Context Dependency" value={contextDependency || "未提供"} />
        <Item label="Resolved Intent" value={resolvedIntent || "未提供"} />
        <Item label="Control Signal" value={controlSignal} />
        <Item label="Decision Reason" value={decisionReason || "未提供"} />
      </div>

      {(control || workflowTrace) && (
        <div className="mt-3 rounded-2xl bg-[rgba(13,37,48,0.04)] p-3">
          <div className="mb-2 flex items-center gap-2 text-sm font-medium text-[var(--color-ink)]">
            <Route size={15} />
            Resolver / Control
          </div>
          <pre className="mono whitespace-pre-wrap text-xs leading-6 text-[var(--color-ink-soft)]">
            {JSON.stringify(
              {
                resolved,
                control,
                workflow: workflowTrace
                  ? {
                      route: workflowTrace.route,
                      handling_mode: workflowTrace.handling_mode,
                      planning_mode: workflowTrace.planning_mode
                    }
                  : null
              },
              null,
              2
            )}
          </pre>
        </div>
      )}
    </TraceDisclosure>
  );
}
