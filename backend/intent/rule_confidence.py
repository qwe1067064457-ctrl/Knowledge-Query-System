from __future__ import annotations

from collections import defaultdict

from intent.types import ContextSignals, ContextState, RuleConfidence, RuleMatch, SignalConfidence, Strength


LEVEL_THRESHOLDS = {
    "high": 0.85,
    "medium": 0.6,
}

CONFLICT_PENALTIES: dict[str, dict[str, float]] = {
    "qa": {"chat": 0.2, "system": 0.15, "unsupported": 0.2},
    "chat": {"qa": 0.2, "system": 0.15, "unsupported": 0.2},
    "system": {"qa": 0.15, "chat": 0.15},
    "follow_up": {"needs_context_check": 0.1},
    "challenge": {"needs_context_check": 0.2},
    "soft_doubt": {"needs_context_check": 0.1},
    "ask_source": {"needs_context_check": 0.1},
}


def calculate_rule_confidence(
    *,
    matched_rules: tuple[RuleMatch, ...],
    raw_signals: tuple[str, ...],
    context_state: ContextState,
    dependency_signals: dict[str, bool] | ContextSignals,
) -> RuleConfidence:
    grouped: dict[str, list[RuleMatch]] = defaultdict(list)
    for match in matched_rules:
        grouped[match.signal].append(match)

    signal_confidences: list[SignalConfidence] = []
    active_signals = set(raw_signals)

    for signal, rules in grouped.items():
        scores = [rule.score for rule in rules]
        base_score = max(scores) if scores else 0.0
        support_bonus = _support_bonus(len(rules))
        conflict_penalty = _conflict_penalty(signal, active_signals)
        context_adjustment = _context_adjustment(signal, rules, context_state, dependency_signals)
        final_score = _clamp_score(base_score + support_bonus - conflict_penalty + context_adjustment)
        signal_confidences.append(
            SignalConfidence(
                signal=signal,
                base_score=round(base_score, 4),
                support_bonus=round(support_bonus, 4),
                conflict_penalty=round(conflict_penalty, 4),
                context_adjustment=round(context_adjustment, 4),
                final_score=round(final_score, 4),
                level=_level_for_score(final_score),
                supporting_rule_ids=tuple(rule.rule_id for rule in rules),
            )
        )

    signal_confidences.sort(key=lambda item: (-item.final_score, item.signal))
    if signal_confidences:
        top = signal_confidences[0]
        explanation = tuple(_build_explanations(signal_confidences))
        return RuleConfidence(
            signal_confidences=tuple(signal_confidences),
            final_signal=top.signal,
            final_score=top.final_score,
            final_level=top.level,
            explanation=explanation,
        )
    return RuleConfidence(explanation=("No matched rules available for rule-based confidence.",))


def _support_bonus(rule_count: int) -> float:
    if rule_count <= 1:
        return 0.0
    return min(0.05 * (rule_count - 1), 0.1)


def _conflict_penalty(signal: str, active_signals: set[str]) -> float:
    penalties = CONFLICT_PENALTIES.get(signal, {})
    total = 0.0
    for conflicting_signal, penalty in penalties.items():
        if conflicting_signal in active_signals:
            total += penalty
    return total


def _context_adjustment(
    signal: str,
    rules: list[RuleMatch],
    context_state: ContextState,
    dependency_signals: dict[str, bool] | ContextSignals,
) -> float:
    if signal == "challenge":
        only_soft_doubt = bool(rules) and all(rule.rule_id == "challenge.soft_doubt" for rule in rules)
        if context_state.has_previous_answer:
            return 0.05 if only_soft_doubt else 0.1
        return -0.35 if only_soft_doubt else -0.3
    if signal == "soft_doubt":
        return 0.05 if context_state.has_previous_answer else -0.35
    if signal == "ask_source":
        if context_state.has_previous_answer:
            return 0.05
        if _context_flag(dependency_signals, "ambiguous"):
            return -0.2
        return 0.0
    if signal == "follow_up":
        if context_state.has_history:
            bonus = 0.05
            if context_state.last_main_intent == "qa" or _context_flag(dependency_signals, "history_reference"):
                bonus += 0.05
            return bonus
        return -0.2
    if signal == "needs_context_check":
        return 0.1 if _context_flag(dependency_signals, "ambiguous") else 0.0
    if signal == "qa":
        return 0.05 if context_state.last_main_intent == "qa" else 0.0
    return 0.0


def _context_flag(dependency_signals: dict[str, bool] | ContextSignals, key: str) -> bool:
    if isinstance(dependency_signals, dict):
        return bool(dependency_signals.get(key))

    alias_map = {
        "history_reference": dependency_signals.has_reference,
        "previous_answer": dependency_signals.previous_answer,
        "previous_retrieval": dependency_signals.previous_retrieval,
        "ambiguous": dependency_signals.ambiguous or dependency_signals.has_implicit_history,
        "none": dependency_signals.none,
    }
    return bool(alias_map.get(key, False))


def _level_for_score(score: float) -> Strength:
    if score >= LEVEL_THRESHOLDS["high"]:
        return "high"
    if score >= LEVEL_THRESHOLDS["medium"]:
        return "medium"
    return "low"


def _clamp_score(score: float) -> float:
    return max(0.0, min(score, 0.98))


def _build_explanations(signal_confidences: list[SignalConfidence]) -> list[str]:
    explanations: list[str] = []
    for item in signal_confidences:
        explanations.append(
            (
                f"signal={item.signal}; "
                f"rules=[{', '.join(item.supporting_rule_ids)}]; "
                f"[Final: {item.final_score:.2f}] = "
                f"Base({item.base_score:.2f}) + "
                f"Bonus({item.support_bonus:+.2f}) - "
                f"Conflict({item.conflict_penalty:.2f}) + "
                f"Context({item.context_adjustment:+.2f})"
            )
        )
    return explanations
