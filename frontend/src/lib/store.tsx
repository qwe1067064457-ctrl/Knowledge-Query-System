"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode
} from "react";

import {
  compressSession,
  createSession,
  deleteSession,
  getKnowledgeIndexStatus,
  getRagMode,
  getSessionAgentTraces,
  getRuntimeMemoryCore,
  getRuntimeMemoryOverview,
  getSessionHistory,
  getSessionTokens,
  listGroups,
  listSessions,
  listSkills,
  loadFile,
  mergeIntentTrace,
  mergeWorkflowTrace,
  normalizeExecutionEvent,
  normalizeIntentTrace,
  normalizeRetrievalStep,
  normalizeToolCall,
  normalizeWorkflowTrace,
  renameSession,
  rebuildKnowledgeIndex as rebuildKnowledgeIndexRequest,
  saveFile,
  setRagMode,
  streamChat,
  type ExecutionEvent,
  type GroupRecord,
  type IntentTrace,
  type KnowledgeIndexStatus,
  type RetrievalStep,
  type RuntimeMemoryCore,
  type RuntimeMemoryOverview,
  type SessionAgentTraceEntry,
  type SessionSummary,
  type ToolCall,
  type WorkflowTrace
} from "@/lib/api";

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolCalls: ToolCall[];
  retrievalSteps: RetrievalStep[];
  intentTrace?: IntentTrace;
  workflowTrace?: WorkflowTrace;
  executionEvents: ExecutionEvent[];
};

type TokenStats = {
  system_tokens: number;
  message_tokens: number;
  total_tokens: number;
};

type AppStore = {
  sessions: SessionSummary[];
  groups: GroupRecord[];
  selectedGroupId: string;
  currentSessionId: string | null;
  messages: Message[];
  isStreaming: boolean;
  ragMode: boolean;
  skills: Array<{ name: string; description: string; path: string }>;
  editableFiles: string[];
  inspectorPath: string;
  inspectorContent: string;
  inspectorDirty: boolean;
  inspectorOpen: boolean;
  sidebarWidth: number;
  inspectorWidth: number;
  tokenStats: TokenStats | null;
  knowledgeIndexStatus: KnowledgeIndexStatus | null;
  runtimeMemoryCore: RuntimeMemoryCore | null;
  runtimeMemoryOverview: RuntimeMemoryOverview | null;
  createNewSession: (groupId?: string) => Promise<void>;
  selectSession: (sessionId: string) => Promise<void>;
  setSelectedGroupId: (groupId: string) => void;
  sendMessage: (value: string) => Promise<void>;
  toggleRagMode: () => Promise<void>;
  renameCurrentSession: (title: string) => Promise<void>;
  removeSession: (sessionId: string) => Promise<void>;
  loadInspectorFile: (path: string) => Promise<void>;
  updateInspectorContent: (value: string) => void;
  saveInspector: () => Promise<void>;
  compressCurrentSession: () => Promise<void>;
  rebuildKnowledgeIndex: () => Promise<void>;
  refreshRuntimeMemory: (groupId?: string) => Promise<void>;
  setInspectorOpen: (open: boolean) => void;
  setSidebarWidth: (width: number) => void;
  setInspectorWidth: (width: number) => void;
};

const FIXED_FILES = [
  "SKILLS_SNAPSHOT.md"
];

const DEFAULT_GROUP_ID = "general";
const DEFAULT_INSPECTOR_FILE = FIXED_FILES[0];
let hasBootstrappedAppStore = false;

const StoreContext = createContext<AppStore | null>(null);

function makeId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

// 0 消息的新会话现在只保留为本地草稿，不再作为正式会话长期展示。
function isRenderableSession(session: SessionSummary) {
  return session.message_count > 0;
}

function buildMessage(partial: Partial<Message> & Pick<Message, "role" | "content">): Message {
  return {
    id: partial.id ?? makeId(),
    role: partial.role,
    content: partial.content,
    toolCalls: partial.toolCalls ?? [],
    retrievalSteps: partial.retrievalSteps ?? [],
    intentTrace: partial.intentTrace,
    workflowTrace: partial.workflowTrace,
    executionEvents: partial.executionEvents ?? []
  };
}

// 历史接口还未稳定持久化 trace，按位置回填本地 trace，避免流式完成后立刻丢失可视化信息。
function mergeMessagesWithLocalTrace(historyMessages: Message[], existingMessages: Message[]) {
  return historyMessages.map((message, index) => {
    const localMessage = existingMessages[index];
    if (!localMessage || localMessage.role !== message.role) {
      return message;
    }

    return {
      ...message,
      intentTrace: message.intentTrace ?? localMessage.intentTrace,
      workflowTrace: message.workflowTrace ?? localMessage.workflowTrace,
      executionEvents: message.executionEvents.length
        ? message.executionEvents
        : localMessage.executionEvents
    };
  });
}

function toUiMessages(history: Awaited<ReturnType<typeof getSessionHistory>>["messages"]) {
  return history.map((message) =>
    buildMessage({
      role: message.role,
      content: message.content ?? "",
      toolCalls: (message.tool_calls ?? [])
        .map((toolCall) => normalizeToolCall(toolCall))
        .filter((toolCall): toolCall is ToolCall => toolCall !== null),
      retrievalSteps: (message.retrieval_steps ?? [])
        .map((step) => normalizeRetrievalStep(step))
        .filter((step): step is RetrievalStep => step !== null),
      intentTrace: normalizeIntentTrace(message.intent_trace) ?? undefined,
      workflowTrace: normalizeWorkflowTrace(message.workflow_trace) ?? undefined,
      executionEvents: (message.execution_events ?? [])
        .map((event) => normalizeExecutionEvent(event))
        .filter((event): event is ExecutionEvent => event !== null)
    })
  );
}

function mergeMessagesWithAgentTraces(
  messages: Message[],
  traceEntries: SessionAgentTraceEntry[]
) {
  if (!traceEntries.length) {
    return messages;
  }

  let assistantIndex = 0;

  return messages.map((message) => {
    if (message.role !== "assistant") {
      return message;
    }

    const traceEntry = traceEntries[assistantIndex];
    assistantIndex += 1;

    const hasTrace =
      Boolean(message.intentTrace || message.workflowTrace) ||
      message.executionEvents.length > 0;
    if (hasTrace) {
      return message;
    }

    if (!traceEntry) {
      return message;
    }

    const intentTrace = normalizeIntentTrace(traceEntry.intent_trace) ?? undefined;
    const workflowTrace = normalizeWorkflowTrace(traceEntry.workflow_trace) ?? undefined;
    const executionEvents = (traceEntry.execution_events ?? [])
      .map((event) => normalizeExecutionEvent(event))
      .filter((event): event is ExecutionEvent => event !== null);

    if (!intentTrace && !workflowTrace && !executionEvents.length) {
      return message;
    }

    return {
      ...message,
      intentTrace,
      workflowTrace,
      executionEvents
    };
  });
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [groups, setGroups] = useState<GroupRecord[]>([]);
  const [selectedGroupId, setSelectedGroupId] = useState("");
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [ragMode, setRagModeState] = useState(false);
  const [skills, setSkills] = useState<Array<{ name: string; description: string; path: string }>>([]);
  const [inspectorPath, setInspectorPath] = useState(DEFAULT_INSPECTOR_FILE);
  const [inspectorContent, setInspectorContent] = useState("");
  const [inspectorDirty, setInspectorDirty] = useState(false);
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(308);
  const [inspectorWidth, setInspectorWidth] = useState(360);
  const [tokenStats, setTokenStats] = useState<TokenStats | null>(null);
  const [knowledgeIndexStatus, setKnowledgeIndexStatus] = useState<KnowledgeIndexStatus | null>(
    null
  );
  const [runtimeMemoryCore, setRuntimeMemoryCore] = useState<RuntimeMemoryCore | null>(null);
  const [runtimeMemoryOverview, setRuntimeMemoryOverview] = useState<RuntimeMemoryOverview | null>(
    null
  );
  const hasHydratedGroupEffectsRef = useRef(false);

  const editableFiles = useMemo(
    () => [...FIXED_FILES, ...skills.map((skill) => skill.path)],
    [skills]
  );

  async function refreshSessions() {
    const nextSessions = await listSessions();
    setSessions(nextSessions);
    return nextSessions;
  }

  async function refreshGroups() {
    const nextGroups = await listGroups();
    setGroups(nextGroups);
    return nextGroups;
  }

  async function refreshSkills() {
    setSkills(await listSkills());
  }

  const refreshKnowledgeIndexStatus = useCallback(async (groupId?: string) => {
    const resolvedGroupId = groupId || selectedGroupId || groups[0]?.id;
    setKnowledgeIndexStatus(await getKnowledgeIndexStatus(resolvedGroupId));
  }, [groups, selectedGroupId]);

  const refreshRuntimeMemory = useCallback(async (groupId?: string) => {
    const resolvedGroupId = groupId || selectedGroupId || groups[0]?.id || DEFAULT_GROUP_ID;
    const [nextCore, nextOverview] = await Promise.all([
      getRuntimeMemoryCore({ user_id: "default", group_id: resolvedGroupId }),
      getRuntimeMemoryOverview({ user_id: "default", group_id: resolvedGroupId })
    ]);
    setRuntimeMemoryCore(nextCore);
    setRuntimeMemoryOverview(nextOverview);
  }, [groups, selectedGroupId]);

  async function refreshSessionDetails(sessionId: string) {
    const [history, tokens, agentTraceRecord] = await Promise.all([
      getSessionHistory(sessionId),
      getSessionTokens(sessionId),
      getSessionAgentTraces(sessionId).catch(() => null)
    ]);
    const nextMessages = mergeMessagesWithAgentTraces(
      toUiMessages(history.messages),
      agentTraceRecord?.traces ?? []
    );
    setMessages((current) => mergeMessagesWithLocalTrace(nextMessages, current));
    setTokenStats(tokens);
  }

  async function createNewSession(groupId?: string) {
    const activeGroupId = groupId ?? selectedGroupId ?? groups[0]?.id ?? DEFAULT_GROUP_ID;
    setSelectedGroupId(activeGroupId);
    setCurrentSessionId(null);
    setMessages([]);
    setTokenStats(null);
  }

  async function selectSession(sessionId: string) {
    const targetSession = sessions.find((session) => session.id === sessionId);
    if (targetSession?.active_group_id) {
      setSelectedGroupId(targetSession.active_group_id);
    }
    setCurrentSessionId(sessionId);
    await refreshSessionDetails(sessionId);
  }

  async function ensureSession() {
    if (currentSessionId) {
      return currentSessionId;
    }

    const activeGroupId = selectedGroupId || groups[0]?.id || DEFAULT_GROUP_ID;
    const created = await createSession("新会话", {
      active_group_id: activeGroupId,
      allowed_group_ids: [activeGroupId]
    });
    setCurrentSessionId(created.id);
    await refreshSessions();
    setSelectedGroupId(created.active_group_id || activeGroupId);
    return created.id;
  }

  async function sendMessage(value: string) {
    if (!value.trim() || isStreaming) {
      return;
    }

    const sessionId = await ensureSession();
    const userMessage = buildMessage({
      role: "user",
      content: value.trim()
    });
    const assistantMessage = buildMessage({
      role: "assistant",
      content: ""
    });

    setMessages((prev) => [...prev, userMessage, assistantMessage]);
    setIsStreaming(true);

    let activeAssistantId = assistantMessage.id;

    const patchAssistant = (updater: (message: Message) => Message) => {
      setMessages((prev) =>
        prev.map((message) => (message.id === activeAssistantId ? updater(message) : message))
      );
    };

    try {
      await streamChat(
        { message: value.trim(), session_id: sessionId },
        {
          onEvent(event, data) {
            if (event === "retrieval") {
              const step = normalizeRetrievalStep(data);
              if (!step) {
                return;
              }
              patchAssistant((message) => ({
                ...message,
                retrievalSteps: [...message.retrievalSteps, step]
              }));
              return;
            }

            if (event === "intent_analysis") {
              const trace = normalizeIntentTrace(data);
              patchAssistant((message) => ({
                ...message,
                intentTrace: mergeIntentTrace(message.intentTrace, trace)
              }));
              return;
            }

            if (event === "workflow_plan") {
              const trace = normalizeWorkflowTrace(data);
              patchAssistant((message) => ({
                ...message,
                workflowTrace: mergeWorkflowTrace(message.workflowTrace, trace)
              }));
              return;
            }

            if (event === "execution_update") {
              const executionEvent = normalizeExecutionEvent(data);
              const workflowTrace = normalizeWorkflowTrace(data);
              patchAssistant((message) => ({
                ...message,
                executionEvents: executionEvent
                  ? [...message.executionEvents, executionEvent]
                  : message.executionEvents,
                workflowTrace: mergeWorkflowTrace(message.workflowTrace, workflowTrace)
              }));
              return;
            }

            if (event === "token") {
              patchAssistant((message) => ({
                ...message,
                content: `${message.content}${String(data.content ?? "")}`
              }));
              return;
            }

            if (event === "tool_start") {
              const toolName = typeof data.tool === "string" ? data.tool.trim() : "";
              const inputText =
                typeof data.input === "string"
                  ? data.input
                  : data.input === undefined || data.input === null
                    ? ""
                    : JSON.stringify(data.input);
              if (!toolName && !inputText.trim()) {
                return;
              }

              patchAssistant((message) => ({
                ...message,
                toolCalls: [
                  ...message.toolCalls,
                  {
                    tool: toolName,
                    input: inputText,
                    output: ""
                  }
                ]
              }));
              return;
            }

            if (event === "tool_end") {
              const outputText =
                typeof data.output === "string"
                  ? data.output
                  : data.output === undefined || data.output === null
                    ? ""
                    : JSON.stringify(data.output);
              patchAssistant((message) => ({
                ...message,
                toolCalls: message.toolCalls.map((toolCall, index, list) =>
                  index === list.length - 1
                    ? { ...toolCall, output: outputText }
                    : toolCall
                )
              }));
              return;
            }

            if (event === "new_response") {
              const nextAssistant = buildMessage({
                role: "assistant",
                content: ""
              });
              activeAssistantId = nextAssistant.id;
              setMessages((prev) => [...prev, nextAssistant]);
              return;
            }

            if (event === "done") {
              const finalContent = String(data.content ?? "");
              patchAssistant((message) =>
                message.content
                  ? message
                  : {
                      ...message,
                      content: finalContent
                    }
              );
              return;
            }

            if (event === "title") {
              void refreshSessions();
              return;
            }

            if (event === "error") {
              patchAssistant((message) => ({
                ...message,
                content:
                  message.content || `请求失败: ${String(data.error ?? "unknown error")}`
              }));
            }
          }
        }
      );
    } finally {
      setIsStreaming(false);
      await refreshSessions();
      await refreshSessionDetails(sessionId);
    }
  }

  async function toggleRagMode() {
    const next = !ragMode;
    setRagModeState(next);
    try {
      await setRagMode(next);
    } catch (error) {
      setRagModeState(!next);
      throw error;
    }
  }

  async function renameCurrentSession(title: string) {
    if (!currentSessionId || !title.trim()) {
      return;
    }
    await renameSession(currentSessionId, title.trim());
    await refreshSessions();
  }

  async function removeSession(sessionId: string) {
    await deleteSession(sessionId);
    const nextSessions = await refreshSessions();
    const nextRenderableSessions = nextSessions.filter(isRenderableSession);
    if (currentSessionId === sessionId) {
      setSessions(nextSessions);
      if (nextRenderableSessions.length) {
        setCurrentSessionId(nextRenderableSessions[0].id);
        setSelectedGroupId(nextRenderableSessions[0].active_group_id || selectedGroupId);
        await refreshSessionDetails(nextRenderableSessions[0].id);
      } else {
        setCurrentSessionId(null);
        setMessages([]);
        setTokenStats(null);
      }
    }
  }

  async function loadInspectorFile(path: string) {
    setInspectorPath(path);
    try {
      const file = await loadFile(path);
      setInspectorContent(file.content);
      setInspectorDirty(false);
    } catch (error) {
      const detail = error instanceof Error ? error.message : String(error);
      setInspectorContent(
        `# 文件暂时不可读\n\n- path: ${path}\n- reason: ${detail}\n\n当前前端会继续保活，不会因为单个 inspector 文件失败而中断页面。`
      );
      setInspectorDirty(false);
    }
  }

  function updateInspectorContent(value: string) {
    setInspectorContent(value);
    setInspectorDirty(true);
  }

  async function saveInspector() {
    await saveFile(inspectorPath, inspectorContent);
    setInspectorDirty(false);
    await refreshSkills();
  }

  async function compressCurrentSession() {
    if (!currentSessionId) {
      return;
    }
    await compressSession(currentSessionId);
    await refreshSessionDetails(currentSessionId);
    await refreshSessions();
  }

  async function rebuildKnowledgeIndex() {
    const resolvedGroupId = selectedGroupId || groups[0]?.id;
    await rebuildKnowledgeIndexRequest(resolvedGroupId);
    await refreshKnowledgeIndexStatus(resolvedGroupId);
  }

  useEffect(() => {
    if (hasBootstrappedAppStore) {
      return;
    }

    hasBootstrappedAppStore = true;

    void (async () => {
      const [initialSessions, initialGroups, rag, initialSkills] = await Promise.all([
        listSessions(),
        listGroups(),
        getRagMode(),
        listSkills()
      ]);

      const initialSelectedGroupId = initialGroups[0]?.id || "";
      const initialKnowledgeIndexStatus = await getKnowledgeIndexStatus(
        initialSelectedGroupId || undefined
      );

      setSessions(initialSessions);
      setGroups(initialGroups);
      setRagModeState(rag.enabled);
      setSkills(initialSkills);
      setKnowledgeIndexStatus(initialKnowledgeIndexStatus);

      const initialRenderableSessions = initialSessions.filter(isRenderableSession);

      if (initialRenderableSessions.length) {
        setCurrentSessionId(initialRenderableSessions[0].id);
        const nextSelectedGroupId =
          initialRenderableSessions[0].active_group_id || initialSelectedGroupId || DEFAULT_GROUP_ID;
        setSelectedGroupId(nextSelectedGroupId);
        await refreshSessionDetails(initialRenderableSessions[0].id);
        await refreshRuntimeMemory(nextSelectedGroupId);
      } else {
        setCurrentSessionId(null);
        setMessages([]);
        setTokenStats(null);
        setSelectedGroupId(initialSelectedGroupId);
        await refreshRuntimeMemory(initialSelectedGroupId || DEFAULT_GROUP_ID);
      }

      await loadInspectorFile(DEFAULT_INSPECTOR_FILE);
    })();
  }, [refreshRuntimeMemory]);

  useEffect(() => {
    if (!selectedGroupId) {
      return;
    }

    if (!hasHydratedGroupEffectsRef.current) {
      hasHydratedGroupEffectsRef.current = true;
      return;
    }

    void refreshRuntimeMemory(selectedGroupId);
    void refreshKnowledgeIndexStatus(selectedGroupId);
  }, [refreshKnowledgeIndexStatus, refreshRuntimeMemory, selectedGroupId]);

  useEffect(() => {
    if (currentSessionId) {
      return;
    }

    setMessages([]);
    setTokenStats(null);
  }, [currentSessionId]);

  useEffect(() => {
    if (!knowledgeIndexStatus?.building) {
      return;
    }

    const timer = window.setInterval(() => {
      void refreshKnowledgeIndexStatus();
    }, 3000);

    return () => window.clearInterval(timer);
  }, [knowledgeIndexStatus?.building, refreshKnowledgeIndexStatus]);

  const value: AppStore = {
    sessions,
    groups,
    selectedGroupId,
    currentSessionId,
    messages,
    isStreaming,
    ragMode,
    skills,
    editableFiles,
    inspectorPath,
    inspectorContent,
    inspectorDirty,
    inspectorOpen,
    sidebarWidth,
    inspectorWidth,
    tokenStats,
    knowledgeIndexStatus,
    runtimeMemoryCore,
    runtimeMemoryOverview,
    createNewSession,
    selectSession,
    setSelectedGroupId,
    sendMessage,
    toggleRagMode,
    renameCurrentSession,
    removeSession,
    loadInspectorFile,
    updateInspectorContent,
    saveInspector,
    compressCurrentSession,
    rebuildKnowledgeIndex,
    refreshRuntimeMemory,
    setInspectorOpen,
    setSidebarWidth,
    setInspectorWidth
  };

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useAppStore() {
  const value = useContext(StoreContext);
  if (!value) {
    throw new Error("useAppStore must be used inside AppProvider");
  }
  return value;
}
