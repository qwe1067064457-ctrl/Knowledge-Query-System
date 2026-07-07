export type ToolCall = {
  tool: string;
  input: string;
  output: string;
};

export type Evidence = {
  source_path: string;
  source_type: string;
  locator: string;
  snippet: string;
  channel: "memory" | "knowledge" | "skill" | "vector" | "bm25" | "fused";
  score: number | null;
  parent_id: string | null;
};

export type RetrievalStep = {
  kind: "memory" | "knowledge";
  stage: string;
  title: string;
  message: string;
  results: Evidence[];
};

export type EvidenceSource =
  | "surface_trigger"
  | "small_model"
  | "context_state"
  | "retrieval_trace"
  | "human"
  | "llm_adjudication";

export type CaseLevelOutcome =
  | "auto_resolve"
  | "auto_resolve_with_warnings"
  | "blocked_by_missing_prerequisite"
  | "requires_adjudication"
  | "guard_required";

export type SignalCriticality =
  | "route"
  | "task_shape"
  | "context_dependency"
  | "safety"
  | "modifier"
  | "diagnostic";

export type CalibrationQuality = "good" | "weak" | "unknown";

export type TypedEvidence = {
  signal: string;
  value: unknown;
  source: EvidenceSource;
  score: number | null;
  threshold: number | null;
  margin: number | null;
  calibration_quality: CalibrationQuality;
  prerequisites: string[];
  missing_prerequisites: string[];
  criticality: SignalCriticality;
  rationale: string;
};

export type EvidenceQualityReport = {
  accepted_evidence: TypedEvidence[];
  downgraded_evidence: TypedEvidence[];
  rejected_evidence: TypedEvidence[];
  conflicts: string[];
  ambiguities: string[];
  missing_prerequisites: string[];
  case_level: CaseLevelOutcome;
  case_reason: string;
};

export type AdjudicationResult = {
  accepted_evidence: TypedEvidence[];
  corrected_evidence: TypedEvidence[];
  rejected_evidence: TypedEvidence[];
  clarified_ambiguity_type: string;
  fallback_recommendation: CaseLevelOutcome | null;
  reason: string;
};

export type IntentTrace = {
  typed_evidence: TypedEvidence[];
  quality_report: EvidenceQualityReport | null;
  adjudication_result: AdjudicationResult | null;
  resolved: Record<string, unknown> | null;
  control: Record<string, unknown> | null;
  decision_reason: string;
};

export type WorkflowExecutionUnit = {
  unit_id: string;
  goal: string;
  capability: string;
  depends_on: string[];
  state: string;
  output_slot: string;
  retrieval_quality_status: string;
  summary: string;
};

export type WorkflowSummaryItem = {
  label: string;
  value: string;
};

export type WorkflowTrace = {
  route: string;
  handling_mode: string;
  policy_flags: string[];
  enabled_powers: string[];
  planning_mode: string;
  fallback_used: boolean;
  fallback_reason: string;
  execution_units: WorkflowExecutionUnit[];
  payload_summary: WorkflowSummaryItem[];
  raw_payload: Record<string, unknown> | null;
};

export type ExecutionEvent = {
  type: string;
  label: string;
  status: string;
  unit_id: string;
  detail: string;
  timestamp: string | null;
  payload: Record<string, unknown> | null;
};

export type KnowledgeIndexStatus = {
  scope?: "all_groups" | "group";
  group_id?: string;
  group_ids?: string[];
  source_file_count?: number;
  ready: boolean;
  building: boolean;
  last_built_at: number | null;
  indexed_files: number;
  chunk_count: number;
  vector_ready: boolean;
  bm25_ready: boolean;
};

export type SessionSummary = {
  id: string;
  title: string;
  created_at: number;
  updated_at: number;
  message_count: number;
  active_group_id: string;
  allowed_group_ids: string[];
};

export type SessionHistory = {
  id: string;
  title: string;
  created_at: number;
  updated_at: number;
  compressed_context?: string;
  messages: Array<{
    role: "user" | "assistant";
    content: string;
    tool_calls?: ToolCall[];
    retrieval_steps?: RetrievalStep[];
    intent_trace?: unknown;
    workflow_trace?: unknown;
    execution_events?: unknown[];
  }>;
};

export type SessionAgentTraceEntry = {
  entry_id: string;
  session_id: string;
  intent_trace?: unknown;
  workflow_trace?: unknown;
  execution_events?: unknown[];
};

export type SessionAgentTraceRecord = {
  session_id: string;
  group_id: string;
  agent_id: string;
  count: number;
  traces: SessionAgentTraceEntry[];
};

export type UserRecord = {
  id: string;
  display_name: string;
  status: "active" | "disabled";
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
};

export type GroupRecord = {
  id: string;
  name: string;
  description: string;
  status: "active" | "archived";
  default_agent_id: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  knowledge: {
    root?: string;
    documents?: string;
    uploads?: string;
  };
  memory_policy: Record<string, unknown>;
  metadata: Record<string, unknown>;
};

export type RuntimeMemoryItem = {
  content: string;
  source: string;
  group_id: string;
  timestamp: string;
  score: number | null;
  scope: string;
  memory_type: string;
  user_id: string;
  title: string;
  subject: string;
  tags: string[];
  source_session_id: string | null;
  anchor_spans: string[];
  confidence: number | null;
  metadata: Record<string, unknown>;
};

export type RuntimeMemoryCore = {
  user_id: string;
  group_id: string;
  storage: {
    user_global_core: string;
    user_group_core: string;
    daily_log_dir: string;
    domain_case_file: string;
  };
  counts: {
    user_global: number;
    user_group: number;
    total: number;
  };
  items: RuntimeMemoryItem[];
};

export type RuntimeMemoryOverview = {
  user_id: string;
  group_id: string;
  storage: {
    user_global_core: string;
    user_group_core: string;
    daily_log_dir: string;
    domain_case_file: string;
  };
  counts: {
    core_total: number;
    user_global_core: number;
    user_group_core: number;
    daily_log_files: number;
    daily_log_entries: number;
    domain_case_entries: number;
  };
  exists: {
    user_global_core: boolean;
    user_group_core: boolean;
    daily_log_dir: boolean;
    domain_case_file: boolean;
  };
};

export type MembershipRecord = {
  group_id: string;
  user_id: string;
  role: "owner" | "admin" | "member" | "viewer";
  status: "active" | "removed";
  created_at: string;
  updated_at: string;
};

export type StreamHandlers = {
  onEvent: (event: string, data: Record<string, unknown>) => void;
};

const DEFAULT_API_PORT = "8004";

const EMPTY_INTENT_TRACE: IntentTrace = {
  typed_evidence: [],
  quality_report: null,
  adjudication_result: null,
  resolved: null,
  control: null,
  decision_reason: ""
};

const EMPTY_WORKFLOW_TRACE: WorkflowTrace = {
  route: "",
  handling_mode: "",
  policy_flags: [],
  enabled_powers: [],
  planning_mode: "",
  fallback_used: false,
  fallback_reason: "",
  execution_units: [],
  payload_summary: [],
  raw_payload: null
};

export const EVIDENCE_SOURCE_LABELS: Record<EvidenceSource, string> = {
  surface_trigger: "哨兵",
  small_model: "证人",
  context_state: "上下文事实",
  retrieval_trace: "检索轨迹",
  human: "人工输入",
  llm_adjudication: "裁判"
};

export const CASE_LEVEL_LABELS: Record<CaseLevelOutcome, string> = {
  auto_resolve: "可自动收敛",
  auto_resolve_with_warnings: "可自动收敛（带提醒）",
  blocked_by_missing_prerequisite: "缺少必要上下文，需要澄清",
  requires_adjudication: "需要裁决",
  guard_required: "安全/能力边界"
};

function normalizeApiBase(base: string) {
  return base.endsWith("/") ? base.slice(0, -1) : base;
}

function getApiBase() {
  const configuredBase = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (configuredBase) {
    return normalizeApiBase(configuredBase);
  }

  if (typeof window === "undefined") {
    return `http://127.0.0.1:${DEFAULT_API_PORT}/api`;
  }

  return `${window.location.protocol}//${window.location.hostname}:${DEFAULT_API_PORT}/api`;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function asString(value: unknown, fallback = "") {
  return typeof value === "string" ? value : fallback;
}

function asStringArray(value: unknown) {
  return Array.isArray(value)
    ? value
        .map((entry) => (typeof entry === "string" ? entry : String(entry ?? "")))
        .filter(Boolean)
    : [];
}

function asNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  return null;
}

function pickRecord(value: Record<string, unknown> | null, keys: string[]) {
  for (const key of keys) {
    const candidate = asRecord(value?.[key]);
    if (candidate) {
      return candidate;
    }
  }

  return null;
}

function pickArray(value: Record<string, unknown> | null, keys: string[]) {
  for (const key of keys) {
    const candidate = value?.[key];
    if (Array.isArray(candidate)) {
      return candidate;
    }
  }

  return [];
}

export function normalizeEvidence(value: unknown): Evidence | null {
  const item = asRecord(value);
  if (!item) {
    return null;
  }

  return {
    source_path: asString(item.source_path),
    source_type: asString(item.source_type),
    locator: asString(item.locator),
    snippet: asString(item.snippet),
    channel: (asString(item.channel, "knowledge") as Evidence["channel"]),
    score: asNumber(item.score),
    parent_id: item.parent_id ? String(item.parent_id) : null
  };
}

export function normalizeRetrievalStep(value: unknown): RetrievalStep | null {
  const item = asRecord(value);
  if (!item) {
    return null;
  }

  const results = pickArray(item, ["results"])
    .map((entry) => normalizeEvidence(entry))
    .filter((entry): entry is Evidence => entry !== null);

  return {
    kind: item.kind === "memory" ? "memory" : "knowledge",
    stage: asString(item.stage, "unknown"),
    title: asString(item.title, "检索结果"),
    message: asString(item.message),
    results
  };
}

export function normalizeToolCall(value: unknown): ToolCall | null {
  const item = asRecord(value);
  if (!item) {
    return null;
  }

  const functionRecord = asRecord(item.function);
  const toolName =
    asString(item.tool) ||
    asString(item.name) ||
    asString(functionRecord?.name) ||
    "tool";
  const rawInput = item.input ?? functionRecord?.arguments;
  const rawOutput = item.output;

  return {
    tool: toolName,
    input:
      typeof rawInput === "string"
        ? rawInput
        : rawInput === undefined || rawInput === null
          ? ""
          : JSON.stringify(rawInput),
    output:
      typeof rawOutput === "string"
        ? rawOutput
        : rawOutput === undefined || rawOutput === null
          ? ""
          : JSON.stringify(rawOutput)
  };
}

function normalizeTypedEvidence(value: unknown): TypedEvidence | null {
  const item = asRecord(value);
  if (!item) {
    return null;
  }

  const source = item.source;
  const criticality = item.criticality;
  const calibrationQuality = item.calibration_quality;

  return {
    signal: asString(item.signal),
    value: item.value ?? null,
    source:
      source === "surface_trigger" ||
      source === "small_model" ||
      source === "context_state" ||
      source === "retrieval_trace" ||
      source === "human" ||
      source === "llm_adjudication"
        ? source
        : "small_model",
    score: asNumber(item.score),
    threshold: asNumber(item.threshold),
    margin: asNumber(item.margin),
    calibration_quality:
      calibrationQuality === "good" || calibrationQuality === "weak" ? calibrationQuality : "unknown",
    prerequisites: asStringArray(item.prerequisites),
    missing_prerequisites: asStringArray(item.missing_prerequisites),
    criticality:
      criticality === "route" ||
      criticality === "task_shape" ||
      criticality === "context_dependency" ||
      criticality === "safety" ||
      criticality === "modifier" ||
      criticality === "diagnostic"
        ? criticality
        : "diagnostic",
    rationale: asString(item.rationale)
  };
}

function normalizeQualityReport(value: unknown): EvidenceQualityReport | null {
  const item = asRecord(value);
  if (!item) {
    return null;
  }

  const caseLevel = item.case_level;

  return {
    accepted_evidence: pickArray(item, ["accepted_evidence"])
      .map((entry) => normalizeTypedEvidence(entry))
      .filter((entry): entry is TypedEvidence => entry !== null),
    downgraded_evidence: pickArray(item, ["downgraded_evidence"])
      .map((entry) => normalizeTypedEvidence(entry))
      .filter((entry): entry is TypedEvidence => entry !== null),
    rejected_evidence: pickArray(item, ["rejected_evidence"])
      .map((entry) => normalizeTypedEvidence(entry))
      .filter((entry): entry is TypedEvidence => entry !== null),
    conflicts: asStringArray(item.conflicts),
    ambiguities: asStringArray(item.ambiguities),
    missing_prerequisites: asStringArray(item.missing_prerequisites),
    case_level:
      caseLevel === "auto_resolve" ||
      caseLevel === "auto_resolve_with_warnings" ||
      caseLevel === "blocked_by_missing_prerequisite" ||
      caseLevel === "requires_adjudication" ||
      caseLevel === "guard_required"
        ? caseLevel
        : "auto_resolve",
    case_reason: asString(item.case_reason)
  };
}

function normalizeAdjudicationResult(value: unknown): AdjudicationResult | null {
  const item = asRecord(value);
  if (!item) {
    return null;
  }

  const fallback = item.fallback_recommendation;

  return {
    accepted_evidence: pickArray(item, ["accepted_evidence"])
      .map((entry) => normalizeTypedEvidence(entry))
      .filter((entry): entry is TypedEvidence => entry !== null),
    corrected_evidence: pickArray(item, ["corrected_evidence"])
      .map((entry) => normalizeTypedEvidence(entry))
      .filter((entry): entry is TypedEvidence => entry !== null),
    rejected_evidence: pickArray(item, ["rejected_evidence"])
      .map((entry) => normalizeTypedEvidence(entry))
      .filter((entry): entry is TypedEvidence => entry !== null),
    clarified_ambiguity_type: asString(item.clarified_ambiguity_type),
    fallback_recommendation:
      fallback === "auto_resolve" ||
      fallback === "auto_resolve_with_warnings" ||
      fallback === "blocked_by_missing_prerequisite" ||
      fallback === "requires_adjudication" ||
      fallback === "guard_required"
        ? fallback
        : null,
    reason: asString(item.reason)
  };
}

export function normalizeIntentTrace(value: unknown): IntentTrace | null {
  const root = asRecord(value);
  if (!root) {
    return null;
  }

  const evidence = pickRecord(root, ["evidence", "intent_trace"]) ?? root;
  const qualityReport =
    normalizeQualityReport(evidence.quality_report) ??
    normalizeQualityReport(root.quality_report);
  const adjudicationResult =
    normalizeAdjudicationResult(evidence.adjudication_result) ??
    normalizeAdjudicationResult(root.adjudication_result);
  const typedEvidence = pickArray(evidence, ["typed_evidence", "accepted_evidence", "evidence"])
    .map((entry) => normalizeTypedEvidence(entry))
    .filter((entry): entry is TypedEvidence => entry !== null);
  const resolved = pickRecord(root, ["resolved"]) ?? pickRecord(evidence, ["resolved"]);
  const control = pickRecord(root, ["control"]) ?? pickRecord(evidence, ["control"]);
  const decisionReason =
    asString(root.decision_reason) ||
    asString(root.reason) ||
    asString(resolved?.reason) ||
    asString(control?.reason) ||
    asString(qualityReport?.case_reason);

  const hasUsefulData =
    typedEvidence.length > 0 || Boolean(qualityReport || adjudicationResult || resolved || control || decisionReason);

  if (!hasUsefulData) {
    return null;
  }

  return {
    typed_evidence: typedEvidence,
    quality_report: qualityReport,
    adjudication_result: adjudicationResult,
    resolved,
    control,
    decision_reason: decisionReason
  };
}

function normalizeWorkflowExecutionUnit(value: unknown): WorkflowExecutionUnit | null {
  const item = asRecord(value);
  if (!item) {
    return null;
  }

  return {
    unit_id: asString(item.unit_id || item.id),
    goal: asString(item.goal),
    capability: asString(item.capability || item.tool || item.kind),
    depends_on: asStringArray(item.depends_on),
    state: asString(item.state || item.status),
    output_slot: asString(item.output_slot),
    retrieval_quality_status: asString(item.retrieval_quality_status),
    summary: asString(item.summary || item.message)
  };
}

function summarizePayload(payload: Record<string, unknown>) {
  const items: WorkflowSummaryItem[] = [];

  for (const [key, rawValue] of Object.entries(payload)) {
    if (
      key === "execution_units" ||
      key === "units" ||
      key === "payload_summary" ||
      rawValue === null ||
      rawValue === undefined
    ) {
      continue;
    }

    if (Array.isArray(rawValue)) {
      if (!rawValue.length) {
        continue;
      }
      items.push({
        label: key,
        value: rawValue.map((entry) => (typeof entry === "string" ? entry : JSON.stringify(entry))).join(" / ")
      });
      continue;
    }

    if (typeof rawValue === "object") {
      items.push({
        label: key,
        value: JSON.stringify(rawValue)
      });
      continue;
    }

    items.push({
      label: key,
      value: String(rawValue)
    });
  }

  return items;
}

export function normalizeWorkflowTrace(value: unknown): WorkflowTrace | null {
  const root = asRecord(value);
  if (!root) {
    return null;
  }

  const plan = pickRecord(root, ["plan", "workflow_trace"]) ?? root;
  const payload = pickRecord(plan, ["payload", "workflow_payload", "execution_payload"]) ?? plan;
  const executionUnits = pickArray(plan, ["execution_units", "units"])
    .concat(pickArray(payload, ["execution_units", "units"]))
    .map((entry) => normalizeWorkflowExecutionUnit(entry))
    .filter((entry): entry is WorkflowExecutionUnit => entry !== null);
  const payloadSummary = pickArray(plan, ["payload_summary"])
    .map((entry) => {
      const item = asRecord(entry);
      if (!item) {
        return null;
      }
      return {
        label: asString(item.label),
        value: asString(item.value)
      } satisfies WorkflowSummaryItem;
    })
    .filter((entry): entry is WorkflowSummaryItem => entry !== null);
  const rawPayload = Object.keys(payload).length ? payload : null;

  const trace: WorkflowTrace = {
    route: asString(plan.route || payload.route),
    handling_mode: asString(plan.handling_mode || payload.handling_mode),
    policy_flags: asStringArray(plan.policy_flags || payload.policy_flags),
    enabled_powers: asStringArray(plan.enabled_powers || payload.enabled_powers),
    planning_mode: asString(plan.planning_mode || payload.planning_mode),
    fallback_used: Boolean(plan.fallback_used ?? payload.fallback_used),
    fallback_reason: asString(plan.fallback_reason || payload.fallback_reason),
    execution_units: executionUnits,
    payload_summary: payloadSummary.length ? payloadSummary : rawPayload ? summarizePayload(rawPayload) : [],
    raw_payload: rawPayload
  };

  const hasUsefulData =
    Boolean(trace.route || trace.handling_mode || trace.planning_mode || trace.fallback_reason) ||
    trace.policy_flags.length > 0 ||
    trace.enabled_powers.length > 0 ||
    trace.execution_units.length > 0 ||
    trace.payload_summary.length > 0;

  return hasUsefulData ? trace : null;
}

export function normalizeExecutionEvent(value: unknown): ExecutionEvent | null {
  const root = asRecord(value);
  if (!root) {
    return null;
  }

  const payload = pickRecord(root, ["payload"]) ?? root;

  return {
    type: asString(root.type || payload.type, "execution_update"),
    label: asString(root.label || payload.label || payload.event || payload.stage, "执行更新"),
    status: asString(root.status || payload.status),
    unit_id: asString(root.unit_id || payload.unit_id),
    detail: asString(root.detail || payload.detail || payload.message),
    timestamp: asString(root.timestamp || payload.timestamp) || null,
    payload: Object.keys(payload).length ? payload : null
  };
}

export function mergeIntentTrace(
  current: IntentTrace | undefined,
  incoming: IntentTrace | null
): IntentTrace | undefined {
  if (!incoming) {
    return current;
  }

  const base = current ?? EMPTY_INTENT_TRACE;

  return {
    typed_evidence: incoming.typed_evidence.length ? incoming.typed_evidence : base.typed_evidence,
    quality_report: incoming.quality_report ?? base.quality_report,
    adjudication_result: incoming.adjudication_result ?? base.adjudication_result,
    resolved: incoming.resolved ?? base.resolved,
    control: incoming.control ?? base.control,
    decision_reason: incoming.decision_reason || base.decision_reason
  };
}

export function mergeWorkflowTrace(
  current: WorkflowTrace | undefined,
  incoming: WorkflowTrace | null
): WorkflowTrace | undefined {
  if (!incoming) {
    return current;
  }

  const base = current ?? EMPTY_WORKFLOW_TRACE;

  return {
    route: incoming.route || base.route,
    handling_mode: incoming.handling_mode || base.handling_mode,
    policy_flags: incoming.policy_flags.length ? incoming.policy_flags : base.policy_flags,
    enabled_powers: incoming.enabled_powers.length ? incoming.enabled_powers : base.enabled_powers,
    planning_mode: incoming.planning_mode || base.planning_mode,
    fallback_used: incoming.fallback_used || base.fallback_used,
    fallback_reason: incoming.fallback_reason || base.fallback_reason,
    execution_units: incoming.execution_units.length ? incoming.execution_units : base.execution_units,
    payload_summary: incoming.payload_summary.length ? incoming.payload_summary : base.payload_summary,
    raw_payload: incoming.raw_payload ?? base.raw_payload
  };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getApiBase()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}

export async function listSessions() {
  return request<SessionSummary[]>("/sessions");
}

export async function createSession(
  title = "新会话",
  options?: {
    active_group_id?: string;
    allowed_group_ids?: string[];
  }
) {
  return request<SessionSummary>("/sessions", {
    method: "POST",
    body: JSON.stringify({
      title,
      active_group_id: options?.active_group_id ?? "general",
      allowed_group_ids: options?.allowed_group_ids ?? undefined
    })
  });
}

export async function renameSession(sessionId: string, title: string) {
  return request<SessionSummary>(`/sessions/${sessionId}`, {
    method: "PUT",
    body: JSON.stringify({ title })
  });
}

export async function deleteSession(sessionId: string) {
  return request<{ ok: boolean }>(`/sessions/${sessionId}`, {
    method: "DELETE"
  });
}

export async function getSessionHistory(sessionId: string) {
  return request<SessionHistory>(`/sessions/${sessionId}/history`);
}

export async function getSessionAgentTraces(sessionId: string) {
  return request<SessionAgentTraceRecord>(`/sessions/${sessionId}/agent-traces`);
}

export async function getSessionTokens(sessionId: string) {
  return request<{
    system_tokens: number;
    message_tokens: number;
    total_tokens: number;
  }>(`/tokens/session/${sessionId}`);
}

export async function listSkills() {
  return request<Array<{ name: string; description: string; path: string }>>("/skills");
}

export async function loadFile(path: string) {
  return request<{ path: string; content: string }>(
    `/files?path=${encodeURIComponent(path)}`
  );
}

export async function saveFile(path: string, content: string) {
  return request<{ ok: boolean; path: string }>("/files", {
    method: "POST",
    body: JSON.stringify({ path, content })
  });
}

export async function getRagMode() {
  return request<{ enabled: boolean }>("/config/rag-mode");
}

export async function setRagMode(enabled: boolean) {
  return request<{ enabled: boolean }>("/config/rag-mode", {
    method: "PUT",
    body: JSON.stringify({ enabled })
  });
}

export async function compressSession(sessionId: string) {
  return request<{ archived_count: number; remaining_count: number }>(
    `/sessions/${sessionId}/compress`,
    { method: "POST" }
  );
}

export async function getKnowledgeIndexStatus(groupId?: string) {
  const suffix = groupId ? `?group_id=${encodeURIComponent(groupId)}` : "";
  return request<KnowledgeIndexStatus>(`/knowledge/index/status${suffix}`);
}

export async function rebuildKnowledgeIndex(groupId?: string) {
  const suffix = groupId ? `?group_id=${encodeURIComponent(groupId)}` : "";
  return request<{ accepted: boolean; group_id?: string | null; queued?: boolean }>(
    `/knowledge/index/rebuild${suffix}`,
    {
    method: "POST"
    }
  );
}

export async function getRuntimeMemoryCore(params?: {
  user_id?: string;
  group_id?: string;
}) {
  const query = new URLSearchParams();
  if (params?.user_id) {
    query.set("user_id", params.user_id);
  }
  if (params?.group_id) {
    query.set("group_id", params.group_id);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<RuntimeMemoryCore>(`/runtime/memory/core${suffix}`);
}

export async function getRuntimeMemoryOverview(params?: {
  user_id?: string;
  group_id?: string;
}) {
  const query = new URLSearchParams();
  if (params?.user_id) {
    query.set("user_id", params.user_id);
  }
  if (params?.group_id) {
    query.set("group_id", params.group_id);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<RuntimeMemoryOverview>(`/runtime/memory/overview${suffix}`);
}

export async function listUsers(includeDisabled = false) {
  const suffix = includeDisabled ? "?include_disabled=true" : "";
  return request<UserRecord[]>(`/users${suffix}`);
}

export async function createUser(payload: {
  id: string;
  display_name?: string;
  metadata?: Record<string, unknown>;
}) {
  return request<UserRecord>("/users", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function deleteUser(userId: string) {
  return request<UserRecord>(`/users/${encodeURIComponent(userId)}`, {
    method: "DELETE"
  });
}

export async function listGroups(includeArchived = false) {
  const suffix = includeArchived ? "?include_archived=true" : "";
  return request<GroupRecord[]>(`/groups${suffix}`);
}

export async function createGroup(payload: {
  id: string;
  name: string;
  created_by: string;
  description?: string;
  default_agent_id?: string;
  memory_policy?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}) {
  return request<GroupRecord>("/groups", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function archiveGroup(groupId: string) {
  return request<GroupRecord>(`/groups/${encodeURIComponent(groupId)}/archive`, {
    method: "POST"
  });
}

export async function restoreGroup(groupId: string) {
  return request<GroupRecord>(`/groups/${encodeURIComponent(groupId)}/restore`, {
    method: "POST"
  });
}

export async function listGroupMembers(groupId: string, includeRemoved = false) {
  const suffix = includeRemoved ? "?include_removed=true" : "";
  return request<MembershipRecord[]>(
    `/groups/${encodeURIComponent(groupId)}/members${suffix}`
  );
}

export async function addGroupMember(
  groupId: string,
  payload: {
    user_id: string;
    role: MembershipRecord["role"];
  }
) {
  return request<MembershipRecord>(`/groups/${encodeURIComponent(groupId)}/members`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function removeGroupMember(groupId: string, userId: string) {
  return request<MembershipRecord>(
    `/groups/${encodeURIComponent(groupId)}/members/${encodeURIComponent(userId)}`,
    { method: "DELETE" }
  );
}

export async function streamChat(
  payload: {
    message: string;
    session_id: string;
  },
  handlers: StreamHandlers
) {
  const response = await fetch(`${getApiBase()}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      ...payload,
      stream: true
    })
  });

  if (!response.ok || !response.body) {
    throw new Error(`Chat request failed: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const flushBlock = (block: string) => {
    const lines = block.split("\n");
    let event = "message";
    const dataLines: string[] = [];

    for (const line of lines) {
      if (line.startsWith("event:")) {
        event = line.slice(6).trim();
      }
      if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trim());
      }
    }

    if (!dataLines.length) {
      return;
    }

    const data = JSON.parse(dataLines.join("\n")) as Record<string, unknown>;
    handlers.onEvent(event, data);
  };

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });

    let boundary = buffer.indexOf("\n\n");
    while (boundary >= 0) {
      flushBlock(buffer.slice(0, boundary));
      buffer = buffer.slice(boundary + 2);
      boundary = buffer.indexOf("\n\n");
    }

    if (done) {
      if (buffer.trim()) {
        flushBlock(buffer);
      }
      break;
    }
  }
}
