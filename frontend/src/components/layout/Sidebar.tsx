"use client";

import { useMemo } from "react";
import { MessageSquare, Plus, Trash2 } from "lucide-react";

import { useAppStore } from "@/lib/store";

function preview(text: string) {
  return text.length > 72 ? `${text.slice(0, 72)}...` : text;
}

function isVisibleSession(messageCount: number, sessionId: string, currentSessionId: string | null) {
  return messageCount > 0 || sessionId === currentSessionId;
}

export function Sidebar() {
  const {
    sessions,
    groups,
    selectedGroupId,
    setSelectedGroupId,
    currentSessionId,
    selectSession,
    createNewSession,
    removeSession,
    messages
  } = useAppStore();
  const visibleSessions = useMemo(
    () =>
      selectedGroupId
        ? sessions.filter(
            (session) =>
              session.active_group_id === selectedGroupId &&
              isVisibleSession(session.message_count, session.id, currentSessionId)
          )
        : [],
    [currentSessionId, selectedGroupId, sessions]
  );
  const hasGroups = groups.length > 0;

  return (
    <aside className="panel flex h-full flex-col overflow-hidden rounded-[30px] p-4">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-[var(--color-ink-soft)]">
            Sessions
          </p>
          <h2 className="text-lg font-semibold tracking-[-0.04em]">按组管理会话</h2>
        </div>
        <button
          className={`flex h-10 w-10 items-center justify-center rounded-2xl ${
            hasGroups
              ? "bg-[rgba(15,139,141,0.12)] text-ocean"
              : "cursor-not-allowed bg-[rgba(13,37,48,0.08)] text-[var(--color-ink-soft)]"
          }`}
          disabled={!hasGroups}
          onClick={() => void createNewSession(selectedGroupId)}
          type="button"
        >
          <Plus size={18} />
        </button>
      </div>

      <div className="mb-4 rounded-[20px] border border-[var(--color-line)] bg-white/50 p-3">
        <label className="block text-xs uppercase tracking-[0.24em] text-[var(--color-ink-soft)]">
          当前组
        </label>
        {hasGroups ? (
          <select
            className="mt-2 w-full rounded-2xl border border-[var(--color-line)] bg-white/70 px-3 py-2 text-sm"
            onChange={(event) => setSelectedGroupId(event.target.value)}
            value={selectedGroupId}
          >
            {groups.map((group) => (
              <option key={group.id} value={group.id}>
                {group.name}
              </option>
            ))}
          </select>
        ) : (
          <div className="mt-2 rounded-2xl border border-dashed border-[var(--color-line)] bg-white/60 px-3 py-3 text-sm text-[var(--color-ink-soft)]">
            后端当前没有返回可选组。
          </div>
        )}
        <p className="mt-2 text-xs leading-5 text-[var(--color-ink-soft)]">
          {hasGroups
            ? "新建会话会绑定到当前组；列表也按当前组过滤显示。"
            : "这里现在显示为空，表示前端没有拿到后端组列表，不再伪造默认组。"}
        </p>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-4">
        <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
          {visibleSessions.map((session) => (
            <div
              className={`rounded-3xl border px-4 py-3 transition ${
                session.id === currentSessionId
                  ? "border-transparent bg-[rgba(15,139,141,0.16)]"
                  : "border-[var(--color-line)] bg-white/45"
              }`}
              key={session.id}
            >
              <button
                className="w-full text-left"
                onClick={() => void selectSession(session.id)}
                type="button"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-medium">{session.title}</p>
                    <p className="mt-1 text-xs text-[var(--color-ink-soft)]">
                      {session.message_count} 条消息
                    </p>
                    <p className="mt-1 text-xs text-[var(--color-ink-soft)]">
                      组：{groups.find((group) => group.id === session.active_group_id)?.name ?? session.active_group_id}
                    </p>
                  </div>
                  <MessageSquare className="mt-1 text-[var(--color-ink-soft)]" size={16} />
                </div>
              </button>
              <button
                className="mt-3 flex items-center gap-2 text-xs text-[var(--color-ember)]"
                onClick={() => void removeSession(session.id)}
                type="button"
              >
                <Trash2 size={14} />
                删除
              </button>
            </div>
          ))}
          {!visibleSessions.length ? (
            <div className="rounded-3xl border border-dashed border-[var(--color-line)] bg-white/45 px-4 py-4 text-sm leading-6 text-[var(--color-ink-soft)]">
              {hasGroups
                ? "当前组下还没有会话。可以直接在上方为该组新建一个会话。"
                : "等待后端返回组列表后，这里才会按组过滤展示会话。"}
            </div>
          ) : null}
        </div>

        <div className="flex h-40 shrink-0 flex-col rounded-[24px] border border-[var(--color-line)] bg-white/40 p-3">
          <p className="text-xs uppercase tracking-[0.28em] text-[var(--color-ink-soft)]">
            Current Messages
          </p>
          <div className="mt-3 min-h-0 space-y-3 overflow-y-auto pr-1">
            {messages.map((message) => (
              <div
                className="rounded-2xl border border-[var(--color-line)] bg-white/60 px-3 py-2"
                key={message.id}
              >
                <div className="mb-1 flex items-center justify-between text-xs uppercase tracking-[0.2em] text-[var(--color-ink-soft)]">
                  <span>{message.role}</span>
                  <span>{message.toolCalls.length} tools</span>
                </div>
                <p className="text-sm text-[var(--color-ink-soft)]">{preview(message.content)}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
}
