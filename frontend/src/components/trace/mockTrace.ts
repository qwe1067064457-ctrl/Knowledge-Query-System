import type { ExecutionEvent, IntentTrace, WorkflowTrace } from "@/lib/api";

export const MOCK_TRACE_INTENT: IntentTrace = {
  typed_evidence: [
    {
      signal: "main_intent",
      value: "qa_runner_v2_explain",
      source: "surface_trigger",
      score: 0.93,
      threshold: 0.58,
      margin: 0.35,
      calibration_quality: "good",
      prerequisites: [],
      missing_prerequisites: [],
      criticality: "route",
      rationale: "问题明确指向设计解释，且含有前后端联动上下文。"
    }
  ],
  quality_report: {
    accepted_evidence: [
      {
        signal: "main_intent",
        value: "qa_runner_v2_explain",
        source: "surface_trigger",
        score: 0.93,
        threshold: 0.58,
        margin: 0.35,
        calibration_quality: "good",
        prerequisites: [],
        missing_prerequisites: [],
        criticality: "route",
        rationale: "显式命中路由关键短语。"
      }
    ],
    downgraded_evidence: [
      {
        signal: "context_dependency",
        value: "medium",
        source: "small_model",
        score: 0.51,
        threshold: 0.5,
        margin: 0.01,
        calibration_quality: "weak",
        prerequisites: [],
        missing_prerequisites: [],
        criticality: "context_dependency",
        rationale: "依赖历史设计上下文，但当前消息本身也能形成初步判定。"
      }
    ],
    rejected_evidence: [
      {
        signal: "safety_block",
        value: false,
        source: "context_state",
        score: 0.12,
        threshold: 0.7,
        margin: -0.58,
        calibration_quality: "unknown",
        prerequisites: [],
        missing_prerequisites: [],
        criticality: "safety",
        rationale: "未触发本次安全边界。"
      }
    ],
    conflicts: [],
    ambiguities: ["是否需要工作流编排级展示"],
    missing_prerequisites: [],
    case_level: "requires_adjudication",
    case_reason: "主意图已清晰，但 workflow 粒度展示存在歧义，需要争议证据裁决。"
  },
  adjudication_result: {
    accepted_evidence: [
      {
        signal: "workflow_visibility",
        value: "show_workflow_trace",
        source: "llm_adjudication",
        score: 0.81,
        threshold: null,
        margin: null,
        calibration_quality: "unknown",
        prerequisites: [],
        missing_prerequisites: [],
        criticality: "task_shape",
        rationale: "用户明确要求展示 workflow trace 和 execution units。"
      }
    ],
    corrected_evidence: [],
    rejected_evidence: [],
    clarified_ambiguity_type: "workflow_depth",
    fallback_recommendation: "auto_resolve_with_warnings",
    reason: "裁决只补足展示粒度，不改变最终 resolver。"
  },
  resolved: {
    main_intent: "frontend_trace_visualization",
    task_shape: "ui_adaptation",
    context_dependency: "medium",
    resolved_intent: "show_agent_decision_chain"
  },
  control: {
    control_signal: "route:orchestrated_ui_update",
    route: "orchestrated",
    handling_mode: "normal"
  },
  decision_reason: "展示型前端改造，需要把证据、gate 与 workflow 路由可视化。"
};

export const MOCK_TRACE_WORKFLOW: WorkflowTrace = {
  route: "orchestrated",
  handling_mode: "normal",
  policy_flags: ["show_trace_cards", "preserve_streaming", "hide_missing_trace"],
  enabled_powers: ["render_markdown", "retrieval_trace", "tool_trace", "workflow_trace"],
  planning_mode: "explicit",
  fallback_used: false,
  fallback_reason: "",
  execution_units: [
    {
      unit_id: "unit-normalize-trace",
      goal: "补全 intent/workflow trace normalizer",
      capability: "frontend_state",
      depends_on: [],
      state: "completed",
      output_slot: "trace_state",
      retrieval_quality_status: "n/a",
      summary: "支持宽松解析，避免后端 contract 未齐时前端报错。"
    },
    {
      unit_id: "unit-render-cards",
      goal: "渲染 Decision Trace / Evidence Board / Workflow Trace",
      capability: "react_ui",
      depends_on: ["unit-normalize-trace"],
      state: "running",
      output_slot: "assistant_message",
      retrieval_quality_status: "good",
      summary: "沿用暖色 rounded panel 风格。"
    }
  ],
  payload_summary: [
    {
      label: "execution_units",
      value: "2 个可视化单元"
    },
    {
      label: "ui_rule",
      value: "没有 trace 时自动隐藏对应区域"
    }
  ],
  raw_payload: {
    route: "orchestrated",
    handling_mode: "normal"
  }
};

export const MOCK_TRACE_EVENTS: ExecutionEvent[] = [
  {
    type: "execution_update",
    label: "trace state ready",
    status: "completed",
    unit_id: "unit-normalize-trace",
    detail: "已完成 intent_analysis / workflow_plan / execution_update 的前端侧宽松归一化。",
    timestamp: null,
    payload: null
  },
  {
    type: "execution_update",
    label: "ui rendering",
    status: "running",
    unit_id: "unit-render-cards",
    detail: "正在渲染 assistant 顶部状态条、证据板与 workflow trace。",
    timestamp: null,
    payload: null
  }
];
