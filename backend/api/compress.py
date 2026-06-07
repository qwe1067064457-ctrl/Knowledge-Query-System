from __future__ import annotations

from fastapi import APIRouter, HTTPException

from graph.agent import agent_manager
from context.session.session_manager import DEFAULT_AGENT, DEFAULT_GROUP

router = APIRouter()


@router.post("/sessions/{session_id}/compress")
async def compress_session(session_id: str) -> dict[str, int]:
    session_manager = agent_manager.raw_session_manager
    context_manager = agent_manager.context_manager
    if session_manager is None or context_manager is None:
        raise HTTPException(status_code=503, detail="Agent manager is not initialized")

    entries = session_manager.get_transcript(DEFAULT_GROUP, DEFAULT_AGENT, session_id, include_compacted=True)
    if len([entry for entry in entries if entry.entry_type != "compaction"]) < 4:
        raise HTTPException(status_code=400, detail="At least 4 messages are required")
    result = await context_manager.compact_session(DEFAULT_GROUP, DEFAULT_AGENT, session_id)
    return {
        "original_tokens": int(result.get("original_tokens", 0)),
        "compressed_tokens": int(result.get("compressed_tokens", 0)),
    }
