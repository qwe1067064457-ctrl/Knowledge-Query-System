from __future__ import annotations

from knowledge_retrieval.types import Evidence, HybridRetrievalResult
from workflow.powers.retrieval_power import RetrievalPower
from workflow.types import QueryUnit


class _FakeRetriever:
    def __init__(self, result: HybridRetrievalResult) -> None:
        self._result = result

    def retrieve(self, query: str, *, top_k: int = 4):
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

    assert quality["status"] in {"good", "weak"}
    assert quality["target_overlap_score"] != "bad"
    assert bundle.source_refs == ("docs/law.md",)


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

    assert quality["target_overlap_score"] == "bad"
    assert quality["should_repair"] is True
    assert "retrieval_quality_weak" in bundle.missing_evidence_notes


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

    assert len(bundle.query_unit_results) == 2
    assert bundle.merged_evidence_items[0].query_unit_ids == ("q1", "q2")
