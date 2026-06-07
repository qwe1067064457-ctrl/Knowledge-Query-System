from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.session_views import (
    build_session_record,
    create_default_session,
    update_session_title,
)
from config import runtime_config
from graph.agent import agent_manager
from graph.prompt_builders.answer_prompt_assembler import build_answer_system_prompt
from context.session.session_manager import DEFAULT_AGENT, DEFAULT_GROUP, DEFAULT_USER, SessionStatus

router = APIRouter()


class CreateSessionRequest(BaseModel):
    title: str = "新会话"
    active_group_id: str = "general"
    allowed_group_ids: list[str] | None = None


class RenameSessionRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)


class GenerateTitleRequest(BaseModel):
    message: str | None = None


@router.get("/sessions")
async def list_sessions() -> list[dict[str, Any]]:
    session_manager = agent_manager.raw_session_manager
    if session_manager is None:
        raise HTTPException(status_code=503, detail="Agent manager is not initialized")
    sessions = session_manager.list_user_sessions(DEFAULT_GROUP, DEFAULT_AGENT, DEFAULT_USER, limit=100)
    return [
        {
            "id": session.id,
            "title": ((session.metadata or {}).get("title") or f"会话 {session.id[:8]}"),
            "created_at": session.created_at.timestamp() * 1000,
            "updated_at": session.last_active_at.timestamp() * 1000,
            "message_count": session.turn_count,
        }
        for session in sessions
    ]


@router.post("/sessions")
async def create_session(payload: CreateSessionRequest) -> dict[str, Any]:
    raw_session_manager = agent_manager.raw_session_manager
    if raw_session_manager is None:
        raise HTTPException(status_code=503, detail="Agent manager is not initialized")
    return create_default_session(
        raw_session_manager,
        title=payload.title,
        active_group_id=payload.active_group_id,
        allowed_group_ids=payload.allowed_group_ids,
    )


@router.put("/sessions/{session_id}")
async def rename_session(session_id: str, payload: RenameSessionRequest) -> dict[str, Any]:
    session_manager = agent_manager.raw_session_manager
    if session_manager is None:
        raise HTTPException(status_code=503, detail="Agent manager is not initialized")
    session = session_manager.get_session(session_id, DEFAULT_GROUP, DEFAULT_AGENT)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return update_session_title(session_manager, session_id, payload.title)


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> dict[str, bool]:
    session_manager = agent_manager.raw_session_manager
    if session_manager is None:
        raise HTTPException(status_code=503, detail="Agent manager is not initialized")
    session_manager.delete_session(session_id, DEFAULT_GROUP, DEFAULT_AGENT)
    return {"ok": True}


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str) -> dict[str, Any]:
    session_manager = agent_manager.raw_session_manager
    if session_manager is None or agent_manager.base_dir is None:
        raise HTTPException(status_code=503, detail="Agent manager is not initialized")
    return {
        "system_prompt": build_answer_system_prompt(agent_manager.base_dir, runtime_config.get_rag_mode()),
        "messages": build_session_record(session_manager, session_id)["messages"],
    }


@router.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str) -> dict[str, Any]:
    session_manager = agent_manager.raw_session_manager
    if session_manager is None:
        raise HTTPException(status_code=503, detail="Agent manager is not initialized")
    return build_session_record(session_manager, session_id)


@router.post("/sessions/{session_id}/generate-title")
async def generate_title(session_id: str, payload: GenerateTitleRequest) -> dict[str, str]:
    session_manager = agent_manager.raw_session_manager
    if session_manager is None:
        raise HTTPException(status_code=503, detail="Agent manager is not initialized")
    if payload.message:
        seed = payload.message
    else:
        messages = build_session_record(session_manager, session_id)["messages"]
        first_user = next((item["content"] for item in messages if item.get("role") == "user"), "")
        seed = first_user
    title = await agent_manager.generate_title(seed or "新会话")
    update_session_title(session_manager, session_id, title)
    return {"session_id": session_id, "title": title}
