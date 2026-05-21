from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from knowledge_retrieval.hybrid_retriever import hybrid_retriever
from knowledge_retrieval.types import OrchestratedRetrievalResult
from workflow.helpers.retrieval_repair_helper import RetrievalRepairHelper
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
    def __init__(self, retriever: Any | None = None, repair_helper: RetrievalRepairHelper | None = None) -> None:
        self.retriever = retriever or hybrid_retriever
        self.repair_helper = repair_helper or RetrievalRepairHelper()

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
            initial_run = self._run_single_query(unit=unit, query_text=unit.text, top_k=top_k)
            evidence_items = initial_run["evidence_items"]
            quality = initial_run["quality"]
            selected_query = initial_run["query_text"]
            selected_mode = initial_run["mode"]
            pre_quality = quality.to_dict()
            repair_plan = self.repair_helper.build_repair_plan(
                query_unit=unit,
                quality=quality,
                current_mode="raw" if unit.origin == "primary" else unit.origin,
            )
            repair_applied = False
            repaired_query: str | None = None
            repaired_mode: str | None = None
            post_quality = pre_quality

            if repair_plan.get("enabled"):
                repaired_query = str(repair_plan.get("next_query_text") or unit.text)
                repaired_mode = str(repair_plan.get("next_mode") or selected_mode)
                repaired_run = self._run_single_query(
                    unit=unit,
                    query_text=repaired_query,
                    top_k=int(repair_plan.get("top_k") or top_k),
                    mode=repaired_mode,
                )
                post_quality = repaired_run["quality"].to_dict()
                if self._should_use_repaired_run(initial_run=initial_run, repaired_run=repaired_run):
                    evidence_items = repaired_run["evidence_items"]
                    quality = repaired_run["quality"]
                    selected_query = repaired_run["query_text"]
                    selected_mode = repaired_run["mode"]
                    repair_applied = True

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
                    "repair_plan": repair_plan,
                    "repair_applied": repair_applied,
                    "repair_strategy": repair_plan.get("strategy", "none"),
                    "selected_query": selected_query,
                    "selected_mode": selected_mode,
                    "repaired_query": repaired_query,
                    "repaired_mode": repaired_mode,
                    "pre_quality": pre_quality,
                    "post_quality": post_quality,
                }
            )

        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        quality_summary = {
            "average_weighted_score": round(avg_quality, 4),
            "status": "good" if avg_quality >= 0.75 else "weak" if avg_quality >= 0.45 else "bad",
            "query_units": len(query_units),
            "merged_evidence_count": len(merged),
            "source_ref_count": len(source_refs),
            "repairable_units": sum(
                1 for item in unit_results if item.get("repair_plan", {}).get("enabled")
            ),
            "repaired_units": sum(1 for item in unit_results if item.get("repair_applied")),
            "repair_strategies": [item.get("repair_strategy", "none") for item in unit_results],
        }
        return EvidenceBundle(
            query_unit_results=tuple(unit_results),
            merged_evidence_items=tuple(merged.values()),
            source_refs=tuple(source_refs),
            coverage_summary={"query_units": len(query_units), "sources": len(source_refs)},
            quality_summary=quality_summary,
            missing_evidence_notes=() if avg_quality >= 0.45 else ("retrieval_quality_weak",),
        )

    def build_bundle_from_orchestrated_result(
        self,
        result: OrchestratedRetrievalResult,
        *,
        query: str,
    ) -> EvidenceBundle:
        query_unit = QueryUnit(unit_id="primary", text=query, origin="primary")
        evidence_items = [
            EvidenceItem(
                evidence_id=f"{index}:{item.source_path}:{item.locator}",
                source_path=item.source_path,
                source_type=item.source_type,
                locator=item.locator,
                snippet=item.snippet,
                channel=item.channel,
                score=item.score,
                query_unit_ids=(query_unit.unit_id,),
                parent_id=item.parent_id,
            )
            for index, item in enumerate(result.evidences, start=1)
        ]
        quality = self.assess_retrieval_quality(evidence_items, target_top_k=max(1, len(evidence_items)))
        source_refs = tuple(dict.fromkeys(item.source_path for item in evidence_items))
        return EvidenceBundle(
            query_unit_results=(
                {
                    "unit_id": query_unit.unit_id,
                    "query": query,
                    "origin": query_unit.origin,
                    "quality": quality.to_dict(),
                    "evidence_count": len(evidence_items),
                    "retrieval_status": result.status,
                    "fallback_used": result.fallback_used,
                    "repair_plan": self.repair_helper.build_repair_plan(
                    query_unit=query_unit,
                    quality=quality,
                    current_mode="raw" if query_unit.origin == "primary" else query_unit.origin,
                ),
                    "repair_applied": False,
                    "repair_strategy": self.repair_helper.build_repair_plan(
                        query_unit=query_unit,
                        quality=quality,
                        current_mode="raw" if query_unit.origin == "primary" else query_unit.origin,
                    ).get("strategy", "none"),
                    "selected_query": query,
                    "selected_mode": "raw",
                    "repaired_query": None,
                    "repaired_mode": None,
                    "pre_quality": quality.to_dict(),
                    "post_quality": quality.to_dict(),
                },
            ),
            merged_evidence_items=tuple(evidence_items),
            source_refs=source_refs,
            coverage_summary={
                "query_units": 1,
                "sources": len(source_refs),
                "retrieval_status": result.status,
            },
            quality_summary={
                "average_weighted_score": quality.weighted_score,
                "status": quality.status,
                "fallback_used": result.fallback_used,
                "merged_evidence_count": len(evidence_items),
                "source_ref_count": len(source_refs),
                "repairable_units": 1
                if self.repair_helper.build_repair_plan(
                    query_unit=query_unit,
                    quality=quality,
                    current_mode="raw" if query_unit.origin == "primary" else query_unit.origin,
                ).get("enabled")
                else 0,
                "repaired_units": 0,
                "repair_strategies": [
                    self.repair_helper.build_repair_plan(
                        query_unit=query_unit,
                        quality=quality,
                        current_mode="raw" if query_unit.origin == "primary" else query_unit.origin,
                    ).get("strategy", "none")
                ],
            },
            missing_evidence_notes=() if result.status == "success" else (result.reason or "knowledge_retrieval_incomplete",),
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

    def _run_single_query(
        self,
        *,
        unit: QueryUnit,
        query_text: str,
        top_k: int,
        mode: str = "raw",
    ) -> dict[str, Any]:
        result = self.retriever.retrieve(query_text, top_k=top_k)
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
        return {
            "query_text": query_text,
            "mode": mode,
            "evidence_items": evidence_items,
            "quality": quality,
        }

    def _should_use_repaired_run(self, *, initial_run: dict[str, Any], repaired_run: dict[str, Any]) -> bool:
        initial_quality: RetrievalQualityAssessment = initial_run["quality"]
        repaired_quality: RetrievalQualityAssessment = repaired_run["quality"]
        if repaired_quality.weighted_score > initial_quality.weighted_score:
            return True
        if repaired_quality.status == "good" and initial_quality.status != "good":
            return True
        if repaired_quality.status == initial_quality.status and len(repaired_run["evidence_items"]) > len(initial_run["evidence_items"]):
            return True
        return False

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
