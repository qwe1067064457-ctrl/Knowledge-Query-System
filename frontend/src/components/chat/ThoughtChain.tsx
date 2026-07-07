"use client";

import { TerminalSquare } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import type { ToolCall } from "@/lib/api";

function readText(value: unknown) {
  return typeof value === "string" ? value : "";
}

function formatBlock(value: unknown) {
  const text = readText(value).trim();
  if (!text) {
    return "暂无";
  }

  try {
    return JSON.stringify(JSON.parse(text), null, 2);
  } catch {
    return text;
  }
}

export function ThoughtChain({ toolCalls }: { toolCalls: ToolCall[] }) {
  const visibleToolCalls = useMemo(
    () =>
      toolCalls.filter((toolCall) => {
        const toolName = readText(toolCall.tool).trim();
        const inputText = readText(toolCall.input).trim();
        const outputText = readText(toolCall.output).trim();
        const hasOnlyPlaceholderTool = toolName === "tool" && !inputText && !outputText;
        return !hasOnlyPlaceholderTool && Boolean(toolName || inputText || outputText);
      }),
    [toolCalls]
  );
  const activeTool =
    [...visibleToolCalls].reverse().find((toolCall) => !readText(toolCall.output).trim()) ?? null;
  const toolNames = useMemo(
    () =>
      Array.from(
        new Set(visibleToolCalls.map((toolCall) => readText(toolCall.tool)).filter(Boolean))
      ),
    [visibleToolCalls]
  );
  const [isOpen, setIsOpen] = useState(Boolean(activeTool));

  useEffect(() => {
    if (activeTool) {
      setIsOpen(true);
    }
  }, [activeTool, visibleToolCalls.length]);

  if (!visibleToolCalls.length) {
    return null;
  }

  return (
    <details
      className="mb-4 rounded-3xl border border-[rgba(212,106,74,0.18)] bg-[rgba(212,106,74,0.08)] p-4"
      onToggle={(event) => setIsOpen(event.currentTarget.open)}
      open={isOpen}
    >
      <summary className="flex cursor-pointer list-none items-start gap-3 text-sm font-medium text-[var(--color-ember)]">
        <TerminalSquare className="mt-0.5 shrink-0" size={16} />
        <div className="min-w-0 flex-1">
          <div>
            {activeTool ? `正在调用 ${readText(activeTool.tool) || "tool"}` : `工具调用 ${visibleToolCalls.length} 次`}
          </div>
          <div className="truncate text-xs font-normal text-[var(--color-ink-soft)]">
            {toolNames.join(" -> ") || "暂无工具名"}
          </div>
        </div>
        <span className="shrink-0 text-xs font-normal text-[var(--color-ink-soft)]">
          {isOpen ? "收起" : "展开"}
        </span>
      </summary>

      <div className="mt-3 space-y-3">
        {visibleToolCalls.map((toolCall, index) => {
          const isFinished = Boolean(readText(toolCall.output).trim());
          const toolName = readText(toolCall.tool) || "tool";

          return (
            <div className="rounded-2xl bg-white/70 p-3" key={`${toolName}-${index}`}>
              <div className="mb-2 flex items-center justify-between gap-3 text-sm font-medium">
                <span>{toolName}</span>
                <span
                  className={`rounded-full px-2 py-1 text-[11px] font-medium ${
                    isFinished
                      ? "bg-[rgba(15,139,141,0.12)] text-[var(--color-ocean)]"
                      : "bg-[rgba(212,106,74,0.12)] text-[var(--color-ember)]"
                  }`}
                >
                  {isFinished ? "已完成" : "运行中"}
                </span>
              </div>

              <div className="space-y-2 text-xs">
                <div className="rounded-2xl bg-[rgba(13,37,48,0.06)] p-3">
                  <div className="mb-1 font-medium text-[var(--color-ink-soft)]">输入</div>
                  <pre className="mono whitespace-pre-wrap">{formatBlock(toolCall.input)}</pre>
                </div>
                <div className="rounded-2xl bg-[rgba(13,37,48,0.06)] p-3">
                  <div className="mb-1 font-medium text-[var(--color-ink-soft)]">输出</div>
                  <pre className="mono whitespace-pre-wrap">{formatBlock(toolCall.output)}</pre>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </details>
  );
}
