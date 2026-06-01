from __future__ import annotations

import re
from typing import Any

from workflow.helpers.challenge_review_helper import (
    build_challenge_answer_constraints,
    summarize_challenge_findings,
)
from workflow.types import EvidenceAssessmentResult, EvidenceBundle, EvidenceRefCandidate, ReviewEvaluationResult


class ReviewWorker:
    _SOURCE_TYPE_QUALITY = {
        "official_structured": "high",
        "official_unstructured": "medium_high",
        "community": "medium",
        "unknown": "low",
    }
    _CHANNEL_QUALITY = {
        "vector": "medium_high",
        "keyword": "medium",
        "bm25": "medium",
        "memory": "medium",
        "unknown": "low",
    }
    _QUALITY_RANK = {
        "unknown": -1,
        "low": 0,
        "medium": 1,
        "medium_high": 2,
        "high": 3,
    }

    def retrieval_quality_check(
        self,
        *,
        evidence_bundle: EvidenceBundle | None,
    ) -> dict[str, Any]:
        if evidence_bundle is None:
            return {
                "status": "not_applicable",
                "should_repair": False,
                "average_weighted_score": 0.0,
                "repairable_units": 0,
                "repaired_units": 0,
                "missing_evidence": False,
                "source_ref_count": 0,
                "merged_evidence_count": 0,
            }
        summary = evidence_bundle.summary_obj()
        quality_view = evidence_bundle.summary_view()
        return {
            "status": str(summary.get("retrieval_quality_status", "unknown")),
            "should_repair": bool(summary.get("repairable_units", 0)),
            "average_weighted_score": float(summary.get("average_weighted_score", 0.0) or 0.0),
            "repairable_units": int(summary.get("repairable_units", 0) or 0),
            "repaired_units": int(summary.get("repaired_units", 0) or 0),
            "missing_evidence": bool(summary.get("missing_evidence", False)),
            "source_ref_count": quality_view.source_ref_count,
            "merged_evidence_count": quality_view.merged_evidence_count,
        }

    def evidence_check(
        self,
        *,
        query: str,
        targets: list[dict[str, Any]],
        evidence_candidates: list[EvidenceRefCandidate | dict[str, Any]],
    ) -> EvidenceAssessmentResult:
        normalized_evidence = self._normalize_evidence_candidates(evidence_candidates)
        evidence_refs = self._collect_evidence_refs(normalized_evidence)
        matched_targets = 0
        per_target_assessment = []
        per_target_support_counts = []
        total_target_refs = 0
        total_matched_refs = 0
        for target in targets:
            explicit_target_refs = {str(ref) for ref in target.get("refs", ()) if ref}
            target_refs = self._target_refs(target)
            target_id = str(target.get("object_id") or target.get("content") or f"target_{len(per_target_assessment) + 1}")
            matched_refs = sorted(target_refs & evidence_refs) if target_refs else []
            related_evidence_refs = self._related_evidence_refs(
                query=query,
                target=target,
                evidence_candidates=normalized_evidence,
            )
            matched = False
            matched_by = "none"
            coverage_status = "missing"
            if target_refs:
                if matched_refs:
                    matched_targets += 1
                    matched = True
                    matched_by = "ref_overlap"
                    coverage_status = "supported"
            elif evidence_candidates:
                if related_evidence_refs:
                    matched_targets += 1
                    matched = True
                    matched_refs = list(related_evidence_refs)
                    matched_by = "text_alignment"
                    coverage_status = "supported"
                else:
                    matched_refs = sorted(evidence_refs)

            if not explicit_target_refs and not matched and evidence_candidates and related_evidence_refs:
                matched_targets += 1
                matched = True
                matched_refs = list(related_evidence_refs)
                matched_by = "text_alignment"
                coverage_status = "supported"

            if not matched and related_evidence_refs:
                matched_by = "text_related_only"
                coverage_status = "related_only"

            per_target_assessment.append(
                {
                    "target_ref": target_id,
                    "target_refs": sorted(target_refs),
                    "matched": matched,
                    "matched_by": matched_by,
                    "coverage_status": coverage_status,
                    "matched_evidence_refs": matched_refs,
                    "related_evidence_refs": list(related_evidence_refs),
                }
            )
            per_target_support_counts.append(
                {
                    "target_ref": target_id,
                    "support_count": len(matched_refs),
                    "matched_evidence_refs": matched_refs,
                    "related_evidence_refs": list(related_evidence_refs),
                }
            )
            total_target_refs += len(target_refs)
            total_matched_refs += len(matched_refs)

        sufficient = bool(targets) and matched_targets == len(targets)
        partially_sufficient = bool(targets) and 0 < matched_targets < len(targets)
        matched_target_refs = [
            str(item.get("target_ref"))
            for item in per_target_assessment
            if item.get("matched")
        ]
        unsupported_target_refs = [
            str(item.get("target_ref"))
            for item in per_target_assessment
            if not item.get("matched")
        ]
        has_related_only_targets = any(
            item.get("coverage_status") == "related_only"
            for item in per_target_assessment
        )
        target_coverage = (matched_targets / len(targets)) if targets else 0.0
        missing_target_ratio = (len(unsupported_target_refs) / len(targets)) if targets else 0.0
        target_evidence_ref_overlap = (total_matched_refs / total_target_refs) if total_target_refs else 0.0
        source_count = len(normalized_evidence)
        source_diversity = len(
            {
                (
                    evidence.get("source_type") or "unknown",
                    evidence.get("channel") or "unknown",
                )
                for evidence in normalized_evidence
            }
        )
        return EvidenceAssessmentResult(
            sufficient=sufficient,
            partially_sufficient=partially_sufficient,
            used_existing_evidence=bool(normalized_evidence),
            triggered_additional_retrieval=not sufficient,
            matched_target_count=matched_targets,
            target_count=len(targets),
            coverage_ratio=target_coverage,
            supporting_evidence_refs=tuple(sorted(evidence_refs)),
            matched_target_refs=tuple(matched_target_refs),
            unsupported_target_refs=tuple(unsupported_target_refs),
            needs_more_evidence_targets=tuple(unsupported_target_refs),
            retrieve_if_needed={
                "needed": bool(targets) and matched_targets < len(targets),
                "target_refs": unsupported_target_refs,
                "reason": (
                    "related_evidence_not_grounded"
                    if unsupported_target_refs and has_related_only_targets
                    else "insufficient_target_coverage"
                    if unsupported_target_refs
                    else "not_needed"
                ),
            },
            per_target_assessment=tuple(per_target_assessment),
            per_target_support_counts=tuple(per_target_support_counts),
            evidence_notes=self._build_evidence_notes(
                sufficient=sufficient,
                has_related_only_targets=has_related_only_targets,
            ),
            target_coverage=target_coverage,
            target_evidence_ref_overlap=target_evidence_ref_overlap,
            missing_target_ratio=missing_target_ratio,
            source_count=source_count,
            source_diversity=source_diversity,
            source_type_quality_band=self._derive_source_type_quality_band(normalized_evidence),
            channel_quality_band=self._derive_channel_quality_band(normalized_evidence),
        )

    def challenge_re_evaluate(
        self,
        *,
        query: str,
        targets: list[dict[str, Any]],
        evidence_assessment: EvidenceAssessmentResult | dict[str, Any],
        evidence_candidates: list[EvidenceRefCandidate | dict[str, Any]],
    ) -> ReviewEvaluationResult:
        assessment_result = (
            evidence_assessment
            if isinstance(evidence_assessment, EvidenceAssessmentResult)
            else EvidenceAssessmentResult.from_dict(evidence_assessment)
        )
        findings = summarize_challenge_findings(
            targets=targets,
            evidence_assessment=assessment_result,
        )
        sufficient = assessment_result.sufficient
        partially_sufficient = assessment_result.partially_sufficient
        status = "success" if sufficient else "partial_success" if partially_sufficient else "insufficient_evidence"
        return ReviewEvaluationResult(
            status=status,
            review_findings=tuple(findings),
            answer_constraints=build_challenge_answer_constraints(
                evidence_assessment=assessment_result,
                sufficient=sufficient,
            ),
        )

    def re_evaluate(
        self,
        *,
        query: str,
        targets: list[dict[str, Any]],
        evidence_assessment: EvidenceAssessmentResult | dict[str, Any],
        evidence_candidates: list[EvidenceRefCandidate | dict[str, Any]],
    ) -> ReviewEvaluationResult:
        return self.challenge_re_evaluate(
            query=query,
            targets=targets,
            evidence_assessment=evidence_assessment,
            evidence_candidates=evidence_candidates,
        )

    def _normalize_evidence_candidates(
        self,
        evidence_candidates: list[EvidenceRefCandidate | dict[str, Any]],
    ) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for evidence in evidence_candidates:
            if isinstance(evidence, EvidenceRefCandidate):
                normalized.append(evidence.to_dict())
            else:
                normalized.append(dict(evidence))
        return normalized

    def _collect_evidence_refs(self, evidence_candidates: list[dict[str, Any]]) -> set[str]:
        refs: set[str] = set()
        for evidence in evidence_candidates:
            object_id = evidence.get("object_id")
            if object_id:
                refs.add(str(object_id))
            for ref in evidence.get("refs", ()):
                refs.add(str(ref))
        return refs

    def _target_refs(self, target: dict[str, Any]) -> set[str]:
        refs: set[str] = set()
        object_id = target.get("object_id")
        if object_id:
            refs.add(str(object_id))
        for ref in target.get("refs", ()):
            refs.add(str(ref))
        return refs

    def _derive_source_type_quality_band(self, evidence_candidates: list[dict[str, Any]]) -> str:
        return self._aggregate_quality_band(
            [self._SOURCE_TYPE_QUALITY.get(str(item.get("source_type") or "unknown"), "low") for item in evidence_candidates]
        )

    def _derive_channel_quality_band(self, evidence_candidates: list[dict[str, Any]]) -> str:
        return self._aggregate_quality_band(
            [self._CHANNEL_QUALITY.get(str(item.get("channel") or "unknown"), "low") for item in evidence_candidates]
        )

    def _aggregate_quality_band(self, bands: list[str]) -> str:
        if not bands:
            return "unknown"
        best = max(bands, key=lambda item: self._QUALITY_RANK.get(item, -1))
        return best

    def _related_evidence_refs(
        self,
        *,
        query: str,
        target: dict[str, Any],
        evidence_candidates: list[dict[str, Any]],
    ) -> tuple[str, ...]:
        target_text = self._target_text(target)
        if not target_text:
            return ()
        target_tokens = self._extract_alignment_tokens(f"{query} {target_text}")
        if len(target_tokens) < 2:
            return ()

        related_refs: list[str] = []
        for evidence in evidence_candidates:
            if not self._evidence_can_support_text_alignment(evidence):
                continue
            evidence_ref = str(evidence.get("object_id") or "").strip()
            if not evidence_ref:
                continue
            evidence_text = self._evidence_text(evidence)
            if not evidence_text:
                continue
            overlap = [token for token in target_tokens if token in evidence_text]
            if len(set(overlap)) >= 2:
                related_refs.append(evidence_ref)
        return tuple(sorted(dict.fromkeys(related_refs)))

    def _target_text(self, target: dict[str, Any]) -> str:
        structured = target.get("structured_payload")
        disputed_span = ""
        if isinstance(structured, dict):
            disputed_span = str(structured.get("disputed_span") or "").strip()
        return disputed_span or str(target.get("content") or "").strip()

    def _evidence_text(self, evidence: dict[str, Any]) -> str:
        return " ".join(
            part.strip()
            for part in (
                str(evidence.get("content") or ""),
                str(evidence.get("snippet") or ""),
            )
            if part and part.strip()
        )

    def _evidence_can_support_text_alignment(self, evidence: dict[str, Any]) -> bool:
        source_band = self._SOURCE_TYPE_QUALITY.get(str(evidence.get("source_type") or "unknown"), "low")
        channel_band = self._CHANNEL_QUALITY.get(str(evidence.get("channel") or "unknown"), "low")
        return (
            self._QUALITY_RANK.get(source_band, -1) >= self._QUALITY_RANK["medium_high"]
            or self._QUALITY_RANK.get(channel_band, -1) >= self._QUALITY_RANK["medium_high"]
        )

    def _extract_alignment_tokens(self, text: str) -> list[str]:
        raw_tokens = re.findall(r"[\u4e00-\u9fff]{2,6}|[A-Za-z0-9_]{3,}", text)
        seen: set[str] = set()
        ordered: list[str] = []
        for token in raw_tokens:
            value = token.strip()
            if not value or value in seen:
                continue
            seen.add(value)
            ordered.append(value)
        return ordered

    def _build_evidence_notes(
        self,
        *,
        sufficient: bool,
        has_related_only_targets: bool,
    ) -> tuple[str, ...]:
        if sufficient:
            return ()
        if has_related_only_targets:
            return ("existing_evidence_related_but_not_grounded",)
        return ("existing_evidence_not_enough",)
