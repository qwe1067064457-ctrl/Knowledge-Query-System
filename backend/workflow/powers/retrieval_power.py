from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from knowledge_retrieval.hybrid_retriever import hybrid_retriever
from workflow.types import EvidenceBundle, EvidenceItem, QueryUnit, RetrievalQualityAssessment


_METRIC_SCORE = {"good": 1.0, "weak": 0.5, "bad": 0.0}
_WEIGHTS = {
    "target_overlap_score": 0.25,
    "coverage_score": 0.25,
    "dedup_hit_score": 0.20,
    "hit_count_score": 0.15,
    "non_empty_snippet_score": 0.10,
    "source_quality_score": 0.05,
}


@dataclass(frozen=True)
class RetrievalQuery:
    text: str
    target_refs: tuple[str, ...] = ()
    path_filters: tuple[str, ...] = ()
    query_hints: tuple[str, ...] = ()
    source_types: tuple[str, ...] = ()
    top_k: int = 4
    mode: str = "raw"


class RetrievalPower:
    def __init__(self, retriever: Any | None = None) -> None:
        self.retriever = retriever or hybrid_retriever

    def build_raw_query(self, text: str, *, top_k: int = 4) -> RetrievalQuery:
        return RetrievalQuery(text=text.strip(), top_k=top_k, mode="raw")

    def build_bound_query(
        self,
        text: str,
        *,
        binding_result: dict[str, Any],
        top_k: int = 4,
    ) -> RetrievalQuery:
        target_refs = tuple(
            str(item.get("object_id") or item.get("content") or "")
            for item in binding_result.get("bound_targets", ())
            if item
        )
        hints = tuple(str(item.get("content") or item.get("object_id") or "") for item in binding_result.get("bound_targets", ()))
        joined_hints = " ".join(hint for hint in hints if hint).strip()
        query_text = text.strip() if not joined_hints else f"{text.strip()} {joined_hints}".strip()
        return RetrievalQuery(
            text=query_text,
            target_refs=target_refs,
            query_hints=hints,
            top_k=top_k,
            mode="bound",
        )

    def retrieve(
        self,
        query_units: tuple[QueryUnit, ...],
        *,
        top_k: int = 4,
    ) -> EvidenceBundle:
        unit_results: list[dict[str, Any]] = []
        merged: dict[tuple[str, str], EvidenceItem] = {}
        source_refs: list[str] = []
        quality_scores: list[float] = []

        for unit in query_units:
            result = self.retriever.retrieve(unit.text, top_k=top_k)
            evidences = [*result.vector_evidences, *result.bm25_evidences]
            evidence_items = [
                EvidenceItem(
                    evidence_id=f"{index}:{item.source_path}:{item.locator}",
                    source_path=item.source_path,
                    source_type=item.source_type,
                    locator=item.locator,
                    snippet=item.snippet,
                    channel=item.channel,
                    score=item.score,
                    query_unit_ids=(unit.unit_id,),
                    parent_id=item.parent_id,
                )
                for index, item in enumerate(evidences, start=1)
            ]
            quality = self.assess_retrieval_quality(
                evidence_items,
                target_refs=unit.target_refs,
                target_top_k=top_k,
            )
            quality_scores.append(quality.weighted_score)

            for evidence in evidence_items:
                dedup_key = (evidence.source_path, evidence.locator)
                if dedup_key not in merged:
                    merged[dedup_key] = evidence
                else:
                    existing = merged[dedup_key]
                    merged[dedup_key] = EvidenceItem(
                        evidence_id=existing.evidence_id,
                        source_path=existing.source_path,
                        source_type=existing.source_type,
                        locator=existing.locator,
                        snippet=existing.snippet,
                        channel=existing.channel,
                        score=max(existing.score or 0.0, evidence.score or 0.0),
                        query_unit_ids=tuple(dict.fromkeys((*existing.query_unit_ids, *evidence.query_unit_ids))),
                        parent_id=existing.parent_id,
                    )
                if evidence.source_path not in source_refs:
                    source_refs.append(evidence.source_path)

            unit_results.append(
                {
                    "unit_id": unit.unit_id,
                    "query": unit.text,
                    "origin": unit.origin,
                    "quality": quality.to_dict(),
                    "evidence_count": len(evidence_items),
                }
            )

        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        quality_summary = {
            "average_weighted_score": round(avg_quality, 4),
            "query_units": len(query_units),
        }
        return EvidenceBundle(
            query_unit_results=tuple(unit_results),
            merged_evidence_items=tuple(merged.values()),
            source_refs=tuple(source_refs),
            coverage_summary={"query_units": len(query_units), "sources": len(source_refs)},
            quality_summary=quality_summary,
            missing_evidence_notes=() if avg_quality >= 0.45 else ("retrieval_quality_weak",),
        )

    def assess_retrieval_quality(
        self,
        evidence_items: list[EvidenceItem],
        *,
        target_refs: tuple[str, ...] = (),
        target_top_k: int = 4,
    ) -> RetrievalQualityAssessment:
        raw_hit_count = len(evidence_items)
        dedup_hit_count = len({(item.source_path, item.locator) for item in evidence_items})
        non_empty_ratio = (
            sum(1 for item in evidence_items if item.snippet.strip()) / raw_hit_count
            if raw_hit_count
            else 0.0
        )
        target_overlap_ratio = self._compute_target_overlap(evidence_items, target_refs)
        coverage_ratio = 1.0 if not target_refs else target_overlap_ratio
        source_quality_ratio = self._compute_source_quality_ratio(evidence_items)

        metrics = {
            "hit_count_score": self._ratio_to_bucket(raw_hit_count / max(1, target_top_k), floor_bad=0.3, floor_good=0.6, absolute_bad=0, absolute_weak=1, absolute_value=raw_hit_count),
            "dedup_hit_score": self._ratio_to_bucket(dedup_hit_count / max(1, target_top_k), floor_bad=0.2, floor_good=0.4, absolute_bad=1, absolute_weak=1, absolute_value=dedup_hit_count),
            "target_overlap_score": self._generic_bucket(target_overlap_ratio, good_floor=0.8, weak_floor=0.4),
            "coverage_score": self._generic_bucket(coverage_ratio, good_floor=1.0, weak_floor=0.5, exact_good=True),
            "non_empty_snippet_score": self._generic_bucket(non_empty_ratio, good_floor=0.8, weak_floor=0.5),
            "source_quality_score": self._generic_bucket(source_quality_ratio, good_floor=0.6, weak_floor=0.3),
        }

        weighted_score = round(
            sum(_WEIGHTS[name] * _METRIC_SCORE[value] for name, value in metrics.items()),
            4,
        )
        status = "good" if weighted_score >= 0.75 else "weak" if weighted_score >= 0.45 else "bad"
        should_repair = (
            metrics["target_overlap_score"] == "bad"
            or metrics["coverage_score"] == "bad"
            or weighted_score < 0.45
        )
        return RetrievalQualityAssessment(
            weighted_score=weighted_score,
            status=status,
            should_repair=should_repair,
            **metrics,
        )

    def _compute_target_overlap(self, evidence_items: list[EvidenceItem], target_refs: tuple[str, ...]) -> float:
        if not target_refs:
            return 1.0
        normalized_targets = [target.lower() for target in target_refs if target]
        if not normalized_targets:
            return 1.0
        matched = 0
        for target in normalized_targets:
            if any(target in f"{item.source_path} {item.snippet}".lower() for item in evidence_items):
                matched += 1
        return matched / len(normalized_targets)

    def _compute_source_quality_ratio(self, evidence_items: list[EvidenceItem]) -> float:
        if not evidence_items:
            return 0.0
        score = 0.0
        for item in evidence_items:
            source = item.source_type.lower()
            if "official" in source or "structured" in source:
                score += 1.0
            elif "curated" in source or "case" in source:
                score += 0.75
            elif "raw" in source or "extract" in source:
                score += 0.5
            else:
                score += 0.25
        return score / len(evidence_items)

    def _ratio_to_bucket(
        self,
        ratio: float,
        *,
        floor_bad: float,
        floor_good: float,
        absolute_bad: int,
        absolute_weak: int,
        absolute_value: int,
    ) -> str:
        if absolute_value <= absolute_bad:
            return "bad"
        if absolute_value <= absolute_weak:
            return "weak"
        return self._generic_bucket(ratio, good_floor=floor_good, weak_floor=floor_bad)

    def _generic_bucket(self, ratio: float, *, good_floor: float, weak_floor: float, exact_good: bool = False) -> str:
        if exact_good:
            if math.isclose(ratio, good_floor) or ratio >= good_floor:
                return "good"
        elif ratio >= good_floor:
            return "good"
        if ratio >= weak_floor:
            return "weak"
        return "bad"
