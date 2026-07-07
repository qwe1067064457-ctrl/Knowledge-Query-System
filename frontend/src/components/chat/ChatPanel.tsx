"use client";

import { useEffect, useRef } from "react";

import { ChatInput } from "@/components/chat/ChatInput";
import { ChatMessage } from "@/components/chat/ChatMessage";
import {
  MOCK_TRACE_EVENTS,
  MOCK_TRACE_INTENT,
  MOCK_TRACE_WORKFLOW
} from "@/components/trace/mockTrace";
import { useAppStore } from "@/lib/store";

function readSavedScrollTop(sessionId: string) {
  if (typeof window === "undefined") {
    return null;
  }

  const rawValue = window.sessionStorage.getItem(`chat-scroll:${sessionId}`);
  if (!rawValue) {
    return null;
  }

  const parsed = Number(rawValue);
  return Number.isFinite(parsed) ? parsed : null;
}

function saveScrollTop(sessionId: string, scrollTop: number) {
  if (typeof window === "undefined") {
    return;
  }

  window.sessionStorage.setItem(`chat-scroll:${sessionId}`, String(scrollTop));
}

export function ChatPanel() {
  const {
    messages,
    currentSessionId,
    sendMessage,
    isStreaming,
    tokenStats,
    compressCurrentSession,
  } = useAppStore();
  const endRef = useRef<HTMLDivElement | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const scrollPositionsRef = useRef<Record<string, number>>({});
  const previousSessionIdRef = useRef<string | null>(null);
  const stickToBottomRef = useRef(false);
  const initializedSessionsRef = useRef<Record<string, boolean>>({});

  useEffect(() => {
    const container = scrollRef.current;
    const previousSessionId = previousSessionIdRef.current;
    if (!container || !currentSessionId) {
      previousSessionIdRef.current = currentSessionId;
      return;
    }

    if (previousSessionId && previousSessionId !== currentSessionId) {
      scrollPositionsRef.current[previousSessionId] = container.scrollTop;
      saveScrollTop(previousSessionId, container.scrollTop);
    }

    const savedTop = scrollPositionsRef.current[currentSessionId] ?? readSavedScrollTop(currentSessionId);
    if (typeof savedTop === "number") {
      container.scrollTop = savedTop;
      const distanceFromBottom =
        container.scrollHeight - container.clientHeight - container.scrollTop;
      stickToBottomRef.current = distanceFromBottom < 80;
    } else if (!initializedSessionsRef.current[currentSessionId]) {
      container.scrollTop = 0;
      // 首次进入且没有历史位置时，默认停在顶部，不把“空容器”误判成需要吸底。
      stickToBottomRef.current = false;
    } else {
      const distanceFromBottom =
        container.scrollHeight - container.clientHeight - container.scrollTop;
      stickToBottomRef.current = distanceFromBottom < 80;
    }

    initializedSessionsRef.current[currentSessionId] = true;
    previousSessionIdRef.current = currentSessionId;
  }, [currentSessionId]);

  useEffect(() => {
    const container = scrollRef.current;
    if (!container || !currentSessionId) {
      return;
    }

    if (stickToBottomRef.current) {
      endRef.current?.scrollIntoView({ behavior: "smooth" });
      return;
    }

    scrollPositionsRef.current[currentSessionId] = container.scrollTop;
  }, [currentSessionId, messages]);

  function handleScroll() {
    const container = scrollRef.current;
    if (!container || !currentSessionId) {
      return;
    }

    scrollPositionsRef.current[currentSessionId] = container.scrollTop;
    saveScrollTop(currentSessionId, container.scrollTop);
    const distanceFromBottom =
      container.scrollHeight - container.clientHeight - container.scrollTop;
    stickToBottomRef.current = distanceFromBottom < 80;
  }

  return (
    <section className="flex h-full min-w-0 flex-1 flex-col gap-4">
      <div className="panel flex items-center justify-between rounded-[30px] px-5 py-4">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-[var(--color-ink-soft)]">
            Agent Workspace
          </p>
          <h2 className="text-lg font-semibold tracking-[-0.04em]">Agent 决策链路</h2>
        </div>
        <div className="mono text-sm text-[var(--color-ink-soft)]">
          {tokenStats ? `${tokenStats.total_tokens} tokens` : "No metrics yet"}
        </div>
      </div>

      <div className="panel flex min-h-0 flex-1 flex-col rounded-[32px] p-5">
        <div className="flex-1 space-y-4 overflow-y-auto pr-2" onScroll={handleScroll} ref={scrollRef}>
          {!messages.length && (
            <>
              <div className="rounded-[28px] border border-dashed border-[var(--color-line)] bg-white/45 p-8">
                <p className="text-xs uppercase tracking-[0.28em] text-[var(--color-ink-soft)]">
                  Ready
                </p>
                <h3 className="mt-2 text-3xl font-semibold tracking-[-0.05em]">
                  一个本地、透明、文件驱动的 Agent 工作台
                </h3>
                <p className="mt-3 max-w-2xl text-[var(--color-ink-soft)]">
                  现在除了答案本身，也可以把 route、gate、争议证据裁决和 workflow trace
                  放进 assistant message 顶部展示。后端还没推送 trace event 时，下面这条本地
                  preview 可直接预览 UI。
                </p>
              </div>

              <ChatMessage
                content="这是本地 trace fixture 预览。真实后端尚未推送 `intent_analysis` / `workflow_plan` 时，正式消息会自动隐藏这些区域，不会报错。"
                executionEvents={MOCK_TRACE_EVENTS}
                intentTrace={MOCK_TRACE_INTENT}
                retrievalSteps={[]}
                role="assistant"
                toolCalls={[]}
                workflowTrace={MOCK_TRACE_WORKFLOW}
              />
            </>
          )}

          {messages.map((message) => (
            <ChatMessage
              content={message.content}
              executionEvents={message.executionEvents}
              intentTrace={message.intentTrace}
              isStreaming={
                isStreaming &&
                message.role === "assistant" &&
                message.id === messages[messages.length - 1]?.id
              }
              key={message.id}
              onRetry={
                message.role === "user"
                  ? () => {
                      void sendMessage(message.content);
                    }
                  : null
              }
              retrievalSteps={message.retrievalSteps}
              role={message.role}
              toolCalls={message.toolCalls}
              workflowTrace={message.workflowTrace}
            />
          ))}
          <div ref={endRef} />
        </div>
      </div>

      <ChatInput
        canCompress={Boolean(currentSessionId)}
        disabled={isStreaming}
        onCompress={compressCurrentSession}
        onSend={sendMessage}
        totalTokens={tokenStats?.total_tokens ?? null}
      />
    </section>
  );
}
