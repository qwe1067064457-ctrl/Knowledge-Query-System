from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TOPOLOGY_EXPORT_PATH = ROOT / "evaluation" / "intent" / "exports" / "v2" / "intent_training_v2_topology_20260518.jsonl"
DEFAULT_AUTO_EXPORT_PATH = ROOT / "evaluation" / "intent" / "exports" / "v2" / "intent_training_v2_auto_20260518.jsonl"
DEFAULT_OUTPUT_DIR = ROOT / "evaluation" / "intent" / "v2_sft" / "backfill_20260519"
DEFAULT_BENCHMARK_OUTPUT_DIR = ROOT / "evaluation" / "intent" / "v2_sft" / "benchmark_backfill_20260519"
DEFAULT_PROTOTYPE_TARGETS = {"dev": 30, "calibration": 32, "heldout": 24}
DEFAULT_BENCHMARK_TARGETS = {"dev": 42, "calibration": 48, "heldout": 42}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a V2 sample-backfill pack for dev/calibration/heldout and review.")
    parser.add_argument("--profile", choices=("prototype", "benchmark"), default="prototype")
    parser.add_argument("--topology-export", type=Path, default=DEFAULT_TOPOLOGY_EXPORT_PATH)
    parser.add_argument("--auto-export", type=Path, default=DEFAULT_AUTO_EXPORT_PATH)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser.parse_args()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _context_flags(row: dict[str, Any]) -> list[str]:
    context_signals = row.get("evidence", {}).get("context_signals", {})
    mapping = {
        "history_reference": bool(context_signals.get("history_reference", False)),
        "needs_previous_answer": bool(
            context_signals.get("needs_previous_answer", False) or context_signals.get("previous_answer", False)
        ),
        "previous_retrieval": bool(context_signals.get("previous_retrieval", False)),
        "clarify_hint": bool(context_signals.get("clarify_hint", False) or context_signals.get("ambiguous", False)),
    }
    return [name for name, active in mapping.items() if active]


def _active_modifiers(row: dict[str, Any]) -> list[str]:
    modifiers = row.get("resolved", {}).get("modifiers", {})
    return [name for name, active in modifiers.items() if active]


def _row_signature(row: dict[str, Any]) -> dict[str, Any]:
    resolved = row.get("resolved", {})
    task = resolved.get("task", {})
    return {
        "main_intent": resolved.get("main_intent", "qa"),
        "task_complexity": task.get("complexity", "simple"),
        "task_shape": task.get("shape", "none"),
        "task_topology": task.get("topology", "single"),
        "modifiers": sorted(_active_modifiers(row)),
        "context": sorted(_context_flags(row)),
    }


def _diff_fields(topology_row: dict[str, Any], auto_row: dict[str, Any]) -> list[str]:
    topology_sig = _row_signature(topology_row)
    auto_sig = _row_signature(auto_row)
    changed: list[str] = []
    for field in ("main_intent", "task_complexity", "task_shape", "task_topology", "modifiers", "context"):
        if topology_sig[field] != auto_sig[field]:
            changed.append(field)
    return changed


def _build_row_record(topology_row: dict[str, Any], auto_row: dict[str, Any]) -> dict[str, Any]:
    metadata = topology_row.get("metadata", {})
    topology_sig = _row_signature(topology_row)
    auto_sig = _row_signature(auto_row)
    changed_fields = _diff_fields(topology_row, auto_row)
    return {
        "id": topology_row["id"],
        "text": topology_row.get("input", {}).get("user_query", ""),
        "current_split": topology_row.get("split", "train"),
        "source_dataset": metadata.get("source_dataset", ""),
        "label_tier": metadata.get("label_tier", topology_row.get("label_tier", "gold")),
        "topology_labels": topology_sig,
        "auto_labels": auto_sig,
        "changed_fields": changed_fields,
        "changed": bool(changed_fields),
        "modifier_count": len(topology_sig["modifiers"]),
        "context_count": len(topology_sig["context"]),
    }


def _prototype_quota_specs() -> dict[str, dict[str, dict[str, int]]]:
    return {
        "dev": {
            "main_intent": {"chat": 3, "system": 3, "unsupported": 3},
            "task_complexity": {"complex": 6, "compound": 2},
            "task_shape": {"verify": 5, "multi_question": 4, "compare": 3, "summarize": 3, "mixed": 2},
            "task_topology": {"parallel_queries": 4},
            "modifiers": {
                "follow_up": 2,
                "challenge": 2,
                "soft_doubt": 2,
                "ask_source": 2,
                "ask_capability": 2,
                "needs_clarification": 2,
                "out_of_scope": 2,
            },
            "context": {"needs_previous_answer": 5, "history_reference": 2, "clarify_hint": 2},
        },
        "calibration": {
            "task_complexity": {"complex": 4, "compound": 1},
            "task_shape": {"verify": 6, "multi_question": 4, "compare": 3},
            "modifiers": {
                "follow_up": 3,
                "challenge": 3,
                "soft_doubt": 3,
                "ask_source": 3,
                "ask_capability": 3,
                "needs_clarification": 3,
                "out_of_scope": 3,
            },
            "context": {"needs_previous_answer": 6, "history_reference": 3, "clarify_hint": 3},
        },
        "heldout": {
            "main_intent": {"chat": 2, "system": 2, "unsupported": 2},
            "task_complexity": {"complex": 4, "compound": 1},
            "task_shape": {"verify": 4, "multi_question": 3, "compare": 2, "summarize": 2, "mixed": 1},
            "task_topology": {"parallel_queries": 4},
        },
    }


def _benchmark_quota_specs() -> dict[str, dict[str, dict[str, int]]]:
    return {
        "dev": {
            "main_intent": {"chat": 4, "system": 4, "unsupported": 4},
            "task_complexity": {"complex": 8, "compound": 4},
            "task_shape": {"verify": 6, "multi_question": 5, "compare": 4, "summarize": 4, "mixed": 3},
            "task_topology": {"parallel_queries": 6, "staged": 2, "parallel_subtasks": 2},
            "modifiers": {
                "follow_up": 3,
                "challenge": 3,
                "soft_doubt": 3,
                "ask_source": 3,
                "ask_capability": 2,
                "needs_clarification": 3,
                "out_of_scope": 3,
            },
            "context": {"needs_previous_answer": 6, "history_reference": 3, "clarify_hint": 3},
        },
        "calibration": {
            "main_intent": {"chat": 3, "system": 3, "unsupported": 3},
            "task_complexity": {"complex": 8, "compound": 4},
            "task_shape": {"verify": 8, "multi_question": 6, "compare": 6, "summarize": 4, "mixed": 3},
            "task_topology": {"parallel_queries": 6, "staged": 2, "parallel_subtasks": 2},
            "modifiers": {
                "follow_up": 4,
                "challenge": 4,
                "soft_doubt": 4,
                "ask_source": 4,
                "ask_capability": 3,
                "needs_clarification": 4,
                "out_of_scope": 4,
            },
            "context": {"needs_previous_answer": 8, "history_reference": 4, "clarify_hint": 4},
        },
        "heldout": {
            "main_intent": {"chat": 3, "system": 3, "unsupported": 3},
            "task_complexity": {"complex": 6, "compound": 4},
            "task_shape": {"verify": 6, "multi_question": 5, "compare": 4, "summarize": 3, "mixed": 2},
            "task_topology": {"parallel_queries": 6, "staged": 2, "parallel_subtasks": 2},
            "modifiers": {
                "follow_up": 2,
                "challenge": 2,
                "soft_doubt": 3,
                "ask_source": 2,
                "needs_clarification": 2,
                "out_of_scope": 3,
            },
            "context": {"needs_previous_answer": 5, "history_reference": 2, "clarify_hint": 2},
        },
    }


def _profile_config(profile: str) -> dict[str, Any]:
    if profile == "benchmark":
        return {
            "task": "v2_benchmark_backfill",
            "title": "V2 Benchmark Backfill Pack 20260519",
            "targets": DEFAULT_BENCHMARK_TARGETS,
            "quotas": _benchmark_quota_specs(),
            "default_output_dir": DEFAULT_BENCHMARK_OUTPUT_DIR,
        }
    return {
        "task": "v2_sample_backfill",
        "title": "V2 Sample Backfill Pack 20260519",
        "targets": DEFAULT_PROTOTYPE_TARGETS,
        "quotas": _prototype_quota_specs(),
        "default_output_dir": DEFAULT_OUTPUT_DIR,
    }


def _current_counts(rows: list[dict[str, Any]]) -> dict[str, Counter]:
    counts = {
        "main_intent": Counter(),
        "task_complexity": Counter(),
        "task_shape": Counter(),
        "task_topology": Counter(),
        "modifiers": Counter(),
        "context": Counter(),
    }
    for row in rows:
        topology_labels = row["topology_labels"]
        counts["main_intent"].update([topology_labels["main_intent"]])
        counts["task_complexity"].update([topology_labels["task_complexity"]])
        counts["task_shape"].update([topology_labels["task_shape"]])
        counts["task_topology"].update([topology_labels["task_topology"]])
        counts["modifiers"].update(topology_labels["modifiers"])
        counts["context"].update(topology_labels["context"])
    return counts


def _score_row(
    row: dict[str, Any],
    counts: dict[str, Counter],
    quotas: dict[str, dict[str, int]],
    split_name: str,
    *,
    label_key: str = "topology_labels",
) -> tuple[float, str]:
    score = 0.0
    topology_labels = row[label_key]
    for feature_name, feature_quotas in quotas.items():
        if feature_name in {"main_intent", "task_complexity", "task_shape", "task_topology"}:
            value = topology_labels[feature_name]
            if counts[feature_name][value] < feature_quotas.get(value, 0):
                score += 10.0
        else:
            for value in topology_labels[feature_name]:
                if counts[feature_name][value] < feature_quotas.get(value, 0):
                    score += 10.0
    if row["changed"]:
        score += 2.5 if split_name != "heldout" else 1.5
    score += min(row["modifier_count"], 3) * 0.8
    score += min(row["context_count"], 3) * 0.8
    if topology_labels["task_complexity"] == "complex":
        score += 1.2
    if topology_labels["task_topology"] == "parallel_queries":
        score += 0.8
    return score, row["id"]


def _select_rows(
    split_name: str,
    base_rows: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    target_size: int,
    quotas: dict[str, dict[str, int]],
    *,
    label_key: str = "topology_labels",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    selected = list(base_rows)
    remaining = list(candidates)
    counts = _current_counts(selected)

    while len(selected) < target_size and remaining:
        scored = sorted(
            ((_score_row(row, counts, quotas, split_name, label_key=label_key), row) for row in remaining),
            key=lambda item: (-item[0][0], item[0][1]),
        )
        _, best_row = scored[0]
        selected.append(best_row)
        remaining = [row for row in remaining if row["id"] != best_row["id"]]
        counts = _current_counts(selected)

    return selected, remaining


def _entry_from_row(row: dict[str, Any], *, split: str, status: str, reason: str) -> dict[str, Any]:
    return {
        "id": row["id"],
        "split": split,
        "status": status,
        "source_dataset": row["source_dataset"],
        "label_tier": row["label_tier"],
        "current_split": row["current_split"],
        "changed": row["changed"],
        "changed_fields": row["changed_fields"],
        "reason": reason,
    }


def _coverage_gap(selected_rows: list[dict[str, Any]], quotas: dict[str, dict[str, int]], *, label_key: str = "topology_labels") -> dict[str, dict[str, int]]:
    counts = {
        "main_intent": Counter(),
        "task_complexity": Counter(),
        "task_shape": Counter(),
        "task_topology": Counter(),
        "modifiers": Counter(),
        "context": Counter(),
    }
    for row in selected_rows:
        labels = row[label_key]
        counts["main_intent"].update([labels["main_intent"]])
        counts["task_complexity"].update([labels["task_complexity"]])
        counts["task_shape"].update([labels["task_shape"]])
        counts["task_topology"].update([labels["task_topology"]])
        counts["modifiers"].update(labels["modifiers"])
        counts["context"].update(labels["context"])
    gaps: dict[str, dict[str, int]] = {}
    for feature_name, feature_quotas in quotas.items():
        missing: dict[str, int] = {}
        for label_name, target in feature_quotas.items():
            deficit = target - counts[feature_name][label_name]
            if deficit > 0:
                missing[label_name] = deficit
        if missing:
            gaps[feature_name] = missing
    return gaps


def _promotion_entry_from_row(row: dict[str, Any], *, split: str, priority: str, gap_features: list[str]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "proposed_split": split,
        "status": "pending_review_auto_promote",
        "priority": priority,
        "source_dataset": row["source_dataset"],
        "label_tier": row["label_tier"],
        "current_split": row["current_split"],
        "changed_fields": row["changed_fields"],
        "gap_features": gap_features,
        "topology_labels": row["topology_labels"],
        "proposed_labels": row["auto_labels"],
        "text": row["text"],
    }


def _match_gap_features(row: dict[str, Any], gaps: dict[str, dict[str, int]]) -> list[str]:
    labels = row["auto_labels"]
    matched: list[str] = []
    for feature_name, missing in gaps.items():
        if feature_name in {"main_intent", "task_complexity", "task_shape", "task_topology"}:
            value = labels[feature_name]
            if value in missing:
                matched.append(f"{feature_name}:{value}")
        else:
            for value in labels[feature_name]:
                if value in missing:
                    matched.append(f"{feature_name}:{value}")
    return matched


def _select_promotion_rows(
    split_name: str,
    candidates: list[dict[str, Any]],
    gap_quotas: dict[str, dict[str, int]],
    target_size: int,
) -> list[dict[str, Any]]:
    if not gap_quotas:
        return []

    selected: list[dict[str, Any]] = []
    remaining = list(candidates)
    while len(selected) < target_size and remaining:
        counts = _current_counts([{"topology_labels": row["proposed_labels"]} for row in selected])
        scored_rows: list[tuple[tuple[float, str], dict[str, Any], list[str]]] = []
        for row in remaining:
            matched = _match_gap_features(row, gap_quotas)
            if not matched:
                continue
            row_for_score = dict(row)
            score, row_id = _score_row(row_for_score, counts, gap_quotas, split_name, label_key="auto_labels")
            scored_rows.append(((score + len(matched) * 12.0, row_id), row, matched))
        if not scored_rows:
            break
        scored_rows.sort(key=lambda item: (-item[0][0], item[0][1]))
        _, best_row, matched = scored_rows[0]
        priority = "high" if any(feature.startswith("task_topology:") for feature in matched) else "medium"
        selected.append(_promotion_entry_from_row(best_row, split=split_name, priority=priority, gap_features=matched))
        remaining = [row for row in remaining if row["id"] != best_row["id"]]
    return selected


def _decrement_gap(gaps: dict[str, dict[str, int]], feature_name: str, label_name: str, amount: int = 1) -> None:
    feature_gaps = gaps.get(feature_name)
    if not feature_gaps:
        return
    if label_name not in feature_gaps:
        return
    remaining = feature_gaps[label_name] - amount
    if remaining > 0:
        feature_gaps[label_name] = remaining
    else:
        feature_gaps.pop(label_name, None)
    if not feature_gaps:
        gaps.pop(feature_name, None)


def _clone_gap_summary(gaps: dict[str, dict[str, dict[str, int]]]) -> dict[str, dict[str, dict[str, int]]]:
    return {
        split_name: {
            feature_name: dict(missing)
            for feature_name, missing in feature_gaps.items()
        }
        for split_name, feature_gaps in gaps.items()
    }


def _apply_promotion_entries_to_gaps(gaps: dict[str, dict[str, dict[str, int]]], promotion_entries: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, int]]]:
    remaining = _clone_gap_summary(gaps)
    for entry in promotion_entries:
        split_name = entry["proposed_split"]
        split_gaps = remaining.get(split_name, {})
        for feature in entry["gap_features"]:
            feature_name, label_name = feature.split(":", 1)
            _decrement_gap(split_gaps, feature_name, label_name)
    return remaining


def _synthetic_base_labels() -> dict[str, Any]:
    return {
        "main_intent": "qa",
        "task_complexity": "simple",
        "task_shape": "single_question",
        "task_topology": "single",
        "modifiers": [],
        "context": [],
    }


def _configure_synthetic_labels(feature_name: str, label_name: str) -> tuple[dict[str, Any], str, str]:
    labels = _synthetic_base_labels()
    template_kind = f"{feature_name}_{label_name}"
    if feature_name == "task_topology":
        if label_name == "staged":
            labels["task_complexity"] = "complex"
            labels["task_shape"] = "mixed"
            labels["task_topology"] = "staged"
            labels["modifiers"] = ["needs_clarification"]
            labels["context"] = ["clarify_hint"]
            text = "请先判断该场景是否属于越权处理，再分阶段列出需要核实的事实、适用规则和最终判断边界。"
        elif label_name == "parallel_subtasks":
            labels["task_complexity"] = "compound"
            labels["task_shape"] = "multi_question"
            labels["task_topology"] = "parallel_subtasks"
            text = "请把这件事拆成两个独立子任务分别处理：先确认数据同步是否合法，再单独说明审计留痕应补哪些字段。"
        else:
            labels["task_complexity"] = "compound"
            labels["task_shape"] = "multi_question"
            labels["task_topology"] = "parallel_queries"
            text = "请分别回答两个并列问题：一是接口越权风险怎么判断，二是日志保留策略通常要满足哪些要求。"
    elif feature_name == "task_shape":
        if label_name == "mixed":
            labels["task_complexity"] = "complex"
            labels["task_shape"] = "mixed"
            labels["task_topology"] = "staged"
            labels["modifiers"] = ["needs_clarification"]
            labels["context"] = ["clarify_hint"]
            text = "先帮我判断这个案例是否可能违规，再按步骤整理争议点、证据缺口和后续核查顺序。"
        elif label_name == "compare":
            labels["task_complexity"] = "complex"
            labels["task_shape"] = "compare"
            text = "请对比‘直接共享病历给外部模型’和‘只共享脱敏摘要’两种做法在合规风险上的差异。"
        elif label_name == "summarize":
            labels["task_shape"] = "summarize"
            text = "把这份关于检索审计、访问控制和留痕策略的要求压缩成一段简明总结。"
        elif label_name == "multi_question":
            labels["task_complexity"] = "compound"
            labels["task_shape"] = "multi_question"
            labels["task_topology"] = "parallel_queries"
            text = "我有两个问题：试用期上限怎么认定，和经济补偿的计算口径分别是什么？"
        else:
            text = "请单独回答这个定义性问题。"
    elif feature_name == "task_complexity":
        if label_name == "compound":
            labels["task_complexity"] = "compound"
            labels["task_shape"] = "multi_question"
            labels["task_topology"] = "parallel_subtasks"
            text = "请先确认是否构成超范围处理，再分别说明告知义务和审计整改两部分该怎么做。"
        else:
            labels["task_complexity"] = "complex"
            labels["task_shape"] = "compare"
            labels["task_topology"] = "staged"
            text = "这个案例牵涉事实认定、规则适用和整改建议三层，请按顺序拆开分析。"
    elif feature_name == "modifiers":
        labels["task_shape"] = "verify"
        labels["task_topology"] = "single"
        labels["context"] = ["needs_previous_answer"]
        if label_name == "challenge":
            labels["modifiers"] = ["challenge"]
            text = "你前面那个结论我不完全认同，能不能说明为什么不存在例外？"
        elif label_name == "soft_doubt":
            labels["modifiers"] = ["soft_doubt"]
            text = "我有点拿不准，你前面的判断会不会把证据层的不确定性压得太早？"
        elif label_name == "needs_clarification":
            labels["modifiers"] = ["needs_clarification"]
            labels["context"] = ["clarify_hint"]
            text = "你先别直接下结论，我这里的‘同步’是指内部镜像还是发给外部供应商，这种情况是不是要先澄清？"
        elif label_name == "ask_source":
            labels["modifiers"] = ["ask_source"]
            text = "这个判断依据是哪条规定，能给我具体来源吗？"
        else:
            labels["modifiers"] = [label_name]
            text = "请根据前文继续处理这个问题。"
    elif feature_name == "context":
        labels["task_shape"] = "verify"
        if label_name == "clarify_hint":
            labels["modifiers"] = ["needs_clarification"]
            labels["context"] = ["clarify_hint"]
            text = "我这里描述得不太清楚，你先别回答实体问题，先告诉我还缺哪个关键条件。"
        elif label_name == "history_reference":
            labels["context"] = ["history_reference"]
            text = "沿用我们刚才那套审计框架，继续看这个新场景还差哪些控制点。"
        else:
            labels["context"] = ["needs_previous_answer"]
            text = "按你上一条的结论继续推，如果系统实际上用了外部缓存，这会改变判断吗？"
    elif feature_name == "main_intent":
        labels["main_intent"] = label_name
        if label_name == "chat":
            labels["task_shape"] = "none"
            text = "这两天一直在补样本有点累，先别讲方案，陪我缓一缓。"
        elif label_name == "system":
            labels["task_shape"] = "single_question"
            text = "你现在支持把这一批 V2 训练样本导出成独立的 calibration 和 heldout 吗？"
        else:
            labels["task_shape"] = "none"
            labels["modifiers"] = ["out_of_scope"]
            labels["context"] = []
            text = "帮我直接登录外部生产系统并修改数据库里的权限配置。"
    else:
        text = "请处理这个补齐 benchmark 缺口的候选问题。"
    return labels, text, template_kind


def _generate_synthetic_entries(
    remaining_gaps: dict[str, dict[str, dict[str, int]]],
    *,
    task_name: str,
) -> list[dict[str, Any]]:
    synthetic_entries: list[dict[str, Any]] = []
    for split_name in ("heldout", "calibration", "dev"):
        split_gaps = remaining_gaps.get(split_name, {})
        for feature_name, missing in split_gaps.items():
            for label_name, deficit in missing.items():
                for index in range(deficit):
                    labels, text, template_kind = _configure_synthetic_labels(feature_name, label_name)
                    row_id = f"{task_name}_{split_name}_{feature_name}_{label_name}_{index + 1:02d}"
                    priority = "high" if feature_name in {"task_topology", "task_complexity"} else "medium"
                    synthetic_entries.append(
                        {
                            "id": row_id,
                            "proposed_split": split_name,
                            "status": "pending_review_synthetic",
                            "priority": priority,
                            "source_dataset": "synthetic_benchmark_backfill_20260519",
                            "label_tier": "synthetic",
                            "current_split": "synthetic",
                            "gap_features": [f"{feature_name}:{label_name}"],
                            "proposed_labels": labels,
                            "template_kind": template_kind,
                            "text": text,
                        }
                    )
    return synthetic_entries


def _review_entry_from_row(row: dict[str, Any], *, queue: str, priority: str, reason: str) -> dict[str, Any]:
    return {
        "id": row["id"],
        "queue": queue,
        "priority": priority,
        "source_dataset": row["source_dataset"],
        "label_tier": row["label_tier"],
        "current_split": row["current_split"],
        "topology_labels": row["topology_labels"],
        "auto_labels": row["auto_labels"],
        "changed": row["changed"],
        "changed_fields": row["changed_fields"],
        "reason": reason,
        "text": row["text"],
    }


def build_backfill_pack(topology_export_path: Path, auto_export_path: Path, *, profile: str = "prototype") -> dict[str, Any]:
    config = _profile_config(profile)
    topology_rows = {row["id"]: row for row in _read_jsonl(topology_export_path)}
    auto_rows = {row["id"]: row for row in _read_jsonl(auto_export_path)}
    records = [_build_row_record(topology_rows[row_id], auto_rows[row_id]) for row_id in sorted(topology_rows)]

    existing_dev = [row for row in records if row["current_split"] == "dev"]
    existing_heldout = [row for row in records if row["current_split"] == "heldout"]
    gold_train = [row for row in records if row["current_split"] == "train" and row["label_tier"] == "gold"]
    silver_changed_train = [row for row in records if row["current_split"] == "train" and row["label_tier"] == "silver" and row["changed"]]

    quotas = config["quotas"]
    targets = config["targets"]

    dev_rows, remaining_after_dev = _select_rows(
        "dev",
        existing_dev,
        gold_train,
        targets["dev"],
        quotas["dev"],
    )
    heldout_rows, remaining_after_heldout = _select_rows(
        "heldout",
        existing_heldout,
        remaining_after_dev,
        targets["heldout"],
        quotas["heldout"],
    )
    calibration_rows, remaining_gold = _select_rows(
        "calibration",
        [],
        remaining_after_heldout,
        targets["calibration"],
        quotas["calibration"],
    )

    split_entries: list[dict[str, Any]] = []
    for row in dev_rows:
        split_entries.append(
            _entry_from_row(
                row,
                split="dev",
                status="legacy_seed" if row["current_split"] == "dev" else "pending_review_gold",
                reason="retain_existing_dev" if row["current_split"] == "dev" else "dev_backfill_gold",
            )
        )
    for row in calibration_rows:
        split_entries.append(
            _entry_from_row(
                row,
                split="calibration",
                status="pending_review_gold",
                reason="calibration_backfill_gold",
            )
        )
    for row in heldout_rows:
        split_entries.append(
            _entry_from_row(
                row,
                split="heldout",
                status="legacy_seed" if row["current_split"] == "heldout" else "pending_review_gold",
                reason="retain_existing_heldout" if row["current_split"] == "heldout" else "heldout_backfill_gold",
            )
        )

    review_rows: list[dict[str, Any]] = []
    for row in dev_rows:
        if row["current_split"] != "dev":
            review_rows.append(_review_entry_from_row(row, queue="eval_review", priority="high", reason="selected_for_dev"))
    for row in calibration_rows:
        review_rows.append(_review_entry_from_row(row, queue="eval_review", priority="high", reason="selected_for_calibration"))
    for row in heldout_rows:
        if row["current_split"] != "heldout":
            review_rows.append(_review_entry_from_row(row, queue="eval_review", priority="high", reason="selected_for_heldout"))

    weak_train_rows = sorted(
        silver_changed_train,
        key=lambda row: (
            "staged" not in {row["auto_labels"]["task_topology"], row["topology_labels"]["task_topology"]},
            "parallel_subtasks" not in {row["auto_labels"]["task_topology"], row["topology_labels"]["task_topology"]},
            -len(row["changed_fields"]),
            row["id"],
        ),
    )
    weak_train_entries = [
        _review_entry_from_row(
            row,
            queue="weak_train",
            priority="medium",
            reason="auto_changed_train_candidate",
        )
        for row in weak_train_rows
    ]

    promotion_entries: list[dict[str, Any]] = []
    gap_summary: dict[str, Any] = {}
    if profile == "benchmark":
        benchmark_gaps = {
            "dev": _coverage_gap(dev_rows, quotas["dev"]),
            "calibration": _coverage_gap(calibration_rows, quotas["calibration"]),
            "heldout": _coverage_gap(heldout_rows, quotas["heldout"]),
        }
        gap_summary = benchmark_gaps
        remaining_promotion_pool = list(weak_train_rows)
        for split_name in ("heldout", "calibration", "dev"):
            split_gaps = benchmark_gaps[split_name]
            selected = _select_promotion_rows(split_name, remaining_promotion_pool, split_gaps, target_size=12)
            promotion_entries.extend(selected)
            chosen_ids = {entry["id"] for entry in selected}
            remaining_promotion_pool = [row for row in remaining_promotion_pool if row["id"] not in chosen_ids]
    remaining_gap_after_promotion = _apply_promotion_entries_to_gaps(gap_summary, promotion_entries) if gap_summary else {}
    synthetic_entries = _generate_synthetic_entries(remaining_gap_after_promotion, task_name=config["task"]) if remaining_gap_after_promotion else []

    summary = {
        "version": "2026-05-19",
        "task": config["task"],
        "profile": profile,
        "targets": targets,
        "input_files": {
            "topology_export": str(topology_export_path),
            "auto_export": str(auto_export_path),
        },
        "source_snapshot": {
            "rows": len(records),
            "existing_dev": len(existing_dev),
            "existing_heldout": len(existing_heldout),
            "gold_train_pool": len(gold_train),
            "silver_changed_train_pool": len(silver_changed_train),
        },
        "proposed_splits": {
            "dev": len(dev_rows),
            "calibration": len(calibration_rows),
            "heldout": len(heldout_rows),
        },
        "review_queue": {
            "eval_review": len(review_rows),
            "weak_train": len(weak_train_entries),
        },
        "promotion_queue": len(promotion_entries),
        "synthetic_queue": len(synthetic_entries),
        "status_counts": Counter(entry["status"] for entry in split_entries),
    }
    if gap_summary:
        summary["gap_summary"] = gap_summary
        summary["remaining_gap_after_promotion"] = remaining_gap_after_promotion

    return {
        "split_manifest": {
            "version": "2026-05-19",
            "task": config["task"],
            "entries": split_entries,
        },
        "review_rows": review_rows,
        "weak_train_rows": weak_train_entries,
        "promotion_rows": promotion_entries,
        "synthetic_rows": synthetic_entries,
        "summary": summary,
        "title": config["title"],
        "profile": profile,
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""), encoding="utf-8")


def _build_readme(pack: dict[str, Any]) -> str:
    summary = pack["summary"]
    lines = [
        f"# {pack['title']}",
        "",
        "## 定位",
        "",
        "- 这是自动补样本产物，不是人工复核完成的正式 gold。",
        "- `split_manifest.json` 提供 `dev / calibration / heldout` 的候选分配。",
        "- `review_candidates.jsonl` 是评估样本 review 队列。",
        "- `weak_train_candidates.jsonl` 是可低权重混训的 auto 弱监督候选。",
        "- `promotion_candidates.jsonl` 是需要 review 后才能晋升到 benchmark split 的 auto 候选。",
        "- `synthetic_candidates.jsonl` 是为补齐剩余 benchmark 缺口自动生成的合成候选。",
        "",
        "## 当前摘要",
        "",
        "```json",
        json.dumps(summary, ensure_ascii=False, indent=2),
        "```",
        "",
        "## 使用建议",
        "",
        "- 先人工复核 `pending_review_gold`，再把通过样本正式冻结进 V2 split。",
        "- `weak_train_candidates.jsonl` 不直接升级为 reviewed gold。",
        "- `promotion_candidates.jsonl` 里的样本只有在复核通过并确认采用 `proposed_labels` 后，才可进入 benchmark split。",
        "- `synthetic_candidates.jsonl` 里的样本默认不进入训练，需要单独复核后再决定是否纳入 benchmark eval。",
        "- 训练侧若要先跑 prototype，可把 `split_manifest.json` 作为 provisional split override 使用。",
        "",
    ]
    return "\n".join(lines) + "\n"


def write_backfill_pack(output_dir: Path, pack: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "split_manifest.json").write_text(
        json.dumps(pack["split_manifest"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_jsonl(output_dir / "review_candidates.jsonl", pack["review_rows"])
    _write_jsonl(output_dir / "weak_train_candidates.jsonl", pack["weak_train_rows"])
    _write_jsonl(output_dir / "promotion_candidates.jsonl", pack.get("promotion_rows", []))
    _write_jsonl(output_dir / "synthetic_candidates.jsonl", pack.get("synthetic_rows", []))
    (output_dir / "summary.json").write_text(
        json.dumps(pack["summary"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "README.md").write_text(_build_readme(pack), encoding="utf-8")


def main() -> int:
    args = parse_args()
    pack = build_backfill_pack(args.topology_export, args.auto_export, profile=args.profile)
    output_dir = args.output_dir or _profile_config(args.profile)["default_output_dir"]
    write_backfill_pack(output_dir, pack)
    print(json.dumps({"output_dir": str(output_dir), "summary": pack["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
