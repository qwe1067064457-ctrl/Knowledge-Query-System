from __future__ import annotations

import asyncio

from helpers import make_memory_system, temp_workspace


def test_daily_log_duplicate_checkpoint_is_filtered() -> None:
    async def run() -> None:
        with temp_workspace() as workspace:
            memory = make_memory_system(workspace)

            first = await memory.flush_from_context(
                "law",
                "default",
                "同一轮确认 retrieval gate 需要保留 challenge path。",
                user_id="u1",
                source_session_id="s1",
            )
            second = await memory.flush_from_context(
                "law",
                "default",
                "同一轮确认 retrieval gate 需要保留 challenge path。",
                user_id="u1",
                source_session_id="s1",
            )

            rows = memory.get_recent_memories("law", "default", days=1, user_id="u1")
            assert first["flushed"] is True
            assert second["flushed"] is False
            assert len(rows) == 1

    asyncio.run(run())
