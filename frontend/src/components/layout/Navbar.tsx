"use client";

import Link from "next/link";
import { Database, FileSearch, PanelRightOpen, Plus, Sparkles } from "lucide-react";

import { useAppStore } from "@/lib/store";

export function Navbar() {
  const {
    createNewSession,
    groups,
    selectedGroupId,
    setSelectedGroupId,
    ragMode,
    toggleRagMode,
    renameCurrentSession,
    rebuildKnowledgeIndex,
    knowledgeIndexStatus,
    sessions,
    currentSessionId,
    inspectorOpen,
    setInspectorOpen
  } = useAppStore();

  const currentTitle =
    sessions.find((session) => session.id === currentSessionId)?.title ?? "新会话";
  const currentGroup = groups.find((group) => group.id === selectedGroupId) ?? null;
  const hasGroups = groups.length > 0;
  const isIndexBuilding = Boolean(knowledgeIndexStatus?.building);
  const knowledgeIndexLabel = isIndexBuilding ? "知识索引维护中" : "知识索引维护";
  const knowledgeIndexHint = isIndexBuilding
    ? "知识库索引维护中"
      : knowledgeIndexStatus?.ready
      ? `知识库索引已就绪 · 源文件 ${knowledgeIndexStatus.source_file_count ?? "?"} 个 · 当前已索引文件 ${knowledgeIndexStatus.indexed_files} 个 · 当前 chunk ${knowledgeIndexStatus.chunk_count ?? "?"} 条 · 上传或修改后应走自动/增量维护`
      : "知识库索引未就绪";

  return (
    <header className="panel flex items-center justify-between rounded-[30px] px-5 py-4">
      <div className="flex items-center gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[rgba(15,139,141,0.14)] text-ocean">
          <Sparkles size={20} />
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.32em] text-[var(--color-ink-soft)]">
            skill-rag
          </p>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold tracking-[-0.04em]">{currentTitle}</h1>
            {currentGroup ? (
              <span className="rounded-full bg-[rgba(15,139,141,0.12)] px-3 py-1 text-xs text-ocean">
                {currentGroup.name}
              </span>
            ) : null}
            <button
              className="rounded-full border border-[var(--color-line)] px-3 py-1 text-xs text-[var(--color-ink-soft)]"
              onClick={() => {
                const next = window.prompt("重命名当前会话", currentTitle);
                if (next) {
                  void renameCurrentSession(next);
                }
              }}
              type="button"
            >
              Rename
            </button>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-end gap-3">
        <Link
          className="flex items-center gap-2 rounded-full border border-[var(--color-line)] bg-white/60 px-4 py-2 text-sm"
          href="/groups"
        >
          <Database size={16} />
          组管理
        </Link>
        <select
          className="rounded-full border border-[var(--color-line)] bg-white/60 px-4 py-2 text-sm"
          disabled={!hasGroups}
          onChange={(event) => setSelectedGroupId(event.target.value)}
          value={selectedGroupId}
        >
          {hasGroups ? (
            groups.map((group) => (
              <option key={group.id} value={group.id}>
                {group.name}
              </option>
            ))
          ) : (
            <option value="">暂无可选组</option>
          )}
        </select>
        <button
          className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm ${
            hasGroups
              ? "border border-[var(--color-line)] bg-white/60"
              : "cursor-not-allowed bg-[rgba(13,37,48,0.08)] text-[var(--color-ink-soft)]"
          }`}
          disabled={!hasGroups}
          onClick={() => void createNewSession(selectedGroupId)}
          type="button"
        >
          <Plus size={16} />
          在当前组中新建会话
        </button>
        <button
          className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm ${
            ragMode
              ? "bg-ocean text-white"
              : "border border-[var(--color-line)] bg-white/60 text-ink"
          }`}
          onClick={() => void toggleRagMode()}
          type="button"
        >
          <Database size={16} />
          {ragMode ? "RAG 已开" : "RAG 已关"}
        </button>
        <button
          className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm ${
            isIndexBuilding
              ? "cursor-not-allowed bg-[rgba(15,139,141,0.12)] text-ocean"
              : "border border-[var(--color-line)] bg-white/60"
          }`}
          disabled={isIndexBuilding}
          onClick={() => void rebuildKnowledgeIndex()}
          type="button"
        >
          <FileSearch size={16} />
          {knowledgeIndexLabel}
        </button>
        <button
          className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm ${
            inspectorOpen
              ? "bg-[rgba(15,139,141,0.12)] text-ocean"
              : "border border-[var(--color-line)] bg-white/60"
          }`}
          onClick={() => setInspectorOpen(!inspectorOpen)}
          type="button"
        >
          <PanelRightOpen size={16} />
          {inspectorOpen ? "收起记忆侧栏" : "打开记忆侧栏"}
        </button>
        <div className="hidden items-center gap-2 rounded-full bg-[rgba(212,106,74,0.12)] px-4 py-2 text-sm text-[var(--color-ember)] md:flex">
          <FileSearch size={16} />
          {knowledgeIndexHint}
        </div>
      </div>
    </header>
  );
}
