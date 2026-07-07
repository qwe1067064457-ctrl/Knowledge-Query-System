from __future__ import annotations

import sys
import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from api.sessions import router
from context.models import TranscriptEntry
from context.session.session_manager import SessionManager
from graph.agent import agent_manager


def _make_temp_dir() -> Path:
    temp_root = ROOT / "backend" / ".test_tmp" / "session_agent_traces_api"
    temp_root.mkdir(parents=True, exist_ok=True)
    directory = temp_root / f"case_{uuid.uuid4().hex}"
    directory.mkdir(parents=True, exist_ok=False)
    return directory


def _build_client(session_manager: SessionManager) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    agent_manager.raw_session_manager = session_manager
    return TestClient(app)


def _make_entry(session_id: str, group_id: str, role: str, content: str) -> TranscriptEntry:
    return TranscriptEntry(
        id=f"entry_{uuid.uuid4().hex[:8]}",
        session_id=session_id,
        group_id=group_id,
        timestamp=1,
        role=role,  # type: ignore[arg-type]
        entry_type="normal",
        content=content,
        token_count=max(1, len(content) // 4),
    )


def test_session_agent_traces_api_returns_isolated_trace_rows() -> None:
    tmp_path = _make_temp_dir()
    session_manager = SessionManager(tmp_path / "storage")
    original_raw_session_manager = agent_manager.raw_session_manager
    try:
        session = session_manager.create_session("general", "default", "default")
        assistant_entry = _make_entry(session.id, "general", "assistant", "这是回答。")
        session_manager.append_entry("general", "default", assistant_entry)
        session_manager.append_agent_trace(
            "general",
            "default",
            session.id,
            {
                "entry_id": assistant_entry.id,
                "session_id": session.id,
                "intent_trace": {"resolved": {"main_intent": "qa"}},
                "workflow_trace": {"plan": {"route": "qa"}},
                "execution_events": [{"stage": "route_payload_ready", "payload": {"action": "respond"}}],
            },
        )

        client = _build_client(session_manager)
        response = client.get(f"/api/sessions/{session.id}/agent-traces")

        assert response.status_code == 200
        payload = response.json()
        assert payload["session_id"] == session.id
        assert payload["group_id"] == "general"
        assert payload["agent_id"] == "default"
        assert payload["count"] == 1
        assert payload["traces"][0]["entry_id"] == assistant_entry.id
        assert payload["traces"][0]["intent_trace"]["resolved"]["main_intent"] == "qa"
        assert payload["traces"][0]["workflow_trace"]["plan"]["route"] == "qa"
        assert payload["traces"][0]["execution_events"][0]["stage"] == "route_payload_ready"
    finally:
        agent_manager.raw_session_manager = original_raw_session_manager


def test_session_agent_traces_api_returns_404_for_unknown_session() -> None:
    tmp_path = _make_temp_dir()
    session_manager = SessionManager(tmp_path / "storage")
    original_raw_session_manager = agent_manager.raw_session_manager
    try:
        client = _build_client(session_manager)
        response = client.get("/api/sessions/session_missing/agent-traces")

        assert response.status_code == 404
        assert response.json()["detail"] == "Session not found"
    finally:
        agent_manager.raw_session_manager = original_raw_session_manager
