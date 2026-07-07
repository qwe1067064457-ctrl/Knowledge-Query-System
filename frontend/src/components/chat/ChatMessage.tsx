"use client";

import { RotateCcw, Sparkles } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { RetrievalCard } from "@/components/chat/RetrievalCard";
import { ThoughtChain } from "@/components/chat/ThoughtChain";
import {
  CASE_LEVEL_LABELS,
  EVIDENCE_SOURCE_LABELS,
  type ExecutionEvent,
  type IntentTrace,
  type RetrievalStep,
  type ToolCall,
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

function TraceRuntimeStrip({
  intentTrace,
  workflowTrace,
  executionEvents,
  retrievalSteps,
  toolCalls,
  content,
  isStreaming,
}: {
  intentTrace?: IntentTrace;
  workflowTrace?: WorkflowTrace;
  executionEvents: ExecutionEvent[];
  retrievalSteps: RetrievalStep[];
  toolCalls: ToolCall[];
  content: string;
  isStreaming: boolean;
}) {
  if (!isStreaming && !intentTrace && !workflowTrace) {
    return null;
  }

  const qualityReport = intentTrace?.quality_report;
  const resolved = intentTrace?.resolved;
  const control = intentTrace?.control;
  const smallModelSignals = intentTrace?.typed_evidence.filter((item) => item.source === "small_model") ?? [];
  const route = workflowTrace?.route || readString(control, ["route", "control_signal"]) || "未提供";
  const handlingMode =
    workflowTrace?.handling_mode || readString(control, ["handling_mode"]) || "未提供";
  const mainIntent = readString(resolved, ["main_intent", "intent", "resolved_intent"]) || "未提供";
  const resolvedIntent = readString(resolved, ["resolved_intent", "intent"]) || mainIntent;
  const gateLabel = qualityReport ? CASE_LEVEL_LABELS[qualityReport.case_level] : "未提供";
  const latestEvents = executionEvents.slice(-3);
  const latestRetrieval = retrievalSteps[retrievalSteps.length - 1];
  const latestToolCall = toolCalls[toolCalls.length - 1];
  const hasAnswerStarted = Boolean(content.trim());

  if (isStreaming) {
    const stages = [
      {
        label: "意图识别",
        status: intentTrace ? "已完成" : "进行中",
        detail: intentTrace
          ? `main intent = ${mainIntent}`
          : "正在等待 intent_analysis 事件返回主意图与证据。",
      },
      {
        label: "Quality Gate",
        status: qualityReport ? "已完成" : "等待中",
        detail: qualityReport
          ? `当前结果为 ${gateLabel}`
          : "正在等待 gate 判断是否自动收敛、需要裁决或缺少上下文。",
      },
      {
        label: "Workflow",
        status: workflowTrace ? "已完成" : "等待中",
        detail: workflowTrace
          ? `route = ${route} / handling = ${handlingMode}`
          : "正在等待 workflow_plan 与 execution_update 返回路由和执行载荷。",
      },
      {
        label: "回答生成",
        status: hasAnswerStarted ? "已开始" : "进行中",
        detail: hasAnswerStarted
          ? `正文已开始流式输出，当前已收到 ${content.length} 个字符。`
          : latestEvents.length
            ? latestEvents[latestEvents.length - 1]?.detail || "正在拼接回答内容。"
            : "当前还没有正文 token，先展示中间过程与执行链路。",
      },
    ];

    return (
      <div className="mb-4 rounded-[26px] border border-[rgba(15,139,141,0.16)] bg-[rgba(15,139,141,0.07)] px-4 py-4">
        <div className="flex items-center gap-2 text-sm font-medium text-ocean">
          <Sparkles size={16} />
          决策链路正在收敛
        </div>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          {stages.map((stage) => (
            <div
              className="rounded-2xl border border-[rgba(13,37,48,0.08)] bg-white/72 px-3 py-3"
              key={stage.label}
            >
              <div className="flex items-center justify-between gap-3">
                <div className="text-sm font-medium text-[var(--color-ink)]">{stage.label}</div>
                <span
                  className={`rounded-full px-2 py-1 text-[11px] ${
                    stage.status === "已完成"
                      ? "bg-[rgba(15,139,141,0.12)] text-ocean"
                      : "bg-[rgba(13,37,48,0.08)] text-[var(--color-ink-soft)]"
                  }`}
                >
                  {stage.status}
                </span>
              </div>
              <p className="mt-2 text-sm leading-6 text-[var(--color-ink-soft)]">{stage.detail}</p>
            </div>
          ))}
        </div>
        <div className="mt-3 space-y-2 text-sm leading-7 text-[var(--color-ink)]">
          <p>route 已确定为 <span className="font-semibold">{route}</span>，handling 为 <span className="font-semibold">{handlingMode}</span>。</p>
          <p>主意图识别为 <span className="font-semibold">{mainIntent}</span>，resolved intent 为 <span className="font-semibold">{resolvedIntent}</span>。</p>
          <p>quality gate 当前结果：<span className="font-semibold">{gateLabel}</span>。</p>
          <p>
            小模型参与：
            <span className="font-semibold">
              {smallModelSignals.length
                ? `已参与（${smallModelSignals.map((item) => item.signal).join(" / ")}）`
                : "当前 trace 未明确给出 small_model 证据"}
            </span>
            。
          </p>
          {latestRetrieval ? (
            <p>
              当前检索：
              <span className="font-semibold">
                {latestRetrieval.title} / {latestRetrieval.stage}
              </span>
              ，{latestRetrieval.message || "正在返回检索结果。"}
            </p>
          ) : null}
          {latestToolCall ? (
            <p>
              当前工具：
              <span className="font-semibold">{latestToolCall.tool}</span>
              {latestToolCall.output ? " 已返回结果。" : " 正在执行。"}
            </p>
          ) : null}
          {qualityReport?.case_reason ? (
            <p>gate 原因：<span className="font-semibold">{qualityReport.case_reason}</span>。</p>
          ) : null}
          {!intentTrace && !workflowTrace && !latestRetrieval && !latestToolCall && !latestEvents.length ? (
            <div className="rounded-2xl bg-white/72 px-3 py-3 text-sm leading-7 text-[var(--color-ink-soft)]">
              <p>后端中间事件还未到达前端，所以这里先保留执行中的位置。</p>
              <p>一旦收到 `intent_analysis`、`workflow_plan` 或 `execution_update`，这里会继续补全，而不是退回“正在生成回答...”占位文案。</p>
            </div>
          ) : null}
          {latestEvents.length ? (
            <div className="rounded-2xl bg-white/72 px-3 py-3 text-sm leading-7 text-[var(--color-ink-soft)]">
              {latestEvents.map((event, index) => (
                <p key={`${event.type}-${event.unit_id}-${index}`}>
                  {event.label || event.type}
                  {event.status ? ` [${event.status}]` : ""}：{event.detail || "处理中"}
                </p>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <div className="mb-4 rounded-[24px] border border-[rgba(13,37,48,0.1)] bg-white/72 px-4 py-4">
      <div className="text-sm font-medium text-[var(--color-ink)]">本轮决策摘要</div>
      <div className="mt-2 flex flex-wrap gap-2 text-xs text-[var(--color-ink-soft)]">
        <span className="rounded-full bg-[rgba(15,139,141,0.12)] px-2 py-1 text-ocean">route {route}</span>
        <span className="rounded-full bg-[rgba(13,37,48,0.08)] px-2 py-1">handling {handlingMode}</span>
        <span className="rounded-full bg-[rgba(212,106,74,0.12)] px-2 py-1 text-[var(--color-ember)]">
          gate {gateLabel}
        </span>
        <span className="rounded-full bg-[rgba(13,37,48,0.08)] px-2 py-1">
          small_model {smallModelSignals.length ? "有" : "未提供"}
        </span>
      </div>
      <div className="mt-3 space-y-2 text-sm leading-7 text-[var(--color-ink-soft)]">
        <p>主意图：{mainIntent}。最终收敛：{resolvedIntent}。</p>
        {qualityReport?.case_reason ? <p>Gate 原因：{qualityReport.case_reason}</p> : null}
        {workflowTrace?.planning_mode ? <p>Workflow：planning mode 为 {workflowTrace.planning_mode}。</p> : null}
      </div>
    </div>
  );
}

export function ChatMessage({
  role,
  content,
  toolCalls,
  retrievalSteps,
  intentTrace,
  workflowTrace,
  executionEvents,
  isStreaming = false,
  onRetry,
}: {
  role: "user" | "assistant";
  content: string;
  toolCalls: ToolCall[];
  retrievalSteps: RetrievalStep[];
  intentTrace?: IntentTrace;
  workflowTrace?: WorkflowTrace;
  executionEvents?: ExecutionEvent[];
  isStreaming?: boolean;
  onRetry?: (() => void) | null;
}) {
  const isUser = role === "user";
  const shouldHideAssistantBody = !isUser && isStreaming && !content.trim();

  return (
    <article
      className={`max-w-[90%] rounded-[28px] px-5 py-4 ${
        isUser
          ? "relative ml-auto bg-[rgba(13,37,48,0.92)] text-white"
          : "panel mr-auto overflow-hidden text-[var(--color-ink)]"
      }`}
    >
      {isUser && onRetry ? (
        <div className="absolute right-4 top-4">
          <button
            className="flex items-center gap-2 rounded-full border border-white/20 bg-white/8 px-3 py-1.5 text-xs text-white/85 backdrop-blur-sm"
            onClick={onRetry}
            type="button"
          >
            <RotateCcw size={14} />
            重发
          </button>
        </div>
      ) : null}

      {!isUser ? (
        <TraceRuntimeStrip
          content={content}
          executionEvents={executionEvents ?? []}
          intentTrace={intentTrace}
          isStreaming={isStreaming}
          retrievalSteps={retrievalSteps}
          toolCalls={toolCalls}
          workflowTrace={workflowTrace}
        />
      ) : null}

      {!isUser && <RetrievalCard steps={retrievalSteps} />}
      {!isUser && <ThoughtChain toolCalls={toolCalls} />}
      {!shouldHideAssistantBody ? (
        <div className={isUser ? "pr-16 whitespace-pre-wrap leading-7" : "markdown"}>
          {isUser ? (
            content
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {content}
            </ReactMarkdown>
          )}
        </div>
      ) : null}
    </article>
  );
}
