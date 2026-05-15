# Ragclaw

Ragclaw is a local-first, file-first, auditable agent workbench.

The repository currently uses a deliberately light documentation structure:

- `README.md`
  - human-facing project entry
- `CONTEXT.md`
  - AI-facing topic and terminology entry
- `notes/`
  - the primary knowledge base
- `docs/`
  - light formal documentation for more stable material

## Documentation Map

- `CONTEXT.md`
  - read this first when an AI agent or a new conversation needs a topic entry
- `notes/README.md`
  - the main knowledge-base entry
- `notes/intent/README.md`
  - stable entry for the intent topic
- `notes/working/README.md`
  - transitional and still-moving documents
- `docs/README.md`
  - light formal documentation map
- `docs/adr/README.md`
  - Architecture Decision Record guidance

## What This Project Emphasizes

- local-first operation
- file-visible state
- explainable retrieval
- inspectable tool usage
- editable memory and skill assets

It is not primarily a generic chat app. Files are the source of truth.

## Current System Shape

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
  - the local workbench UI

## Quick Start

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn app:app --host 127.0.0.1 --port 8004 --reload
```

Health check:

```text
http://127.0.0.1:8004/health
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Default frontend URL:

```text
http://127.0.0.1:3000
```

Default backend API URL:

```text
http://127.0.0.1:8004/api
```

If the backend port changes:

```powershell
$env:NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:8010/api"
```

## Retrieval Summary

The current retrieval path is:

1. the user request enters the Agent Workspace
2. Skill Retrieval runs first
3. if the result is partial, uncertain, or not found, Hybrid Retrieval runs
4. Hybrid Retrieval combines vector retrieval, BM25 retrieval, and RRF
5. the answer returns with visible evidence

For the current topic language and reading order, use `CONTEXT.md` instead of relying on this README alone.
