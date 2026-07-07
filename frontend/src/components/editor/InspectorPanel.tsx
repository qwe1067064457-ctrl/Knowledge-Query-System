"use client";

import { Database, RefreshCcw } from "lucide-react";

import { useAppStore } from "@/lib/store";

function formatCountLabel(label: string, value: number) {
  return (
    <div className="rounded-2xl border border-[var(--color-line)] bg-white/55 px-3 py-2">
      <p className="text-[10px] uppercase tracking-[0.24em] text-[var(--color-ink-soft)]">{label}</p>
      <p className="mt-1 text-sm font-medium text-[var(--color-ink)]">{value}</p>
    </div>
  );
}

export function InspectorPanel() {
  const {
    selectedGroupId,
    runtimeMemoryCore,
    runtimeMemoryOverview,
    refreshRuntimeMemory
  } = useAppStore();

  const globalItems =
    runtimeMemoryCore?.items.filter((item) => item.scope === "user_global") ?? [];
  const groupItems =
    runtimeMemoryCore?.items.filter((item) => item.scope === "user_group") ?? [];

  return (
    <aside className="panel flex h-full flex-col overflow-hidden rounded-[30px] p-4">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-[var(--color-ink-soft)]">
            Inspector
          </p>
          <h2 className="text-lg font-semibold tracking-[-0.04em]">运行时记忆侧栏</h2>
          <p className="mt-1 max-w-xs text-xs leading-5 text-[var(--color-ink-soft)]">
            这里只展示后端正式提供的 runtime memory，不再混入 skill snapshot 文件预览。
          </p>
        </div>
        <button
          className="flex items-center gap-2 rounded-full border border-[var(--color-line)] bg-white/70 px-4 py-2 text-sm text-[var(--color-ink-soft)]"
          onClick={() => void refreshRuntimeMemory(selectedGroupId)}
          type="button"
        >
          <RefreshCcw size={16} />
          刷新记忆
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto pr-1">
        <section className="rounded-[26px] border border-[var(--color-line)] bg-white/45 p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-[var(--color-ink-soft)]">
                Runtime Memory
              </p>
              <h3 className="mt-1 text-base font-semibold tracking-[-0.03em]">当前注入前的记忆底稿</h3>
              <p className="mt-1 text-xs leading-5 text-[var(--color-ink-soft)]">
                当前按 <code>default / {(runtimeMemoryOverview?.group_id ?? selectedGroupId) || "general"}</code> 读取。
              </p>
            </div>
            <div className="flex items-center gap-2 rounded-full bg-[rgba(15,139,141,0.12)] px-3 py-1 text-xs text-ocean">
              <Database size={14} />
              {runtimeMemoryOverview ? "API 已接通" : "等待加载"}
            </div>
          </div>

          {runtimeMemoryOverview ? (
            <>
              <div className="mt-4 grid grid-cols-2 gap-2">
                {formatCountLabel("Core Total", runtimeMemoryOverview.counts.core_total)}
                {formatCountLabel("Global Core", runtimeMemoryOverview.counts.user_global_core)}
                {formatCountLabel("Group Core", runtimeMemoryOverview.counts.user_group_core)}
                {formatCountLabel("Daily Logs", runtimeMemoryOverview.counts.daily_log_files)}
                {formatCountLabel("Daily Entries", runtimeMemoryOverview.counts.daily_log_entries)}
                {formatCountLabel("Domain Cases", runtimeMemoryOverview.counts.domain_case_entries)}
              </div>

              <details className="mt-4 rounded-3xl border border-[var(--color-line)] bg-white/55 px-4 py-3">
                <summary className="cursor-pointer list-none text-sm font-medium text-[var(--color-ink)]">
                  存储路径概览
                </summary>
                <div className="mt-3 space-y-2 text-xs leading-5 text-[var(--color-ink-soft)]">
                  <p>`user_global_core`: {runtimeMemoryOverview.storage.user_global_core}</p>
                  <p>`user_group_core`: {runtimeMemoryOverview.storage.user_group_core}</p>
                  <p>`daily_log_dir`: {runtimeMemoryOverview.storage.daily_log_dir}</p>
                  <p>`domain_case_file`: {runtimeMemoryOverview.storage.domain_case_file}</p>
                </div>
              </details>
            </>
          ) : (
            <div className="mt-4 rounded-3xl border border-dashed border-[var(--color-line)] bg-white/55 px-4 py-4 text-sm leading-6 text-[var(--color-ink-soft)]">
              运行时记忆暂未返回。若这里长期为空，优先检查 `/api/runtime/memory/core` 与 `/api/runtime/memory/overview`。
            </div>
          )}

          {runtimeMemoryCore ? (
            <div className="mt-4 space-y-3">
              <details className="rounded-3xl border border-[var(--color-line)] bg-white/55 px-4 py-3">
                <summary className="cursor-pointer list-none text-sm font-medium text-[var(--color-ink)]">
                  `user_global` 记忆 ({globalItems.length})
                </summary>
                <div className="mt-3 space-y-3">
                  {globalItems.length ? (
                    globalItems.map((item, index) => (
                      <article
                        className="rounded-2xl border border-[var(--color-line)] bg-white/70 px-3 py-3"
                        key={`${item.scope}-${item.title}-${index}`}
                      >
                        <div className="flex flex-wrap gap-2 text-[10px] uppercase tracking-[0.22em] text-[var(--color-ink-soft)]">
                          <span>{item.memory_type || "core"}</span>
                          <span>{item.source || "unknown"}</span>
                        </div>
                        <p className="mt-2 text-sm font-medium text-[var(--color-ink)]">
                          {item.title || item.subject || "未命名记忆"}
                        </p>
                        <p className="mt-2 text-sm leading-6 text-[var(--color-ink-soft)]">
                          {item.content}
                        </p>
                      </article>
                    ))
                  ) : (
                    <p className="text-sm text-[var(--color-ink-soft)]">暂无 `user_global` 记忆。</p>
                  )}
                </div>
              </details>

              <details className="rounded-3xl border border-[var(--color-line)] bg-white/55 px-4 py-3">
                <summary className="cursor-pointer list-none text-sm font-medium text-[var(--color-ink)]">
                  `user_group` 记忆 ({groupItems.length})
                </summary>
                <div className="mt-3 space-y-3">
                  {groupItems.length ? (
                    groupItems.map((item, index) => (
                      <article
                        className="rounded-2xl border border-[var(--color-line)] bg-white/70 px-3 py-3"
                        key={`${item.scope}-${item.title}-${index}`}
                      >
                        <div className="flex flex-wrap gap-2 text-[10px] uppercase tracking-[0.22em] text-[var(--color-ink-soft)]">
                          <span>{item.memory_type || "core"}</span>
                          <span>{item.group_id || "group"}</span>
                        </div>
                        <p className="mt-2 text-sm font-medium text-[var(--color-ink)]">
                          {item.title || item.subject || "未命名记忆"}
                        </p>
                        <p className="mt-2 text-sm leading-6 text-[var(--color-ink-soft)]">
                          {item.content}
                        </p>
                        {item.tags.length ? (
                          <div className="mt-2 flex flex-wrap gap-2">
                            {item.tags.map((tag) => (
                              <span
                                className="rounded-full bg-[rgba(15,139,141,0.12)] px-2 py-1 text-[10px] text-ocean"
                                key={tag}
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        ) : null}
                      </article>
                    ))
                  ) : (
                    <p className="text-sm text-[var(--color-ink-soft)]">暂无 `user_group` 记忆。</p>
                  )}
                </div>
              </details>
            </div>
          ) : null}
        </section>
      </div>
    </aside>
  );
}
