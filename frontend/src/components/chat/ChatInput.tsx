"use client";

import { DatabaseZap, SendHorizonal } from "lucide-react";
import { useState } from "react";

const CONTEXT_TOKEN_BUDGET = 6000;

function formatBudgetRatio(totalTokens: number | null) {
  if (!totalTokens) {
    return {
      label: "暂无预算统计",
      detail: "当前还没有 token 统计，发送或切换会话后这里会更新。",
      percent: 0,
    };
  }

  const percent = Math.min(100, (totalTokens / CONTEXT_TOKEN_BUDGET) * 100);
  return {
    label: `${totalTokens} / ${CONTEXT_TOKEN_BUDGET} tokens`,
    detail: `按当前上下文预算估算，约占 ${percent.toFixed(1)}% 。接近上限时更适合先压缩再继续追问。`,
    percent,
  };
}

export function ChatInput({
  disabled,
  onSend,
  onCompress,
  canCompress,
  totalTokens,
}: {
  disabled: boolean;
  onSend: (value: string) => Promise<void>;
  onCompress: () => Promise<void>;
  canCompress: boolean;
  totalTokens: number | null;
}) {
  const [value, setValue] = useState("");
  const budgetInfo = formatBudgetRatio(totalTokens);

  return (
    <div className="panel rounded-[28px] p-3">
      <textarea
        className="min-h-28 w-full resize-none rounded-[22px] border border-[var(--color-line)] bg-white/70 px-4 py-3 outline-none"
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
            event.preventDefault();
            const nextValue = value.trim();
            if (!nextValue) {
              return;
            }
            void onSend(nextValue);
            setValue("");
          }
        }}
        placeholder="输入你的问题，Cmd/Ctrl + Enter 发送"
        value={value}
      />
      <div className="mt-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="group relative">
            <button
              className="flex items-center gap-2 rounded-full border border-[var(--color-line)] bg-white/70 px-3 py-2 text-sm text-[var(--color-ink)] disabled:cursor-not-allowed disabled:bg-[rgba(13,37,48,0.06)] disabled:text-[var(--color-ink-soft)]"
              disabled={!canCompress || disabled}
              onClick={() => void onCompress()}
              type="button"
            >
              <DatabaseZap size={16} />
              压缩
            </button>
            <div className="pointer-events-none absolute bottom-[calc(100%+10px)] left-0 hidden w-72 rounded-2xl border border-[var(--color-line)] bg-white/95 p-3 shadow-[0_16px_40px_rgba(13,37,48,0.12)] group-hover:block">
              <div className="text-sm font-medium text-[var(--color-ink)]">上下文预算占比</div>
              <div className="mt-1 text-sm leading-6 text-[var(--color-ink-soft)]">
                {budgetInfo.detail}
              </div>
              <div className="mt-3 rounded-full bg-[rgba(13,37,48,0.08)]">
                <div
                  className="h-2 rounded-full bg-ocean transition-all"
                  style={{ width: `${budgetInfo.percent}%` }}
                />
              </div>
              <div className="mt-2 text-xs text-[var(--color-ink-soft)]">{budgetInfo.label}</div>
            </div>
          </div>
          <p className="text-sm text-[var(--color-ink-soft)]">
            支持工具调用、Memory 检索和多段响应。
          </p>
        </div>
        <button
          className="flex items-center gap-2 rounded-full bg-ocean px-4 py-2 text-sm text-white disabled:cursor-not-allowed disabled:bg-[rgba(15,139,141,0.45)]"
          disabled={disabled || !value.trim()}
          onClick={() => {
            const nextValue = value.trim();
            if (!nextValue) {
              return;
            }
            void onSend(nextValue);
            setValue("");
          }}
          type="button"
        >
          <SendHorizonal size={16} />
          发送
        </button>
      </div>
    </div>
  );
}
