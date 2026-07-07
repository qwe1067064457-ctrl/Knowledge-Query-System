from __future__ import annotations

from knowledge_retrieval.types import Evidence, HybridRetrievalResult
from knowledge_retrieval.types import OrchestratedRetrievalResult
from workflow.powers.retrieval_power import RetrievalPower
from workflow.types import QueryUnit, RetrievalUnitResult


class _FakeRetriever:
    def __init__(self, result: HybridRetrievalResult) -> None:
        self._result = result

    def retrieve(self, query: str, *, top_k: int = 4, path_filters=None, query_hints=None):
        del query_hints
        del path_filters
        return self._result


class _SequenceRetriever:
    def __init__(self, results: list[HybridRetrievalResult]) -> None:
        self._results = list(results)
        self.calls: list[tuple[str, int]] = []

    def retrieve(self, query: str, *, top_k: int = 4, path_filters=None, query_hints=None):
        del query_hints
        del path_filters
        self.calls.append((query, top_k))
        if len(self._results) == 1:
            return self._results[0]
        return self._results.pop(0)


class _CapturingRetriever:
    def __init__(self, result: HybridRetrievalResult) -> None:
        self._result = result
        self.calls: list[dict[str, object]] = []

    def retrieve(self, query: str, *, top_k: int = 4, path_filters=None, query_hints=None):
        self.calls.append(
            {
                "query": query,
                "top_k": top_k,
                "path_filters": list(path_filters or []),
                "query_hints": list(query_hints or []),
            }
        )
        return self._result


def test_retrieval_quality_good_when_target_covered() -> None:
    retriever = _FakeRetriever(
        HybridRetrievalResult(
            vector_evidences=[
                Evidence(
                    source_path="docs/law.md",
                    source_type="official_structured",
                    locator="p1",
                    snippet="劳动合同法第19条规定试用期。",
                    channel="vector",
                    score=0.9,
                )
            ],
            bm25_evidences=[],
        )
    )
    power = RetrievalPower(retriever=retriever)

    bundle = power.retrieve((QueryUnit(unit_id="q1", text="试用期依据", target_refs=("劳动合同法",)),), top_k=4)
    quality = bundle.query_unit_results[0]["quality"]
    payload = bundle.to_dict()

    assert quality["status"] in {"good", "weak"}
    assert quality["query_relevance_score"] != "bad"
    assert quality["target_overlap_score"] != "bad"
    assert bundle.source_refs == ("docs/law.md",)
    assert bundle.query_unit_results[0]["repair_strategy"] == "none"
    assert bundle.query_unit_results[0]["selected_mode"] == "raw"
    assert payload["evidence_summary"]["query_unit_count"] == 1
    assert payload["evidence_summary"]["merged_evidence_count"] == 1
    assert payload["evidence_summary"]["retrieval_quality_status"] in {"good", "weak"}
    assert payload["evidence_summary"]["missing_evidence"] is False


def test_retrieval_quality_bad_triggers_repair_signal_when_target_missing() -> None:
    retriever = _FakeRetriever(
        HybridRetrievalResult(
            vector_evidences=[
                Evidence(
                    source_path="docs/other.md",
                    source_type="raw_extracted",
                    locator="p2",
                    snippet="与目标无关的说明。",
                    channel="vector",
                    score=0.2,
                )
            ],
            bm25_evidences=[],
        )
    )
    power = RetrievalPower(retriever=retriever)

    bundle = power.retrieve((QueryUnit(unit_id="q1", text="试用期依据", target_refs=("劳动合同法",)),), top_k=4)
    quality = bundle.query_unit_results[0]["quality"]
    repair_plan = bundle.query_unit_results[0]["repair_plan"]
    payload = bundle.to_dict()

    assert quality["target_overlap_score"] == "bad"
    assert quality["query_relevance_score"] == "bad"
    assert quality["should_repair"] is True
    assert repair_plan["enabled"] is True
    assert repair_plan["strategy"] == "switch_to_bound_query"
    assert "retrieval_quality_weak" in bundle.missing_evidence_notes
    assert bundle.query_unit_results[0]["pre_quality"]["status"] == "bad"
    assert bundle.query_unit_results[0]["repaired_query"] is not None
    assert payload["evidence_summary"]["retrieval_quality_status"] == "bad"
    assert payload["evidence_summary"]["missing_evidence"] is True


def test_retrieval_quality_rejects_irrelevant_hits_even_without_target_refs() -> None:
    retriever = _FakeRetriever(
        HybridRetrievalResult(
            merged_hits=[
                Evidence(
                    source_path="docs/uc.md",
                    source_type="raw_extracted",
                    locator="p7",
                    snippet="美沙拉嗪用于溃疡性结肠炎的治疗与随访。",
                    channel="fused",
                    score=0.91,
                )
            ]
        )
    )
    power = RetrievalPower(retriever=retriever)

    bundle = power.retrieve((QueryUnit(unit_id="q1", text="TFA peptide ligation SARS-CoV-2 E protein nanobody"),), top_k=4)
    quality = bundle.query_unit_results[0]["quality"]

    assert quality["query_relevance_score"] == "bad"
    assert quality["status"] == "bad"
    assert quality["should_repair"] is True


def test_multi_query_units_keep_provenance() -> None:
    retriever = _FakeRetriever(
        HybridRetrievalResult(
            vector_evidences=[
                Evidence(
                    source_path="docs/common.md",
                    source_type="official_structured",
                    locator="p1",
                    snippet="共同证据",
                    channel="vector",
                    score=0.9,
                )
            ],
            bm25_evidences=[],
        )
    )
    power = RetrievalPower(retriever=retriever)

    bundle = power.retrieve(
        (
            QueryUnit(unit_id="q1", text="问题一"),
            QueryUnit(unit_id="q2", text="问题二"),
        ),
        top_k=4,
    )
    payload = bundle.to_dict()

    assert len(bundle.query_unit_results) == 2
    assert bundle.merged_evidence_items[0].query_unit_ids == ("q1", "q2")
    assert payload["evidence_summary"]["query_unit_count"] == 2
    assert payload["evidence_summary"]["source_ref_count"] == 1


def test_build_bundle_from_orchestrated_result_preserves_sources() -> None:
    power = RetrievalPower(retriever=_FakeRetriever(HybridRetrievalResult()))
    result = OrchestratedRetrievalResult(
        status="partial",
        evidences=[
            Evidence(
                source_path="docs/law.md",
                source_type="official_structured",
                locator="p1",
                snippet="劳动合同法第19条。",
                channel="fused",
                score=0.8,
            )
        ],
        fallback_used=True,
        reason="需要补充检索",
    )

    bundle = power.build_bundle_from_orchestrated_result(result, query="试用期依据")
    payload = bundle.to_dict()

    assert bundle.source_refs == ("docs/law.md",)
    assert bundle.query_unit_results[0]["retrieval_status"] == "partial"
    assert bundle.quality_summary["fallback_used"] is True
    assert payload["evidence_summary"]["retrieval_quality_status"] == bundle.quality_summary["status"]
    assert payload["evidence_summary"]["source_ref_count"] == 1


def test_retrieval_quality_good_has_no_repair_plan() -> None:
    retriever = _FakeRetriever(
        HybridRetrievalResult(
            vector_evidences=[
                Evidence(
                    source_path="docs/law.md",
                    source_type="official_structured",
                    locator="p1",
                    snippet="劳动合同法第19条规定试用期。",
                    channel="vector",
                    score=0.9,
                )
            ],
            bm25_evidences=[],
        )
    )
    power = RetrievalPower(retriever=retriever)

    bundle = power.retrieve((QueryUnit(unit_id="q1", text="试用期依据", target_refs=("劳动合同法",)),), top_k=1)
    payload = bundle.to_dict()

    assert bundle.query_unit_results[0]["repair_plan"]["enabled"] is False
    assert bundle.quality_summary["repaired_units"] == 0
    assert payload["evidence_summary"]["repaired_units"] == 0


def test_retrieval_power_executes_single_repair_when_quality_improves() -> None:
    retriever = _SequenceRetriever(
        [
            HybridRetrievalResult(
                vector_evidences=[
                    Evidence(
                        source_path="docs/other.md",
                        source_type="raw_extracted",
                        locator="p2",
                        snippet="与目标无关的说明。",
                        channel="vector",
                        score=0.2,
                    )
                ],
                bm25_evidences=[],
            ),
            HybridRetrievalResult(
                vector_evidences=[
                    Evidence(
                        source_path="docs/law.md",
                        source_type="official_structured",
                        locator="p1",
                        snippet="劳动合同法第19条规定试用期。",
                        channel="vector",
                        score=0.9,
                    )
                ],
                bm25_evidences=[],
            ),
        ]
    )
    power = RetrievalPower(retriever=retriever)

    bundle = power.retrieve((QueryUnit(unit_id="q1", text="试用期依据", target_refs=("劳动合同法",)),), top_k=4)
    payload = bundle.to_dict()

    assert len(retriever.calls) == 2
    assert bundle.query_unit_results[0]["repair_applied"] is True
    assert bundle.query_unit_results[0]["repair_strategy"] == "switch_to_bound_query"
    assert bundle.query_unit_results[0]["selected_mode"] == "bound"
    assert bundle.query_unit_results[0]["selected_query"].endswith("劳动合同法")
    assert bundle.query_unit_results[0]["post_quality"]["status"] in {"good", "weak"}
    assert bundle.source_refs == ("docs/law.md",)
    assert bundle.quality_summary["repaired_units"] == 1
    assert payload["evidence_summary"]["repaired_units"] == 1
    assert payload["evidence_summary"]["retrieval_quality_status"] in {"good", "weak"}
    unit_result = bundle.query_unit_result_objs()[0]
    assert unit_result.was_repaired() is True
    assert unit_result.repair_strategy_name() == "switch_to_bound_query"
    assert unit_result.selected_mode_name() == "bound"


def test_retrieval_power_returns_typed_query_unit_results() -> None:
    retriever = _FakeRetriever(
        HybridRetrievalResult(
            vector_evidences=[
                Evidence(
                    source_path="docs/law.md",
                    source_type="official_structured",
                    locator="p1",
                    snippet="劳动合同法第19条规定试用期。",
                    channel="vector",
                    score=0.9,
                )
            ],
            bm25_evidences=[],
        )
    )
    power = RetrievalPower(retriever=retriever)

    bundle = power.retrieve((QueryUnit(unit_id="q1", text="试用期依据", target_refs=("劳动合同法",)),), top_k=4)
    unit_result = bundle.query_unit_result_objs()[0]

    assert isinstance(unit_result, RetrievalUnitResult)
    assert unit_result.unit_id == "q1"
    assert unit_result.selected_mode_name() == "raw"
    assert unit_result.selected_query_text() == "试用期依据"
    assert unit_result.quality_status() in {"good", "weak"}
    assert unit_result.should_repair() is False
    assert unit_result.repair_strategy_name() == "none"
    assert unit_result.was_repaired() is False


def test_retrieval_power_forwards_path_filters_to_backend() -> None:
    retriever = _CapturingRetriever(
        HybridRetrievalResult(
            vector_evidences=[
                Evidence(
                    source_path="docs/medicine.md",
                    source_type="official_structured",
                    locator="p1",
                    snippet="药物机制综述。",
                    channel="vector",
                    score=0.9,
                )
            ],
            bm25_evidences=[],
        )
    )
    power = RetrievalPower(retriever=retriever)

    power.retrieve(
        (QueryUnit(unit_id="q1", text="查药物机制"),),
        path_filters=("storage/groups/medicine/knowledge",),
    )

    assert retriever.calls == [
        {
            "query": "查药物机制",
            "top_k": 4,
            "path_filters": ["storage/groups/medicine/knowledge"],
            "query_hints": [],
        }
    ]
