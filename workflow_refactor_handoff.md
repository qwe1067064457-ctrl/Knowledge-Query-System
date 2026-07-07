# Handoff: Workflow Refactor for Runtime Skills and Registry Removal

## Summary

本次重构目标不是继续往现有 `workflow` 里加 worker，而是做一次职责收缩：

```text
1. 拔除 registry entry runtime 依赖。
2. QA route 收缩成 retrieval-only 轻路径。
3. Context Binding / Challenge / Decomposition 不再作为硬编码工具散落在 route 里。
4. ReAct Agent 调用的能力改成 Runtime Skill，并尽量采用 Codex Skill 风格的目录规范。
5. 每个 typed execution unit 通过 runtime skill 绑定工具白名单、输出 schema 和失败兜底。
```

核心原则：

```text
Tool 是确定性动作。
Runtime Skill 是工作手册。
Judge / Planner 是语义判断和结构生成。
Policy 决定是否触发这些流程。
QA route 不再承载 context binding / challenge。
```

## Current Problems

### 1. Registry Entry 被误用为短程记忆

当前 registry entry 原本想作为短程记忆候选，但它主要来自规则或 execution payload projection，噪音较多。它被读取后会进入：

```text
CandidateCollection
ContextBinding
ChallengeTargetSelection
EvidenceCandidate
```

问题：

```text
1. 规则抽取的 entry 精度不稳定。
2. 它不是用户显式确认的事实。
3. 它不应等同于 Session Working Memory。
4. 它会污染 context binding 和 challenge target selection。
5. 它让短程状态变成规则残渣。
```

目标：

```text
RegistryEntry 不再作为 runtime 的默认候选来源。
RegistryEntry 不再作为短程记忆。
旧 registry 文件可以保留，但 runtime 不再依赖。
```

### 2. QA Route 过胖

当前 QA route 里硬编码了：

```text
ContextBindingPower
ChallengePower
BindingWorker
ReviewWorker
RetrievalPower
RetrievalGate
MemoryAnchor hydration
```

这导致 QA route 同时承担：

```text
普通问答
上下文绑定
质疑复核
检索
回答约束
```

目标：

```text
QA route 只保留轻量 retrieval + payload finalize。
Context binding 由 ContextBinding runtime skill 负责。
Challenge 由 Challenge runtime skill 负责。
Decomposition / Planning 由 orchestrated route 负责。
```

### 3. 有些工具不应该存在为 Tool

不是所有能力都适合做工具。以下能力不应被建模成普通 tool：

```text
TargetResolution
RelevantSetSelection
ChallengeTargetSelection
EvidenceCheck
ChallengeReEvaluate
QuestionBoundaryDetector
DependencyResolver
Planning
Decomposition
Synthesis
```

这些能力包含语义判断、上下文消解、证据裁决、边界判断，不是稳定函数。

目标：

```text
确定性动作 -> Worker / Tool / scripts
语义判断 -> Judge / Atomic Capability
流程组织 -> Runtime Skill
结构生成 -> Planner
触发条件 -> Policy
```

## Target Architecture

### Main Flow

```text
IntentAnalysis
  -> WorkflowPolicy
     -> route / handling_mode / enabled runtime skills
  -> RouteRunner
     -> qa | chat | orchestrated | reject
  -> RuntimeSkill if required
     -> context-binding | challenge-review | decomposition | synthesis
  -> ExecutionPayload
  -> Final Answer Model
```

### QA Route v2

```text
QaRouteRunner
  -> build payload
  -> optional memory anchor hydration
  -> RetrievalGate
  -> RetrievalPower
  -> RetrievalQuality
  -> EvidenceBundle
  -> finalize ExecutionPayload
```

QA route should not call:

```text
ContextBindingPower
ChallengePower
BindingWorker
ReviewWorker
registry binding candidates
registry evidence candidates
```

If context binding is needed:

```text
WorkflowPolicy -> ContextBindingRuntimeSkill -> rewritten query / clarify
```

If challenge is needed:

```text
WorkflowPolicy -> ChallengeRuntimeSkill -> answer constraints / clarify / insufficient evidence
```

## Runtime Skill Convention

Runtime Skill should follow Codex Skill style, but with runtime metadata.

Recommended structure:

```text
backend/workflow/runtime_skills/
  context-binding/
    SKILL.md
    runtime.yaml
    references/
      schema.md
      examples.md
      failure-modes.md
    scripts/
      candidate_collection.py
      query_rewrite.py

  challenge-review/
    SKILL.md
    runtime.yaml
    references/
      schema.md
      evidence-rubric.md
      challenge-types.md
      examples.md
    scripts/
      answer_constraint.py

  decomposition/
    SKILL.md
    runtime.yaml
    references/
      schema.md
      examples.md
      anti-patterns.md
    scripts/
      query_unit_builder.py

  synthesis/
    SKILL.md
    runtime.yaml
    references/
      schema.md
      answer-assembly-rules.md
    scripts/
      evidence_anchor.py
      caution_assembly.py
```

### SKILL.md Role

`SKILL.md` is the runtime work manual:

```text
1. What the skill does.
2. When to use it.
3. When not to use it.
4. Procedure.
5. Output contract.
6. Failure fallback.
7. Which references to load when needed.
```

### runtime.yaml Role

`runtime.yaml` defines runtime constraints:

```yaml
name: context-binding
capability: context_binding
unit_types:
  - qa_like
  - verify
allowed_tools:
  - candidate_collection
  - query_rewrite
output_schema: ContextBindingResult
max_steps: 4
allow_llm: true
allow_external_io: false
fallback:
  ambiguous: needs_clarification
```

### scripts/ Role

Only deterministic actions go into `scripts/`.

Good candidates:

```text
candidate_collection
query_rewrite
query_unit_builder
answer_constraint
evidence_anchor
caution_assembly
```

Do not put these directly into scripts as if they were deterministic tools:

```text
target_resolution
challenge_re_evaluate
question_boundary_detector
dependency_resolver
evidence_check
```

Those should be handled as judge/procedure steps with schemas and validation.

## Runtime Skill Breakdown

### Context Binding Runtime Skill

Procedure:

```text
CandidateCollection
  -> RelevantSetSelection
  -> TargetResolution
  -> QueryRewrite
```

Classification:

```text
CandidateCollection: deterministic worker
RelevantSetSelection: atomic capability / semantic filter
TargetResolution: judge
QueryRewrite: deterministic worker
```

Output:

```text
ContextBindingSkillResult:
  status: bound | ambiguous | no_target | needs_clarification
  bound_targets
  relevant_set
  rewritten_query
  confidence
  reason
```

### Challenge Runtime Skill

Procedure:

```text
ChallengeTargetSelection
  -> EvidenceCheck
  -> FollowupRetrievalPlanner
  -> ChallengeReEvaluate
  -> AnswerConstraint
```

Classification:

```text
ChallengeTargetSelection: atomic capability / semantic target selection
EvidenceCheck: judge
FollowupRetrievalPlanner: planner
ChallengeReEvaluate: judge
AnswerConstraint: deterministic worker
```

Output:

```text
ChallengeSkillResult:
  status: maintained | corrected | insufficient_evidence | needs_clarification
  targets
  findings
  answer_constraints
  evidence_refs
  confidence
  reason
```

### Decomposition Runtime Skill

Procedure:

```text
QuestionBoundaryDetector
  -> DependencyResolver
  -> SubQuestionRewriter
  -> QueryUnitBuilder
```

Classification:

```text
QuestionBoundaryDetector: planner/judge
DependencyResolver: planner
SubQuestionRewriter: deterministic or LLM-assisted rewrite step
QueryUnitBuilder: deterministic worker
```

Output:

```text
DecompositionSkillResult:
  status: decomposed | single_unit | uncertain | needs_clarification
  query_units
  dependency_edges
  confidence
  reason
```

Fallback:

```text
If boundaries are unclear, prefer single_unit.
Do not over-split because the query is long.
Do not invent missing sub-goals.
```

### Synthesis Runtime Skill

Procedure:

```text
FindingProjection
  -> EvidenceAnchor
  -> CautionAssembly
```

Classification:

```text
FindingProjection: structured projector
EvidenceAnchor: deterministic worker
CautionAssembly: deterministic worker
```

Output:

```text
SynthesisSkillResult:
  primary_findings
  supporting_findings
  status_findings
  evidence_anchors
  cautions
```

## Files to Inspect First

Start with:

```text
backend/workflow/routes/qa_runner.py
backend/workflow/routes/chat_runner.py
backend/workflow/orchestrated/route/orchestrated_runner.py
backend/workflow/policy.py
backend/workflow/runners/base.py
backend/workflow/adapters/workflow_registry_projection.py
backend/workflow/adapters/workflow_registry_consumer.py
backend/context/registry/
backend/context/assembly/context_manager.py
backend/graph/agent.py
backend/workflow/orchestrated/execution_layer/workers/
backend/workflow/orchestrated/execution_layer/executors/
```

## Implementation Plan

### Phase 1: Disable Registry Runtime Dependency

Do:

```text
1. Stop loading recent registry entries into request.context.
2. Stop reading registry entries in BaseRouteRunner candidate helpers.
3. Stop projecting ExecutionPayload into ContextRegistryEntry by default.
4. Mark workflow registry adapters legacy or unused.
5. Keep old registry files; do not delete historical data.
```

Expected behavior:

```text
No route should depend on request.context["registry_entries"].
Context binding should use working memory / recent messages / memory anchors / structured unit outputs instead.
```

### Phase 2: Slim QA Route

Do:

```text
1. Remove ContextBindingPower from QaRouteRunner.
2. Remove ChallengePower from QaRouteRunner.
3. Remove BindingWorker / ReviewWorker direct route ownership where possible.
4. Keep RetrievalGate / RetrievalPower / RetrievalQuality.
5. Keep memory anchor hydration only if it supports retrieval context, not registry candidate generation.
```

Expected QA responsibilities:

```text
single-turn answer flow
retrieval
evidence bundle
answer constraints derived from retrieval state
payload finalize
```

### Phase 3: Add Runtime Skill Loader

Add:

```text
backend/workflow/runtime_skills/
  loader.py
  contracts.py
  registry.py
```

Core concepts:

```text
RuntimeSkillSpec
RuntimeSkillResult
RuntimeSkillLoader
```

Skill loader should:

```text
1. Load SKILL.md.
2. Load runtime.yaml.
3. Resolve allowed deterministic tools.
4. Provide prompt context to ReAct agent only for the selected skill.
5. Validate structured output.
```

### Phase 4: Move Context Binding to Runtime Skill

Do:

```text
1. Create context-binding runtime skill folder.
2. Move deterministic candidate_collection and query_rewrite into scripts or wrapped workers.
3. Treat relevant_set_selection and target_resolution as procedure/judge steps.
4. Return structured ContextBindingSkillResult.
5. Route-level code consumes result, not raw workers.
```

### Phase 5: Move Challenge to Runtime Skill

Do:

```text
1. Create challenge-review runtime skill folder.
2. Keep answer_constraint deterministic.
3. Treat evidence_check and challenge_re_evaluate as judge steps.
4. Return structured ChallengeSkillResult.
5. Remove direct challenge hardcoding from QA route.
```

### Phase 6: Move Decomposition to Runtime Skill

Do:

```text
1. Replace naive split_parallel_queries with DecompositionRuntimeSkill.
2. Keep QueryUnitBuilder deterministic.
3. Add single_unit fallback.
4. Do not over-split ambiguous user queries.
```

### Phase 7: Restrict WorkerRegistry

Do:

```text
1. WorkerRegistry should expose only deterministic tools to ReAct.
2. Semantic judges should not be wrapped as generic StructuredTool unless explicitly scoped by a runtime skill.
3. Each typed unit should receive only its skill-specific allowed tools.
```

## Tests Required

Use pytest. Add black-box tests.

Suggested files:

```text
backend_test/workflow/test_registry_removal.py
backend_test/workflow/test_qa_route_slim.py
backend_test/workflow/test_runtime_skill_loader.py
backend_test/workflow/test_context_binding_runtime_skill.py
backend_test/workflow/test_challenge_runtime_skill.py
backend_test/workflow/test_decomposition_runtime_skill.py
```

Minimum cases:

```text
test_registry_removal.py
  positive: agent request context no longer includes registry_entries
  negative: old registry files do not affect binding candidates

test_qa_route_slim.py
  positive: qa route can still retrieve and return EvidenceBundle
  negative: qa route does not call ContextBindingPower or ChallengePower

test_runtime_skill_loader.py
  positive: loads SKILL.md + runtime.yaml + allowed tools
  negative: rejects missing output_schema or unknown tool

test_context_binding_runtime_skill.py
  positive: clear target binds and rewrites query
  negative: ambiguous target returns needs_clarification

test_challenge_runtime_skill.py
  positive: evidence-supported challenge produces answer constraints
  negative: target not found returns needs_clarification

test_decomposition_runtime_skill.py
  positive: explicit multi-question query becomes QueryUnit[]
  negative: ambiguous long query stays single_unit
```

Do not pollute real storage. Use `tmp_path`.

## Non-Goals

Do not do these in this refactor:

```text
1. Do not delete historical registry JSON files.
2. Do not implement full pause/resume workflow runtime.
3. Do not add human approval yet.
4. Do not rewrite final answer model prompt unless needed for contract compatibility.
5. Do not expose all runtime skill internals as global ReAct tools.
6. Do not rename Codex Skill concepts inside `.codex/skills`.
```

## Acceptance Criteria

The refactor is acceptable when:

```text
1. Runtime no longer depends on ContextRegistryEntry for binding/challenge candidates.
2. QA route no longer owns context binding or challenge logic.
3. Context Binding / Challenge / Decomposition are represented as runtime skills/procedures with structured outputs.
4. Deterministic actions remain tools/workers.
5. Semantic judgment steps are not exposed as generic tools.
6. Typed units have tool white-lists and output schemas.
7. Existing qa retrieval still works.
8. Tests cover positive and negative paths.
```

## Interview Framing

Use this explanation:

```text
I later found that registry entries should not be treated as short-term memory because many of them were rule-extracted and noisy. So I removed them from runtime decision paths and kept short-term state in Session Working Memory, recent messages, memory anchors, and structured UnitResult.

I also stopped treating every reusable ability as a tool. Deterministic actions remain tools, but semantic procedures like target resolution, challenge re-evaluation, and decomposition are runtime skills with structured input/output, validation, and fallback. QA route was slimmed down to retrieval-only, while context binding and challenge became separate runtime skills triggered by WorkflowPolicy.
```

