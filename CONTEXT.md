# Ragclaw Context

## 0. Topic Entry

When the topic is clear, prefer entering the project through `notes/` instead of trying to scan the whole repository.

### Intent / Rule Tuning / Evaluation / Small-Model SFT

Read in this order:

1. `notes/intent/README.md`
2. `notes/intent/intent_project_info.md`
3. `notes/intent/intent_testing_and_evaluation.md`
4. `notes/intent/rule_tuning.md`
5. `notes/intent/rule_supervision.md`
6. `notes/intent/sft_preparation.md`

### Knowledge Construct / Crawling / Knowledge Layout

Read in this order:

1. `notes/knowledge_construct/README.md`
2. `notes/knowledge_construct/crawler/README.md`
3. `notes/knowledge_construct/knowledge/README.md`

### Context / Memory / Session / Group

Read in this order:

1. `notes/modules/README.md`
2. `notes/modules/context_manager.md`
3. `notes/modules/memory_system.md`
4. `notes/modules/session_manager.md`
5. `notes/modules/group_management.md`

### Working Notes / Transitional Documents

If the user is discussing a temporary plan, an unfinished design, or a document in progress, check:

1. `notes/working/README.md`
2. the relevant files under `notes/working/`

## 1. Product

Ragclaw is a local-first, file-first, auditable agent workbench.

The system is optimized for:

- visible reasoning trails
- inspectable tool usage
- explainable retrieval
- editable memory and skill assets

It is not primarily a generic chat app. It is an agent workspace where files are the source of truth.

---

## 2. Core Domain Terms

Use these terms consistently when discussing the codebase.

### Agent Workspace

The end-to-end environment in which a user chats with the agent, inspects execution, edits files, and reviews retrieval evidence.

### Session Store

The persisted conversation history written to `backend/sessions/*.json`.

### Memory Store

The long-term memory files under `backend/memory/`.

### Knowledge Workspace

The local knowledge corpus under `backend/knowledge/`, including Markdown, JSON, PDF, Excel, and any future user-added assets.

### Skill

A readable, editable capability package whose core contract is `SKILL.md`.

### Skill Retrieval

The retrieval path where a specialized skill attempts to satisfy the user request before general retrieval fallback is used.

### Hybrid Retrieval

The fallback retrieval path that combines vector retrieval, BM25 retrieval, and RRF fusion.

### Retrieval Orchestrator

The module that decides how Skill Retrieval and Hybrid Retrieval are combined.

### Evidence

The observable support returned to the user or inspector, including retrieval citations, tool calls, and any supporting execution trail.

### Intent Module

The module that transforms a user input into:

- `input`
- `evidence`
- `resolved`
- `control`

It does not answer the question itself. It stabilizes direction before execution.

### Control Signal

The coarse execution switch produced by the Intent Module, used to decide whether the request should go to `rag`, `chat`, `direct`, `agent`, or `reject`.

### Domain Bootstrap Rules

Group-shared rule assets that help cold-start intent recognition in current knowledge domains, but are not globally stable semantics.

---

## 3. Current System Shape

The current system has these major work areas:

- `backend/api`
  - HTTP interfaces for chat, file operations, config, sessions, and indexing
- `backend/graph`
  - agent execution and prompt assembly
- `backend/knowledge_retrieval`
  - Skill Retrieval plus Hybrid Retrieval fallback
- `backend/skills`
  - project-local skills
- `backend/tools`
  - tool adapters
- `backend/memory`
  - long-term memory files
- `frontend`
  - the three-column local workbench UI

---

## 4. Retrieval Language

When discussing retrieval, prefer this flow:

1. User request enters the Agent Workspace
2. Retrieval Orchestrator attempts Skill Retrieval first
3. If Skill Retrieval is partial, uncertain, or not found, Hybrid Retrieval runs
4. Hybrid Retrieval combines vector, BM25, and RRF
5. The answer returns with visible Evidence

Avoid calling this simply “search”.

---

## 5. Intent Language

When discussing intent, prefer this flow:

1. `input`
2. `evidence`
3. `resolved`
4. `control`

Use:

- `global stable rules`
- `group_shared / domain bootstrap rules`
- `signal_buckets`
- `context_signals`

Avoid flattening everything into “classifier output”.

---

## 6. Current Architectural Priorities

The current priorities are:

- make retrieval and tool execution explainable
- make intent routing more stable and more auditable
- keep knowledge and memory file-native
- improve testability and AI navigability
- prepare the system for a future small intent model without losing rule guardrails
- keep `notes/` as the primary knowledge base until more topics are stable enough to move into `docs/`

---

## 7. Known Boundaries

The codebase currently assumes:

- local-first operation
- file-visible state
- evolving skill and retrieval logic

The codebase does not yet assume:

- fully mature production SaaS constraints
- final intent modeling architecture
- complete ADR coverage
- a fully mature documentation taxonomy beyond `README.md`, `CONTEXT.md`, `notes/`, and a light `docs/`
