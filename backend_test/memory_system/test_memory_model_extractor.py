from __future__ import annotations

import asyncio

from helpers import make_memory_system, temp_workspace, write_group_meta


def test_model_extractor_writes_structured_memory_payloads() -> None:
    async def run() -> None:
        with temp_workspace() as workspace:
            write_group_meta(
                workspace,
                "law",
                {
                    "enabled_memory_types": ["core", "daily_log", "domain_case"],
                    "core": {
                        "explicit_markers": ["ALWAYS", "DEFAULT"],
                        "min_candidate_length": 1,
                        "max_candidate_length": 200,
                    },
                    "daily_log": {"checkpoint_enabled": True},
                    "domain_case": {
                        "completion_markers": ["DONE"],
                        "structural_markers": ["ISSUE", "ANALYSIS", "CONCLUSION"],
                        "case_markers": ["CASE"],
                    },
                },
            )
            memory = make_memory_system(workspace)

            def fake_llm(prompt: str) -> str:
                if "抽取成 core memory" in prompt:
                    return """{"memory_type":"core","scope":"user_group","subject":"citation_style","content":"在 LAW 工作区优先引用法条原文。","confidence":0.93}"""
                if "抽取成 daily_log" in prompt:
                    return """{"memory_type":"daily_log","scope":"user_group","subject":"retrieval_gate","content":"本轮确认 retrieval gate 需要保留 challenge path。","confidence":0.88}"""
                if "抽取成 domain_case" in prompt:
                    return """{"memory_type":"domain_case","scope":"user_group","title":"law::breach liability","subject":"breach liability","content":"ISSUE: breach liability. ANALYSIS: compare foreseeability. CONCLUSION: keep it in the main holding. DONE.","confidence":0.91}"""
                return ""

            memory.set_extractor_llm_call(fake_llm)
            await memory.flush_from_context(
                "law",
                "default",
                "ISSUE: breach liability. ANALYSIS: compare foreseeability. CONCLUSION: keep it in the main holding. DONE.",
                user_id="u1",
                source_session_id="session_1",
                messages=[
                    {"id": "msg_1", "role": "user", "content": "DEFAULT in this LAW workspace, cite statute text first.", "memory_scope": "user_group"},
                    {"id": "msg_2", "role": "assistant", "content": "ISSUE: breach liability. ANALYSIS: compare foreseeability. CONCLUSION: keep it in the main holding. DONE."},
                ],
            )

            core_entries = memory.get_core_memories(user_id="u1", group_id="law")
            assert any(item.scope == "user_group" and item.subject == "citation_style" for item in core_entries)

            daily_logs = memory.get_recent_memories("law", "default", days=1, user_id="u1")
            assert daily_logs
            assert daily_logs[0].subject == "retrieval_gate"
            assert daily_logs[0].anchor_spans

            cases = memory.search(
                "law",
                "default",
                "breach liability foreseeability",
                user_id="u1",
                include_core=False,
                include_daily_logs=False,
                min_score=0.01,
            )
            assert cases
            assert cases[0].title == "law::breach liability"
            assert cases[0].scope == "user_group"

    asyncio.run(run())


def test_model_extractor_falls_back_to_rule_based_payload_when_json_invalid() -> None:
    async def run() -> None:
        with temp_workspace() as workspace:
            write_group_meta(
                workspace,
                "law",
                {
                    "enabled_memory_types": ["core", "daily_log"],
                    "core": {
                        "explicit_markers": ["ALWAYS"],
                        "min_candidate_length": 1,
                        "max_candidate_length": 120,
                    },
                    "daily_log": {"checkpoint_enabled": True},
                    "domain_case": {
                        "completion_markers": ["DONE"],
                        "structural_markers": ["ISSUE", "ANALYSIS", "CONCLUSION"],
                        "case_markers": ["CASE"],
                    },
                },
            )
            memory = make_memory_system(workspace)
            memory.set_extractor_llm_call(lambda _prompt: "not-json")

            result = await memory.flush_from_context(
                "law",
                "default",
                "Checkpoint summary",
                user_id="u1",
                source_session_id="session_2",
                messages=[{"id": "msg_1", "role": "user", "content": "ALWAYS answer in Chinese."}],
            )

            core_entries = memory.get_core_memories(user_id="u1", group_id="law")
            assert result["flushed"] is True
            assert any(item.scope == "user_global" and item.content == "ALWAYS answer in Chinese." for item in core_entries)

    asyncio.run(run())
