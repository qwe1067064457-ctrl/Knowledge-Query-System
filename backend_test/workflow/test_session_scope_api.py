from __future__ import annotations

import asyncio
from pathlib import Path

from api.sessions import CreateSessionRequest, create_session
from context.session.session_manager import SessionManager
from graph.agent import agent_manager


def test_create_session_persists_scope_metadata(tmp_path: Path) -> None:
    raw_session_manager = SessionManager(tmp_path / "storage")

    original_raw_session_manager = agent_manager.raw_session_manager
    try:
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
        agent_manager.raw_session_manager = original_raw_session_manager
