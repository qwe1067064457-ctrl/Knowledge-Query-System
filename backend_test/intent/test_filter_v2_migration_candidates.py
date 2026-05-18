from __future__ import annotations

from evaluation.intent.filter_v2_migration_candidates import select_v2_migration_candidates


def _row(
    *,
    row_id: str,
    complexity: str = "simple",
    shape: str = "single_question",
    follow_up: bool = False,
    challenge: bool = False,
    ask_source: bool = False,
    needs_clarification: bool = False,
    route: str = "rag",
    mode: str = "normal",
) -> dict:
    return {
        "id": row_id,
        "batch": "test",
        "input": {"user_query": "test", "history": []},
        "gold": {
            "evidence": {"classifier_mode": "rule_plus_model"},
            "resolved": {
                "main_intent": "qa",
                "modifiers": {
                    "follow_up": follow_up,
                    "challenge": challenge,
                    "ask_source": ask_source,
                    "ask_capability": False,
                    "needs_clarification": needs_clarification,
                    "out_of_scope": False,
                    "soft_doubt": False,
                },
                "task": {
                    "complexity": complexity,
                    "shape": shape,
                },
                "context_dependency": "none",
            },
            "control": {"route": route, "mode": mode},
        },
    }


def test_select_v2_migration_candidates_picks_high_risk_rows() -> None:
    rows = [
        _row(row_id="compound", complexity="compound", shape="multi_question"),
        _row(row_id="clarify", needs_clarification=True, route="direct", mode="clarify"),
        _row(row_id="stable"),
    ]

    selected = select_v2_migration_candidates(rows)

    assert {row["id"] for row in selected} == {"compound", "clarify"}
    assert selected[0]["migration_review"]["required"] is True


def test_select_v2_migration_candidates_skips_low_risk_rows() -> None:
    rows = [_row(row_id="stable_a"), _row(row_id="stable_b", route="rag", mode="normal")]

    selected = select_v2_migration_candidates(rows)

    assert selected == []
