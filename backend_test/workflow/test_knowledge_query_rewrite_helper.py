from __future__ import annotations

from workflow.helpers.knowledge_query_rewrite_helper import KnowledgeQueryRewriteHelper


def test_knowledge_query_rewrite_helper_expands_chinese_query_with_english_terms() -> None:
    helper = KnowledgeQueryRewriteHelper()

    result = helper.rewrite(
        "查知识库，ai发展趋势",
        llm_call=lambda _prompt: (
            '{"rewritten_query":"AI development trends AI Agent multi-agent systems",'
            '"query_hints":["AI Agent","multi-agent systems","foundation models"]}'
        ),
    )

    assert result["applied"] is True
    assert "查知识库，ai发展趋势" in result["query"]
    assert "AI development trends" in result["query"]
    assert "multi-agent systems" in result["query"]
    assert result["query_hints"] == ("AI Agent", "multi-agent systems", "foundation models")


def test_knowledge_query_rewrite_helper_keeps_raw_query_when_llm_unavailable() -> None:
    helper = KnowledgeQueryRewriteHelper()

    result = helper.rewrite("查知识库，ai发展趋势", llm_call=None)

    assert result == {
        "applied": False,
        "query": "查知识库，ai发展趋势",
        "rewritten_query": None,
        "query_hints": (),
    }
