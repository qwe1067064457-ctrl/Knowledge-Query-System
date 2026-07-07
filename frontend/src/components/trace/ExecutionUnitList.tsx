"use client";

import { Activity, CircleDot } from "lucide-react";

import type { ExecutionEvent, WorkflowExecutionUnit } from "@/lib/api";

function UnitCard({ unit }: { unit: WorkflowExecutionUnit }) {
  return (
    <div className="rounded-2xl bg-white/70 p-3">
      <div className="flex items-center justify-between gap-3">
        <div className="text-sm font-medium text-[var(--color-ink)]">
          {unit.unit_id || "未命名单元"}
        </div>
        <span className="rounded-full bg-[rgba(13,37,48,0.08)] px-2 py-1 text-[11px] text-[var(--color-ink-soft)]">
          {unit.state || "pending"}
        </span>
      </div>
      <div className="mt-2 space-y-1 text-sm leading-6 text-[var(--color-ink-soft)]">
        <div>goal: {unit.goal || "未提供"}</div>
        <div>capability: {unit.capability || "未提供"}</div>
        <div>depends_on: {unit.depends_on.length ? unit.depends_on.join(" / ") : "无"}</div>
        <div>output_slot: {unit.output_slot || "未提供"}</div>
        <div>retrieval_quality: {unit.retrieval_quality_status || "未提供"}</div>
        {unit.summary ? <div>summary: {unit.summary}</div> : null}
      </div>
    </div>
  );
}

function EventCard({ event }: { event: ExecutionEvent }) {
  return (
    <div className="rounded-2xl bg-[rgba(13,37,48,0.04)] p-3">
      <div className="flex items-center justify-between gap-3">
        <div className="text-sm font-medium text-[var(--color-ink)]">{event.label || event.type}</div>
        <span className="rounded-full bg-white/70 px-2 py-1 text-[11px] text-[var(--color-ink-soft)]">
          {event.status || "更新"}
        </span>
      </div>
      <div className="mt-2 text-sm leading-6 text-[var(--color-ink-soft)]">
        {event.unit_id ? <div>unit: {event.unit_id}</div> : null}
        <div>{event.detail || "无额外说明"}</div>
      </div>
    </div>
  );
}

export function ExecutionUnitList({
  units,
  events
}: {
  units: WorkflowExecutionUnit[];
  events: ExecutionEvent[];
}) {
  if (!units.length && !events.length) {
    return null;
  }

  return (
    <div className="mt-3 grid gap-3 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
      <div>
        <div className="mb-2 flex items-center gap-2 text-sm font-medium text-[var(--color-ink)]">
          <CircleDot size={15} />
          Execution Units
        </div>
        <div className="space-y-3">
          {units.length ? (
            units.map((unit, index) => <UnitCard key={`${unit.unit_id}-${index}`} unit={unit} />)
          ) : (
            <div className="rounded-2xl bg-white/65 p-3 text-sm text-[var(--color-ink-soft)]">
              暂无 execution unit。
            </div>
          )}
        </div>
      </div>

      <div>
        <div className="mb-2 flex items-center gap-2 text-sm font-medium text-[var(--color-ink)]">
          <Activity size={15} />
          Execution Updates
        </div>
        <div className="space-y-3">
          {events.length ? (
            events.map((event, index) => <EventCard event={event} key={`${event.type}-${index}`} />)
          ) : (
            <div className="rounded-2xl bg-white/65 p-3 text-sm text-[var(--color-ink-soft)]">
              暂无 execution update。
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
