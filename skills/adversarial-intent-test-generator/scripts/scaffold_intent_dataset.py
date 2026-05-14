from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_BATCHES = (
    "standard_qa",
    "fuzzy_qa",
    "chat",
    "meta",
    "follow_up",
    "mixed_intent",
    "adversarial",
    "long_case_complex",
)

DEFAULT_HISTORY_VARIANTS = ("supportive", "weak", "conflicting")
DEFAULT_GENERATION_MODES = ("near_miss", "mixed", "cost_focused")

FALSE_UNSUPPORTED = {
    "file_write_request": False,
    "file_delete_request": False,
    "kb_admin_request": False,
    "privileged_operation": False,
    "unknown_external_action": False,
}

DEP_NONE = {
    "none": True,
    "history_reference": False,
    "previous_answer": False,
    "previous_retrieval": False,
    "ambiguous": False,
}
DEP_HISTORY = {
    "none": False,
    "history_reference": True,
    "previous_answer": False,
    "previous_retrieval": False,
    "ambiguous": False,
}
DEP_PREV_ANSWER = {
    "none": False,
    "history_reference": False,
    "previous_answer": True,
    "previous_retrieval": False,
    "ambiguous": False,
}
DEP_AMBIG = {
    "none": False,
    "history_reference": False,
    "previous_answer": False,
    "previous_retrieval": False,
    "ambiguous": True,
}

HISTORY_TEMPLATES: dict[str, dict[str, list[dict[str, str]]]] = {
    "follow_up": {
        "supportive": [
            {"role": "user", "content": "刚才我们在讨论合同责任和证据条件。"},
            {"role": "assistant", "content": "我刚才先按合同责任和证据规则做了一个概括。"},
        ],
        "weak": [
            {"role": "user", "content": "前面提过这个问题。"},
            {"role": "assistant", "content": "我前面简单说了一下，但没有展开。"},
        ],
        "conflicting": [
            {"role": "user", "content": "刚才我们在聊推荐哪本书更适合入门。"},
            {"role": "assistant", "content": "我刚才给了两本非法律类书籍的建议。"},
        ],
    },
    "challenge": {
        "supportive": [
            {"role": "user", "content": "你刚才说试用期最长可以约定六个月。"},
            {"role": "assistant", "content": "是的，我刚才按常见劳动合同期限做了概括。"},
        ],
        "weak": [
            {"role": "user", "content": "你前面提过这个问题。"},
            {"role": "assistant", "content": "我前面简单提了一下，但没有展开法条依据。"},
        ],
        "conflicting": [
            {"role": "user", "content": "刚才我们在聊天气和推荐书目。"},
            {"role": "assistant", "content": "我刚才给的是日常闲聊回答。"},
        ],
    },
    "meta": {
        "supportive": [
            {"role": "user", "content": "你刚才说合同无效要分情形判断。"},
            {"role": "assistant", "content": "是的，我刚才根据民法典合同编做了一个概括。"},
        ],
        "weak": [
            {"role": "user", "content": "你前面讲过一点。"},
            {"role": "assistant", "content": "我前面提了一句，但没有给细节。"},
        ],
        "conflicting": [
            {"role": "user", "content": "刚才我们在聊电影。"},
            {"role": "assistant", "content": "我刚才是在做轻松闲聊。"},
        ],
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scaffold an intent dataset directory. Can create empty files, generate a prefilled campaign, or derive samples from a query list."
    )
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--batches", nargs="*", default=list(DEFAULT_BATCHES))
    parser.add_argument(
        "--profile",
        choices=("empty", "v1_adversarial_campaign", "twins_campaign_v2", "from_query_list"),
        default="empty",
    )
    parser.add_argument("--input-file", type=Path, default=None)
    parser.add_argument("--generation-modes", nargs="*", default=list(DEFAULT_GENERATION_MODES))
    parser.add_argument("--history-variants", nargs="*", default=list(DEFAULT_HISTORY_VARIANTS))
    parser.add_argument("--sample-limit", type=int, default=0)
    return parser.parse_args()


def modifiers(**kwargs: bool) -> dict[str, bool]:
    base = {
        "follow_up": False,
        "challenge": False,
        "ask_source": False,
        "ask_capability": False,
        "needs_clarification": False,
        "out_of_scope": False,
    }
    base.update(kwargs)
    return base


def sample(
    *,
    sid: str,
    batch: str,
    query: str,
    history: list[dict[str, str]],
    classifier_mode: str,
    required_signals: list[str],
    required_rule_ids: list[str],
    rule_expectations: dict[str, bool],
    dependency_signals: dict[str, bool],
    main_intent: str,
    mod: dict[str, bool],
    complexity: str,
    shape: str,
    context_dependency: str,
    route: str,
    mode: str,
    notes: str,
    history_template: str,
    generation_mode: str,
    risk_flags: list[str] | None = None,
    source_query_id: str | None = None,
) -> dict[str, Any]:
    merged_risk_flags = _merge_risk_flags(
        risk_flags or [],
        _derived_risk_flags(
            query=query,
            history=history,
            main_intent=main_intent,
            route=route,
            context_dependency=context_dependency,
        ),
    )
    return {
        "id": sid,
        "batch": batch,
        "input": {
            "user_query": query,
            "history": history,
        },
        "gold": {
            "evidence": {
                "classifier_mode": classifier_mode,
                "required_signals": required_signals,
                "required_rule_ids": required_rule_ids,
                "rule_expectations": rule_expectations,
                "unsupported_signals": dict(FALSE_UNSUPPORTED),
                "dependency_signals": dependency_signals,
            },
            "resolved": {
                "main_intent": main_intent,
                "modifiers": mod,
                "task": {
                    "complexity": complexity,
                    "shape": shape,
                },
                "context_dependency": context_dependency,
            },
            "control": {
                "route": route,
                "mode": mode,
            },
        },
        "notes": notes,
        "source_query_id": source_query_id,
        "review_hints": {
            "consistency_checks": [
                "input 是否足以支撑 resolved",
                "evidence 是否是最小充分证据",
                "control 是否符合错误路由成本预期",
            ],
            "history_template": history_template,
            "generation_mode": generation_mode,
            "risk_flags": merged_risk_flags,
        },
    }


def _merge_risk_flags(*flag_groups: list[str]) -> list[str]:
    merged: list[str] = []
    for group in flag_groups:
        for flag in group:
            if flag not in merged:
                merged.append(flag)
    return merged


def _derived_risk_flags(
    *,
    query: str,
    history: list[dict[str, str]],
    main_intent: str,
    route: str,
    context_dependency: str,
) -> list[str]:
    flags: list[str] = []
    if context_dependency == "none" and history:
        flags.append("REDUNDANT_HISTORY_FOR_NON_DEP_SAMPLE")
    if main_intent == "qa" and route == "chat":
        flags.append("ROUTE_INTENT_MISMATCH")
    if main_intent == "system" and route == "rag":
        flags.append("ROUTE_INTENT_MISMATCH")
    if route == "rag" and len(query) > 120:
        flags.append("POSSIBLE_COMPLEX_TASK_MISS_ROUTED")
    return flags


def _write_json(path: Path, payload: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def generate_empty_dataset(output_dir: Path, batches: list[str]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for batch in batches:
        path = output_dir / f"{batch}.json"
        if not path.exists():
            _write_json(path, [])


def generate_v1_adversarial_campaign(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    follow_up_rows = _build_follow_up_near_miss_rows()
    challenge_rows = _build_challenge_near_miss_rows()
    _write_json(output_dir / "follow_up.json", follow_up_rows)
    _write_json(output_dir / "challenge.json", challenge_rows)
    readme = """# v1_adversarial_campaign

This campaign focuses on the first high-value adversarial loop for intent recognition.

Scope:
- `follow_up`
- `challenge`

Design goals:
- prioritize `near_miss` and `mixed`
- include supportive, weak, and conflicting history templates
- prefill the four-layer schema so a reviewer only needs to confirm or adjust the gold labels
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")


def generate_twins_campaign_v2(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    challenge_rows = _build_challenge_vs_clarify_twins()
    follow_up_rows = _build_follow_up_vs_ambiguous_twins()
    qa_system_rows = _build_qa_vs_system_twins()
    _write_json(output_dir / "challenge_twins.json", challenge_rows)
    _write_json(output_dir / "follow_up_twins.json", follow_up_rows)
    _write_json(output_dir / "qa_system_twins.json", qa_system_rows)
    readme = """# twins_campaign_v2

This campaign focuses on twin-pair adversarial samples.

Scope:
- challenge vs clarify
- follow_up vs ambiguous
- qa vs system

Design goals:
- keep surface wording very close while flipping the intended route
- expose brittle rule boundaries rather than broad domain coverage
- add lightweight risk flags for route and history mismatches
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")


def generate_from_query_list(
    *,
    output_dir: Path,
    input_file: Path,
    generation_modes: list[str],
    history_variants: list[str],
    sample_limit: int,
) -> None:
    rows = _load_query_items(input_file)
    if sample_limit > 0:
        rows = rows[:sample_limit]

    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in rows:
        query_id = item["id"]
        query = item["query"]
        hints = item.get("hints", {})
        batch = _infer_batch(query, hints.get("preferred_batch"))
        variants = _build_variants_for_query(
            source_query_id=query_id,
            query=query,
            batch=batch,
            generation_modes=generation_modes,
            history_variants=history_variants,
        )
        grouped.setdefault(batch, []).extend(variants)

    output_dir.mkdir(parents=True, exist_ok=True)
    for batch, batch_rows in sorted(grouped.items()):
        _write_json(output_dir / f"{batch}.json", batch_rows)

    readme = f"""# query_list_campaign

Input file: `{input_file.name}`

This campaign was scaffolded from a raw query list.

Generation modes:
- {", ".join(generation_modes)}

History variants:
- {", ".join(history_variants)}
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")


def _load_query_items(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".txt":
        items = []
        for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            query = line.strip()
            if not query:
                continue
            items.append({"id": f"query_{index:03d}", "query": query, "hints": {}})
        return items

    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("JSON input file must contain a list")
        return [_normalize_query_item(item, idx) for idx, item in enumerate(payload, start=1)]

    if path.suffix.lower() == ".jsonl":
        rows = []
        for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            rows.append(_normalize_query_item(json.loads(line), idx))
        return rows

    raise ValueError(f"Unsupported input file format: {path.suffix}")


def _normalize_query_item(item: Any, index: int) -> dict[str, Any]:
    if isinstance(item, str):
        return {"id": f"query_{index:03d}", "query": item, "hints": {}}
    if not isinstance(item, dict) or "query" not in item:
        raise ValueError("Each query item must be a string or an object with a 'query' field")
    return {
        "id": str(item.get("id") or f"query_{index:03d}"),
        "query": str(item["query"]),
        "hints": dict(item.get("hints") or {}),
        "notes": str(item.get("notes") or ""),
    }


def _infer_batch(query: str, preferred_batch: str | None = None) -> str:
    if preferred_batch:
        return preferred_batch
    text = query.strip()
    if _looks_like_follow_up(text):
        return "follow_up"
    if _looks_like_challenge(text):
        return "challenge"
    if _looks_like_ask_source(text):
        return "meta"
    if _looks_like_mixed(text):
        return "mixed_intent"
    if _looks_like_fuzzy_qa(text):
        return "fuzzy_qa"
    if _looks_like_long_case(text):
        return "long_case_complex"
    if _looks_like_chat(text):
        return "chat"
    return "standard_qa"


def _build_variants_for_query(
    *,
    source_query_id: str,
    query: str,
    batch: str,
    generation_modes: list[str],
    history_variants: list[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for history_variant in _history_variants_for_batch(batch, history_variants):
        rows.append(
            _build_base_variant(
                source_query_id=source_query_id,
                query=query,
                batch=batch,
                history_variant=history_variant,
            )
        )
    if "near_miss" in generation_modes:
        near_miss = _build_near_miss_variant(source_query_id=source_query_id, query=query, batch=batch)
        if near_miss is not None:
            rows.append(near_miss)
    if "mixed" in generation_modes:
        mixed = _build_mixed_variant(source_query_id=source_query_id, query=query, batch=batch)
        if mixed is not None:
            rows.append(mixed)
    if "cost_focused" in generation_modes:
        cost_variant = _build_cost_focused_variant(source_query_id=source_query_id, query=query, batch=batch)
        if cost_variant is not None:
            rows.append(cost_variant)
    return rows


def _history_variants_for_batch(batch: str, requested: list[str]) -> list[str]:
    supported = list(requested)
    if batch == "follow_up":
        return [variant for variant in supported if variant in {"supportive", "weak", "conflicting"}]
    if batch in {"challenge", "meta"}:
        return [variant for variant in supported if variant in {"supportive", "weak"}]
    if batch == "fuzzy_qa":
        return [variant for variant in supported if variant == "weak"] or ["weak"]
    return ["supportive"]


def _build_base_variant(
    *,
    source_query_id: str,
    query: str,
    batch: str,
    history_variant: str,
) -> dict[str, Any]:
    if batch == "follow_up":
        return _follow_up_variant(source_query_id, query, history_variant)
    if batch == "challenge":
        return _challenge_variant(source_query_id, query, history_variant)
    if batch == "meta":
        return _meta_variant(source_query_id, query, history_variant)
    if batch == "fuzzy_qa":
        return _fuzzy_variant(source_query_id, query, history_variant)
    if batch == "long_case_complex":
        return _long_case_variant(source_query_id, query)
    if batch == "chat":
        return _chat_variant(source_query_id, query)
    return _standard_qa_variant(source_query_id, query, batch)


def _standard_qa_variant(source_query_id: str, query: str, batch: str) -> dict[str, Any]:
    return sample(
        sid=f"{source_query_id}_{batch}_supportive",
        batch=batch,
        query=query,
        history=[],
        classifier_mode="rule_plus_model",
        required_signals=["qa"],
        required_rule_ids=[],
        rule_expectations={"intent.qa.domain": False},
        dependency_signals=dict(DEP_NONE),
        main_intent="qa",
        mod=modifiers(),
        complexity="simple",
        shape="single_question",
        context_dependency="none",
        route="rag",
        mode="normal",
        notes="基于原始 query 的标准 QA 草稿",
        history_template="supportive",
        generation_mode="positive",
        risk_flags=[],
        source_query_id=source_query_id,
    )


def _chat_variant(source_query_id: str, query: str) -> dict[str, Any]:
    return sample(
        sid=f"{source_query_id}_chat_supportive",
        batch="chat",
        query=query,
        history=[],
        classifier_mode="model_first_with_rule_guard",
        required_signals=["chat"],
        required_rule_ids=[],
        rule_expectations={"intent.chat.greeting": False, "intent.qa.domain": False},
        dependency_signals=dict(DEP_NONE),
        main_intent="chat",
        mod=modifiers(),
        complexity="simple",
        shape="none",
        context_dependency="none",
        route="chat",
        mode="normal",
        notes="基于原始 query 的闲聊草稿",
        history_template="supportive",
        generation_mode="positive",
        risk_flags=[],
        source_query_id=source_query_id,
    )


def _fuzzy_variant(source_query_id: str, query: str, history_variant: str) -> dict[str, Any]:
    risk_flags = ["INPUT_TOO_WEAK", "QUERY_NEEDS_MANUAL_REVIEW"]
    return sample(
        sid=f"{source_query_id}_fuzzy_{history_variant}",
        batch="fuzzy_qa",
        query=query,
        history=[],
        classifier_mode="model_first_with_rule_guard",
        required_signals=["qa", "needs_clarification"],
        required_rule_ids=[],
        rule_expectations={"intent.qa.domain": False, "challenge.disagree": False},
        dependency_signals=dict(DEP_AMBIG),
        main_intent="qa",
        mod=modifiers(needs_clarification=True),
        complexity="simple",
        shape="single_question",
        context_dependency="ambiguous",
        route="direct",
        mode="clarify",
        notes="原始 query 信息不足，预填为模糊 QA 草稿",
        history_template=history_variant,
        generation_mode="positive",
        risk_flags=risk_flags,
        source_query_id=source_query_id,
    )


def _follow_up_variant(source_query_id: str, query: str, history_variant: str) -> dict[str, Any]:
    if history_variant == "supportive":
        return sample(
            sid=f"{source_query_id}_follow_up_supportive",
            batch="follow_up",
            query=query,
            history=list(HISTORY_TEMPLATES["follow_up"]["supportive"]),
            classifier_mode="rule_plus_model",
            required_signals=["follow_up"],
            required_rule_ids=["context.follow_up.reference"],
            rule_expectations={"context.follow_up.reference": True, "challenge.disagree": False},
            dependency_signals=dict(DEP_HISTORY),
            main_intent="qa",
            mod=modifiers(follow_up=True),
            complexity="simple",
            shape="single_question",
            context_dependency="history_reference",
            route="rag",
            mode="normal",
            notes="原始 query 配强相关历史，验证有效追问召回",
            history_template=history_variant,
            generation_mode="positive",
            risk_flags=[],
            source_query_id=source_query_id,
        )
    if history_variant == "weak":
        return sample(
            sid=f"{source_query_id}_follow_up_weak",
            batch="follow_up",
            query=query,
            history=[],
            classifier_mode="rule_plus_model",
            required_signals=["needs_clarification"],
            required_rule_ids=["context.follow_up.missing_history"],
            rule_expectations={"context.follow_up.reference": False, "context.follow_up.missing_history": True},
            dependency_signals=dict(DEP_AMBIG),
            main_intent="chat",
            mod=modifiers(needs_clarification=True),
            complexity="simple",
            shape="none",
            context_dependency="ambiguous",
            route="direct",
            mode="clarify",
            notes="原始 query 缺少历史，重点测误判成 follow_up 的风险",
            history_template=history_variant,
            generation_mode="positive",
            risk_flags=["INPUT_TOO_WEAK", "HISTORY_SUPPORT_UNCLEAR"],
            source_query_id=source_query_id,
        )
    return sample(
        sid=f"{source_query_id}_follow_up_conflicting",
        batch="follow_up",
        query=query,
        history=list(HISTORY_TEMPLATES["follow_up"]["conflicting"]),
        classifier_mode="rule_plus_model",
        required_signals=["follow_up", "needs_clarification"],
        required_rule_ids=["context.follow_up.reference"],
        rule_expectations={"context.follow_up.reference": True, "challenge.disagree": False},
        dependency_signals={
            "none": False,
            "history_reference": True,
            "previous_answer": False,
            "previous_retrieval": False,
            "ambiguous": True,
        },
        main_intent="qa",
        mod=modifiers(follow_up=True, needs_clarification=True),
        complexity="simple",
        shape="single_question",
        context_dependency="history_reference",
        route="direct",
        mode="clarify",
        notes="原始 query 配冲突历史，测试系统是否会因为存在历史而强行关联",
        history_template=history_variant,
        generation_mode="positive",
        risk_flags=["HISTORY_SUPPORT_UNCLEAR"],
        source_query_id=source_query_id,
    )


def _challenge_variant(source_query_id: str, query: str, history_variant: str) -> dict[str, Any]:
    if history_variant == "supportive":
        return sample(
            sid=f"{source_query_id}_challenge_supportive",
            batch="challenge",
            query=query,
            history=list(HISTORY_TEMPLATES["challenge"]["supportive"]),
            classifier_mode="rule_only",
            required_signals=["challenge"],
            required_rule_ids=["challenge.disagree"],
            rule_expectations={"challenge.disagree": True, "source.ask_basis": False},
            dependency_signals=dict(DEP_PREV_ANSWER),
            main_intent="qa",
            mod=modifiers(challenge=True),
            complexity="simple",
            shape="verify",
            context_dependency="previous_answer",
            route="rag",
            mode="challenge",
            notes="原始 query 配回答历史，验证标准 challenge 路由",
            history_template=history_variant,
            generation_mode="positive",
            risk_flags=[],
            source_query_id=source_query_id,
        )
    return sample(
        sid=f"{source_query_id}_challenge_weak",
        batch="challenge",
        query=query,
        history=list(HISTORY_TEMPLATES["challenge"]["weak"]),
        classifier_mode="rule_plus_model",
        required_signals=["needs_clarification"],
        required_rule_ids=[],
        rule_expectations={"challenge.disagree": False, "source.ask_basis": False},
        dependency_signals=dict(DEP_AMBIG),
        main_intent="chat",
        mod=modifiers(needs_clarification=True),
        complexity="simple",
        shape="none",
        context_dependency="ambiguous",
        route="direct",
        mode="clarify",
        notes="看起来像 challenge，但历史不足以支撑验证流",
        history_template=history_variant,
        generation_mode="positive",
        risk_flags=["HISTORY_SUPPORT_UNCLEAR"],
        source_query_id=source_query_id,
    )


def _meta_variant(source_query_id: str, query: str, history_variant: str) -> dict[str, Any]:
    if _looks_like_ask_source(query):
        return sample(
            sid=f"{source_query_id}_meta_{history_variant}",
            batch="meta",
            query=query,
            history=list(HISTORY_TEMPLATES["meta"].get(history_variant, HISTORY_TEMPLATES["meta"]["supportive"])),
            classifier_mode="rule_plus_model",
            required_signals=["ask_source"],
            required_rule_ids=["source.ask_basis"],
            rule_expectations={"source.ask_basis": True, "challenge.disagree": False},
            dependency_signals=dict(DEP_PREV_ANSWER if history_variant == "supportive" else DEP_AMBIG),
            main_intent="qa",
            mod=modifiers(ask_source=True, needs_clarification=history_variant != "supportive"),
            complexity="simple",
            shape="single_question",
            context_dependency="previous_answer" if history_variant == "supportive" else "ambiguous",
            route="rag" if history_variant == "supportive" else "direct",
            mode="normal" if history_variant == "supportive" else "clarify",
            notes="原始 query 作为 ask_source 草稿",
            history_template=history_variant,
            generation_mode="positive",
            risk_flags=([] if history_variant == "supportive" else ["HISTORY_SUPPORT_UNCLEAR"]),
            source_query_id=source_query_id,
        )
    return sample(
        sid=f"{source_query_id}_meta_{history_variant}",
        batch="meta",
        query=query,
        history=[],
        classifier_mode="rule_only",
        required_signals=["system", "ask_capability"],
        required_rule_ids=["system.capability.ask"],
        rule_expectations={"system.capability.ask": True, "intent.qa.domain": False},
        dependency_signals=dict(DEP_NONE),
        main_intent="system",
        mod=modifiers(ask_capability=True),
        complexity="simple",
        shape="none",
        context_dependency="none",
        route="direct",
        mode="capability",
        notes="原始 query 作为系统能力草稿",
        history_template=history_variant,
        generation_mode="positive",
        risk_flags=[],
        source_query_id=source_query_id,
    )


def _long_case_variant(source_query_id: str, query: str) -> dict[str, Any]:
    return sample(
        sid=f"{source_query_id}_long_case_supportive",
        batch="long_case_complex",
        query=query,
        history=[],
        classifier_mode="model_first_with_rule_guard",
        required_signals=["qa", "complex"],
        required_rule_ids=[],
        rule_expectations={"intent.qa.domain": False, "task.complex.request": False},
        dependency_signals=dict(DEP_NONE),
        main_intent="qa",
        mod=modifiers(),
        complexity="complex",
        shape="verify",
        context_dependency="none",
        route="agent",
        mode="normal",
        notes="长事实链样本，默认视为复杂分析",
        history_template="supportive",
        generation_mode="positive",
        risk_flags=["CONTROL_ROUTE_COST_RISK"],
        source_query_id=source_query_id,
    )


def _build_near_miss_variant(source_query_id: str, query: str, batch: str) -> dict[str, Any] | None:
    if batch == "follow_up":
        transformed = _transform_follow_up_to_near_miss(query)
        return sample(
            sid=f"{source_query_id}_follow_up_near_miss",
            batch="follow_up",
            query=transformed,
            history=[],
            classifier_mode="rule_plus_model",
            required_signals=["needs_clarification"],
            required_rule_ids=[],
            rule_expectations={"context.follow_up.reference": False, "context.follow_up.missing_history": False},
            dependency_signals=dict(DEP_AMBIG),
            main_intent="chat",
            mod=modifiers(needs_clarification=True),
            complexity="simple",
            shape="none",
            context_dependency="ambiguous",
            route="direct",
            mode="clarify",
            notes="近邻负例：看起来像追问，实际更像请求解释",
            history_template="weak",
            generation_mode="near_miss",
            risk_flags=["INPUT_TOO_WEAK", "HISTORY_SUPPORT_UNCLEAR"],
            source_query_id=source_query_id,
        )
    if batch == "challenge":
        transformed = _transform_challenge_to_near_miss(query)
        return sample(
            sid=f"{source_query_id}_challenge_near_miss",
            batch="challenge",
            query=transformed,
            history=list(HISTORY_TEMPLATES["challenge"]["weak"]),
            classifier_mode="rule_plus_model",
            required_signals=["needs_clarification"],
            required_rule_ids=[],
            rule_expectations={"challenge.disagree": False, "source.ask_basis": False},
            dependency_signals=dict(DEP_AMBIG),
            main_intent="chat",
            mod=modifiers(needs_clarification=True),
            complexity="simple",
            shape="none",
            context_dependency="ambiguous",
            route="direct",
            mode="clarify",
            notes="近邻负例：看起来像质疑，实际更像没听清",
            history_template="weak",
            generation_mode="near_miss",
            risk_flags=["HISTORY_SUPPORT_UNCLEAR"],
            source_query_id=source_query_id,
        )
    if batch == "meta" and _looks_like_ask_source(query):
        transformed = query.replace("依据", "解释").replace("出处", "意思")
        return sample(
            sid=f"{source_query_id}_meta_near_miss",
            batch="meta",
            query=transformed,
            history=list(HISTORY_TEMPLATES["meta"]["weak"]),
            classifier_mode="rule_plus_model",
            required_signals=["needs_clarification"],
            required_rule_ids=[],
            rule_expectations={"source.ask_basis": False, "challenge.disagree": False},
            dependency_signals=dict(DEP_AMBIG),
            main_intent="chat",
            mod=modifiers(needs_clarification=True),
            complexity="simple",
            shape="none",
            context_dependency="ambiguous",
            route="direct",
            mode="clarify",
            notes="近邻负例：从 ask_source 偏到说明请求",
            history_template="weak",
            generation_mode="near_miss",
            risk_flags=["INPUT_TOO_WEAK"],
            source_query_id=source_query_id,
        )
    return None


def _build_mixed_variant(source_query_id: str, query: str, batch: str) -> dict[str, Any] | None:
    if batch == "challenge":
        transformed = f"{query.rstrip('？?。')}，依据是哪条？"
        return sample(
            sid=f"{source_query_id}_challenge_mixed",
            batch="challenge",
            query=transformed,
            history=list(HISTORY_TEMPLATES["challenge"]["supportive"]),
            classifier_mode="rule_plus_model",
            required_signals=["challenge", "ask_source"],
            required_rule_ids=["challenge.disagree", "source.ask_basis"],
            rule_expectations={"challenge.disagree": True, "source.ask_basis": True},
            dependency_signals=dict(DEP_PREV_ANSWER),
            main_intent="qa",
            mod=modifiers(challenge=True, ask_source=True),
            complexity="simple",
            shape="verify",
            context_dependency="previous_answer",
            route="rag",
            mode="challenge",
            notes="混合变体：challenge 与 ask_source 叠加",
            history_template="supportive",
            generation_mode="mixed",
            risk_flags=[],
            source_query_id=source_query_id,
        )
    if batch == "follow_up":
        transformed = f"{query.rstrip('？?。')}，如果不是的话为什么？"
        return sample(
            sid=f"{source_query_id}_follow_up_mixed",
            batch="follow_up",
            query=transformed,
            history=list(HISTORY_TEMPLATES["follow_up"]["supportive"]),
            classifier_mode="rule_plus_model",
            required_signals=["follow_up", "multi_question"],
            required_rule_ids=["context.follow_up.reference", "task.enumerated_questions"],
            rule_expectations={"context.follow_up.reference": True, "task.enumerated_questions": True},
            dependency_signals=dict(DEP_HISTORY),
            main_intent="qa",
            mod=modifiers(follow_up=True),
            complexity="compound",
            shape="multi_question",
            context_dependency="history_reference",
            route="rag",
            mode="normal",
            notes="混合变体：追问叠加双问题",
            history_template="supportive",
            generation_mode="mixed",
            risk_flags=[],
            source_query_id=source_query_id,
        )
    return None


def _build_cost_focused_variant(source_query_id: str, query: str, batch: str) -> dict[str, Any] | None:
    if batch in {"standard_qa", "fuzzy_qa"}:
        transformed = (
            f"我想先确认一个定义问题：{query}"
            "。背景情况很多，但核心只是确认这个概念本身怎么定义。"
        )
        return sample(
            sid=f"{source_query_id}_{batch}_cost_focused",
            batch=batch,
            query=transformed,
            history=[],
            classifier_mode="model_first_with_rule_guard",
            required_signals=["qa"],
            required_rule_ids=[],
            rule_expectations={"intent.qa.domain": False},
            dependency_signals=dict(DEP_NONE),
            main_intent="qa",
            mod=modifiers(),
            complexity="simple",
            shape="single_question",
            context_dependency="none",
            route="rag",
            mode="normal",
            notes="成本偏差样本：表面长，核心仍是简单定义问答，容易被误送到 agent。",
            history_template="supportive",
            generation_mode="cost_focused",
            risk_flags=["CONTROL_ROUTE_COST_RISK"],
            source_query_id=source_query_id,
        )
    if batch in {"mixed_intent", "long_case_complex"}:
        transformed = f"{query} 请按步骤整理关键事实、争议点和判断依据。"
        return sample(
            sid=f"{source_query_id}_{batch}_cost_focused",
            batch=batch,
            query=transformed,
            history=[],
            classifier_mode="model_first_with_rule_guard",
            required_signals=["qa", "complex"],
            required_rule_ids=[],
            rule_expectations={"intent.qa.domain": False},
            dependency_signals=dict(DEP_NONE),
            main_intent="qa",
            mod=modifiers(),
            complexity="complex",
            shape="mixed",
            context_dependency="none",
            route="agent",
            mode="normal",
            notes="成本偏差样本：表面仍像问答，但隐含多步整理任务，容易被误送到 rag。",
            history_template="supportive",
            generation_mode="cost_focused",
            risk_flags=["CONTROL_ROUTE_COST_RISK"],
            source_query_id=source_query_id,
        )
    return None


def _transform_follow_up_to_near_miss(query: str) -> str:
    if query.startswith(("那", "如果", "这")):
        return "你能再解释一下刚才那个意思吗？"
    return f"{query.rstrip('？?。')}，你能再解释一下吗？"


def _transform_challenge_to_near_miss(query: str) -> str:
    if "不对" in query or "确定" in query:
        return "我没太听懂，你能再说清楚一点吗？"
    return f"{query.rstrip('？?。')}，你能换个说法解释一下吗？"


def _looks_like_follow_up(text: str) -> bool:
    return bool(re.search(r"^(那|如果|要是|这种|这个|刚才|前面|上面)", text))


def _looks_like_challenge(text: str) -> bool:
    return bool(re.search(r"你确定|不对吧|搞错|说反|站不住|不一样", text))


def _looks_like_ask_source(text: str) -> bool:
    return bool(re.search(r"依据|出处|哪条|法条|来源|证据", text))


def _looks_like_mixed(text: str) -> bool:
    return (_looks_like_challenge(text) and _looks_like_ask_source(text)) or ("还是" in text and "？" in text)


def _looks_like_fuzzy_qa(text: str) -> bool:
    return bool(re.search(r"算不算|合理吗|会怎么判|可以长期|要赔钱吗|会被拘留吗|属于侵权吗", text))


def _looks_like_long_case(text: str) -> bool:
    return len(text) >= 60 or text.count("，") >= 3


def _looks_like_chat(text: str) -> bool:
    return bool(re.search(r"聊聊|哈哈|你是谁|推荐一本书|压力有点大|天气不错", text))


def _build_challenge_vs_clarify_twins() -> list[dict[str, Any]]:
    pairs = [
        (
            "你刚才这个结论不太对吧？",
            "你刚才这个结论我没太听懂。",
        ),
        (
            "这和你前面说的不一致吧？",
            "这和你前面说的是一个意思吗？",
        ),
        (
            "你是不是把条件搞反了？",
            "你是不是把条件说得太快了？",
        ),
        (
            "这个说法站不住吧？",
            "这个说法能不能再展开一点？",
        ),
    ]
    rows: list[dict[str, Any]] = []
    for index, (challenge_query, clarify_query) in enumerate(pairs, start=1):
        source = f"twins_challenge_{index:03d}"
        rows.append(_challenge_variant(source, challenge_query, "supportive"))
        rows.append(
            sample(
                sid=f"{source}_clarify_twin",
                batch="challenge",
                query=clarify_query,
                history=list(HISTORY_TEMPLATES["challenge"]["supportive"]),
                classifier_mode="rule_plus_model",
                required_signals=["needs_clarification"],
                required_rule_ids=[],
                rule_expectations={"challenge.disagree": False, "source.ask_basis": False},
                dependency_signals=dict(DEP_AMBIG),
                main_intent="chat",
                mod=modifiers(needs_clarification=True),
                complexity="simple",
                shape="none",
                context_dependency="ambiguous",
                route="direct",
                mode="clarify",
                notes="Twin pair: challenge wording versus clarify wording under the same prior answer.",
                history_template="supportive",
                generation_mode="near_miss",
                risk_flags=["INPUT_TOO_WEAK", "HISTORY_SUPPORT_UNCLEAR"],
                source_query_id=source,
            )
        )
    return rows


def _build_follow_up_vs_ambiguous_twins() -> list[dict[str, Any]]:
    pairs = [
        (
            "那如果是未成年人呢？",
            "那这个呢？",
        ),
        (
            "那如果没有证据呢？",
            "那这个标准呢？",
        ),
        (
            "如果换成公司主体呢？",
            "如果换一种情况呢？",
        ),
        (
            "那法院一般怎么处理？",
            "那上面那个情况呢？",
        ),
    ]
    rows: list[dict[str, Any]] = []
    for index, (follow_up_query, ambiguous_query) in enumerate(pairs, start=1):
        source = f"twins_follow_up_{index:03d}"
        rows.append(_follow_up_variant(source, follow_up_query, "supportive"))
        rows.append(
            sample(
                sid=f"{source}_ambiguous_twin",
                batch="follow_up",
                query=ambiguous_query,
                history=list(HISTORY_TEMPLATES["follow_up"]["weak"]),
                classifier_mode="rule_plus_model",
                required_signals=["needs_clarification"],
                required_rule_ids=["context.follow_up.missing_history"],
                rule_expectations={"context.follow_up.reference": False, "context.follow_up.missing_history": True},
                dependency_signals=dict(DEP_AMBIG),
                main_intent="chat",
                mod=modifiers(needs_clarification=True),
                complexity="simple",
                shape="none",
                context_dependency="ambiguous",
                route="direct",
                mode="clarify",
                notes="Twin pair: valid follow-up versus vague referential phrase with insufficient grounding.",
                history_template="weak",
                generation_mode="near_miss",
                risk_flags=["INPUT_TOO_WEAK", "HISTORY_SUPPORT_UNCLEAR"],
                source_query_id=source,
            )
        )
    return rows


def _build_qa_vs_system_twins() -> list[dict[str, Any]]:
    pairs = [
        (
            "告诉我怎么查社保缴费记录。",
            "告诉我你现在接的是哪个知识库版本。",
        ),
        (
            "怎么查最新司法解释？",
            "你能查到最新司法解释吗？",
        ),
        (
            "怎么查看医保报销比例？",
            "你支持查看哪些医保数据源？",
        ),
        (
            "怎么判断合同条款是否有效？",
            "你是根据哪个版本的民法典回答的？",
        ),
    ]
    rows: list[dict[str, Any]] = []
    for index, (qa_query, system_query) in enumerate(pairs, start=1):
        source = f"twins_qa_system_{index:03d}"
        rows.append(
            sample(
                sid=f"{source}_qa_twin",
                batch="standard_qa",
                query=qa_query,
                history=[],
                classifier_mode="rule_plus_model",
                required_signals=["qa"],
                required_rule_ids=[],
                rule_expectations={"intent.qa.domain": True, "system.capability.ask": False},
                dependency_signals=dict(DEP_NONE),
                main_intent="qa",
                mod=modifiers(),
                complexity="simple",
                shape="single_question",
                context_dependency="none",
                route="rag",
                mode="normal",
                notes="Twin pair: user asks how to perform a business lookup within the domain.",
                history_template="supportive",
                generation_mode="near_miss",
                risk_flags=[],
                source_query_id=source,
            )
        )
        rows.append(
            sample(
                sid=f"{source}_system_twin",
                batch="meta",
                query=system_query,
                history=[],
                classifier_mode="rule_only",
                required_signals=["system", "ask_capability"],
                required_rule_ids=["system.capability.ask"],
                rule_expectations={"intent.qa.domain": False, "system.capability.ask": True},
                dependency_signals=dict(DEP_NONE),
                main_intent="system",
                mod=modifiers(ask_capability=True),
                complexity="simple",
                shape="none",
                context_dependency="none",
                route="direct",
                mode="capability",
                notes="Twin pair: wording stays close to business QA, but intent shifts to system capability or provenance.",
                history_template="supportive",
                generation_mode="near_miss",
                risk_flags=[],
                source_query_id=source,
            )
        )
    return rows


def _build_follow_up_near_miss_rows() -> list[dict[str, Any]]:
    supportive_queries = [
        "那如果是未成年人呢？",
        "那公司作为另一方也一样吗？",
        "那如果没有证据呢？",
        "这种情况赔多少？",
        "那法院一般怎么处理？",
        "如果是医疗场景也照这个规则吗？",
        "那换成刑事责任呢？",
        "这个标准全国都一样吗？",
        "如果对方是平台呢？",
        "那严重一点会怎样？",
    ]
    weak_queries = [
        "那这个呢？",
        "这种呢？",
        "那上面那个情况呢？",
        "如果换一种情况呢？",
        "这也算吗？",
        "这种也一样？",
        "那这个标准呢？",
        "如果是另一边呢？",
    ]
    conflicting_queries = [
        "那如果是公司呢？",
        "这种情况也一样吗？",
        "那这个还能这么看吗？",
        "如果没证据也照这个来吗？",
        "这种情形也支持吗？",
        "那另一种主体也一样？",
        "这个规则也能套吗？",
    ]

    rows: list[dict[str, Any]] = []
    for index, query in enumerate(supportive_queries, start=1):
        rows.append(_follow_up_variant(f"campaign_follow_up_{index:03d}", query, "supportive"))
    for index, query in enumerate(weak_queries, start=1):
        rows.append(_follow_up_variant(f"campaign_follow_up_weak_{index:03d}", query, "weak"))
    for index, query in enumerate(conflicting_queries, start=1):
        rows.append(_follow_up_variant(f"campaign_follow_up_conflicting_{index:03d}", query, "conflicting"))
    return rows


def _build_challenge_near_miss_rows() -> list[dict[str, Any]]:
    supportive_queries = [
        "你刚才这个说法不对吧？",
        "你确定这个结论没问题吗？",
        "我觉得你这里理解错了。",
        "这和我查到的规则不一致吧？",
        "你是不是把条件说反了？",
        "这个结论明显太绝对了吧？",
        "你刚才是不是漏掉了限制条件？",
        "这个说法站不住吧？",
        "你这里是不是搞错了？",
        "这应该不能这么概括吧？",
    ]
    weak_queries = [
        "我没太听懂，是这个意思吗？",
        "你这个能再解释一下吗？",
        "我有点疑惑，这里怎么理解？",
        "这个我还没跟上。",
        "这里是不是我理解慢了？",
        "你能换个说法吗？",
        "这个我还是不太明白。",
        "能展开一点吗？",
    ]
    mixed_queries = [
        "你刚才这个结论不太对吧，依据是哪条？",
        "我查到的不一样，你这个出处是什么？",
        "你是不是说错了？有法条吗？",
        "这个说法站不住吧，证据在哪里？",
        "你这里理解偏了吧，依据是什么？",
        "这个结论太武断了，来源能给一下吗？",
        "你刚才是不是搞错了？按哪条说的？",
    ]

    rows: list[dict[str, Any]] = []
    for index, query in enumerate(supportive_queries, start=1):
        rows.append(_challenge_variant(f"campaign_challenge_{index:03d}", query, "supportive"))
    for index, query in enumerate(weak_queries, start=1):
        rows.append(_challenge_variant(f"campaign_challenge_weak_{index:03d}", query, "weak"))
    for index, query in enumerate(mixed_queries, start=1):
        rows.append(
            sample(
                sid=f"campaign_challenge_mixed_{index:03d}",
                batch="challenge",
                query=query,
                history=list(HISTORY_TEMPLATES["challenge"]["supportive"]),
                classifier_mode="rule_plus_model",
                required_signals=["challenge", "ask_source"],
                required_rule_ids=["challenge.disagree", "source.ask_basis"],
                rule_expectations={"challenge.disagree": True, "source.ask_basis": True},
                dependency_signals=dict(DEP_PREV_ANSWER),
                main_intent="qa",
                mod=modifiers(challenge=True, ask_source=True),
                complexity="simple",
                shape="verify",
                context_dependency="previous_answer",
                route="rag",
                mode="challenge",
                notes="challenge 与 ask_source 混合",
                history_template="supportive",
                generation_mode="mixed",
                risk_flags=[],
                source_query_id=f"campaign_challenge_mixed_{index:03d}",
            )
        )
    return rows


def main() -> int:
    args = parse_args()
    if args.profile == "empty":
        generate_empty_dataset(args.output_dir, args.batches)
        return 0
    if args.profile == "v1_adversarial_campaign":
        generate_v1_adversarial_campaign(args.output_dir)
        return 0
    if args.profile == "twins_campaign_v2":
        generate_twins_campaign_v2(args.output_dir)
        return 0
    if args.input_file is None:
        raise ValueError("--input-file is required when profile is from_query_list")
    generate_from_query_list(
        output_dir=args.output_dir,
        input_file=args.input_file,
        generation_modes=args.generation_modes,
        history_variants=args.history_variants,
        sample_limit=args.sample_limit,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
