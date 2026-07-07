"use client";

import type { ReactNode } from "react";

import {
  CASE_LEVEL_LABELS,
  EVIDENCE_SOURCE_LABELS,
  type ExecutionEvent,
  type IntentTrace,
  type WorkflowTrace,
} from "@/lib/api";

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

function Section({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="border-t border-[rgba(13,37,48,0.12)] pt-6 first:border-t-0 first:pt-0">
      <h4 className="text-3xl font-semibold tracking-[-0.05em] text-[var(--color-ink)]">{title}</h4>
      <div className="mt-5 space-y-4 text-[17px] leading-9 text-[var(--color-ink)]">{children}</div>
    </section>
  );
}

function Line({ label, value }: { label: string; value: unknown }) {
  return (
    <p>
      <span className="font-semibold text-[var(--color-ink)]">{label}：</span>
      {formatValue(value)}
    </p>
  );
}

export function TraceNarrative({
  intentTrace,
  workflowTrace,
  executionEvents,
}: {
  intentTrace?: IntentTrace;
  workflowTrace?: WorkflowTrace;
  executionEvents: ExecutionEvent[];
}) {
  if (!intentTrace && !workflowTrace) {
    return null;
  }

  const qualityReport = intentTrace?.quality_report;
  const adjudication = intentTrace?.adjudication_result;
  const resolved = intentTrace?.resolved;
  const control = intentTrace?.control;

  const acceptedEvidence = qualityReport?.accepted_evidence ?? [];
  const downgradedEvidence = qualityReport?.downgraded_evidence ?? [];
  const rejectedEvidence = qualityReport?.rejected_evidence ?? [];

  return (
    <div className="mb-6 rounded-[30px] border border-[rgba(13,37,48,0.08)] bg-white/78 px-6 py-7 shadow-[0_18px_45px_rgba(13,37,48,0.06)]">
      <Section title="本轮决策链路">
        <Line label="Route" value={workflowTrace?.route || readString(control, ["route", "control_signal"])} />
        <Line label="Handling" value={workflowTrace?.handling_mode || readString(control, ["handling_mode"])} />
        <Line label="Main Intent" value={readString(resolved, ["main_intent", "intent"])} />
        <Line label="Task Shape" value={readString(resolved, ["task_shape", "shape"])} />
        <Line label="Context Dependency" value={readString(resolved, ["context_dependency"])} />
        <Line label="Resolved Intent" value={readString(resolved, ["resolved_intent", "intent"])} />
        <Line label="Control Signal" value={readString(control, ["control_signal", "signal", "route"])} />
        <Line label="Decision Reason" value={intentTrace?.decision_reason} />
      </Section>

      {qualityReport ? (
        <Section title="Gate 判断">
          <Line label="Case Level" value={CASE_LEVEL_LABELS[qualityReport.case_level]} />
          <Line label="Case Reason" value={qualityReport.case_reason} />
          <Line label="Conflicts" value={qualityReport.conflicts} />
          <Line label="Ambiguities" value={qualityReport.ambiguities} />
          <Line label="Missing Prerequisites" value={qualityReport.missing_prerequisites} />
        </Section>
      ) : null}

      {qualityReport ? (
        <Section title="证据摘要">
          <Line
            label="Accepted"
            value={acceptedEvidence.map((item) => `${item.signal}(${EVIDENCE_SOURCE_LABELS[item.source]})`)}
          />
          <Line
            label="Downgraded"
            value={downgradedEvidence.map((item) => `${item.signal}(${EVIDENCE_SOURCE_LABELS[item.source]})`)}
          />
          <Line
            label="未用于本次决策"
            value={rejectedEvidence.map((item) => `${item.signal}(${EVIDENCE_SOURCE_LABELS[item.source]})`)}
          />
        </Section>
      ) : null}

      {adjudication ? (
        <Section title="争议证据裁决">
          <Line
            label="Accepted"
            value={adjudication.accepted_evidence.map((item) => item.signal)}
          />
          <Line
            label="Corrected"
            value={adjudication.corrected_evidence.map((item) => item.signal)}
          />
          <Line
            label="Rejected"
            value={adjudication.rejected_evidence.map((item) => item.signal)}
          />
          <Line label="Clarified Ambiguity" value={adjudication.clarified_ambiguity_type} />
          <Line
            label="Fallback Recommendation"
            value={
              adjudication.fallback_recommendation
                ? CASE_LEVEL_LABELS[adjudication.fallback_recommendation]
                : "未提供"
            }
          />
          <Line label="Reason" value={adjudication.reason} />
        </Section>
      ) : null}

      {workflowTrace ? (
        <Section title="Workflow 摘要">
          <Line label="Planning Mode" value={workflowTrace.planning_mode} />
          <Line label="Policy Flags" value={workflowTrace.policy_flags} />
          <Line label="Enabled Powers" value={workflowTrace.enabled_powers} />
          <Line
            label="Fallback"
            value={
              workflowTrace.fallback_used
                ? workflowTrace.fallback_reason || "已触发 fallback"
                : "未触发"
            }
          />
          <Line
            label="Execution Units"
            value={workflowTrace.execution_units.map((unit) => `${unit.unit_id}: ${unit.state || "pending"}`)}
          />
          <Line
            label="Payload Summary"
            value={workflowTrace.payload_summary.map((item) => `${item.label}: ${item.value}`)}
          />
        </Section>
      ) : null}

      {executionEvents.length ? (
        <Section title="执行更新">
          {executionEvents.map((event, index) => (
            <p key={`${event.type}-${event.unit_id}-${index}`}>
              <span className="font-semibold text-[var(--color-ink)]">
                {event.label || event.type}
                {event.status ? ` [${event.status}]` : ""}：
              </span>
              {event.detail || "无额外说明"}
              {event.unit_id ? ` (unit: ${event.unit_id})` : ""}
            </p>
          ))}
        </Section>
      ) : null}
    </div>
  );
}
