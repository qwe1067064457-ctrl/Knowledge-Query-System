from __future__ import annotations

import asyncio
from pathlib import Path

from api.sessions import CreateSessionRequest, create_session
from context.session_manager import SessionManager
from context.legacy_adapter import LegacySessionManagerAdapter
from graph.agent import agent_manager


def test_create_session_persists_scope_metadata(tmp_path: Path) -> None:
    raw_session_manager = SessionManager(tmp_path / "storage")
    legacy_adapter = LegacySessionManagerAdapter(raw_session_manager)
    legacy_adapter.configure_legacy_paths(tmp_path)

    original_session_manager = agent_manager.session_manager
    original_raw_session_manager = agent_manager.raw_session_manager
    try:
        agent_manager.session_manager = legacy_adapter
        agent_manager.raw_session_manager = raw_session_manager

        record = asyncio.run(
            create_session(
                CreateSessionRequest(
                    title="测试会话",
                    active_group_id="law",
                    allowed_group_ids=["law", "medical"],
                )
            )
        )

        session = raw_session_manager.get_session(record["id"], "general", "default")
        assert session is not None
        assert session.metadata is not None
        assert session.metadata["active_group_id"] == "law"
        assert session.metadata["allowed_group_ids"] == ["law", "medical"]
    finally:
        agent_manager.session_manager = original_session_manager
        agent_manager.raw_session_manager = original_raw_session_manager
