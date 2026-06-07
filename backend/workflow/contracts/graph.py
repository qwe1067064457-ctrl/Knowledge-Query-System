from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

BindingMode = Literal["skip", "pre_shared", "lazy"]
ExecutionUnitCapability = Literal["qa_like", "chat_like", "reject_like", "compare", "verify", "synthesis"]
ExecutionEdgeType = Literal["depends_on", "conditional"]
UnitState = Literal["pending", "completed", "skipped", "degraded", "blocked"]


@dataclass(frozen=True)
class GlobalBindingFrame:
    query_is_context_dependent: bool = False
    binding_scope_hint: Literal["global", "partial", "none"] = "none"
    shared_target_candidates: tuple[str, ...] = ()
    recommended_binding_mode: Literal["skip", "global_only", "selective_per_unit"] = "skip"
    segment_hints: tuple[dict[str, Any], ...] = ()
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_is_context_dependent": self.query_is_context_dependent,
            "binding_scope_hint": self.binding_scope_hint,
            "shared_target_candidates": list(self.shared_target_candidates),
            "recommended_binding_mode": self.recommended_binding_mode,
            "segment_hints": [dict(item) for item in self.segment_hints],
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "GlobalBindingFrame":
        data = dict(payload or {})
        return cls(
            query_is_context_dependent=bool(data.get("query_is_context_dependent", False)),
            binding_scope_hint=str(data.get("binding_scope_hint", "none")),  # type: ignore[arg-type]
            shared_target_candidates=tuple(
                str(item) for item in data.get("shared_target_candidates", ()) or () if item
            ),
            recommended_binding_mode=str(data.get("recommended_binding_mode", "skip")),  # type: ignore[arg-type]
            segment_hints=tuple(dict(item) for item in data.get("segment_hints", ()) or ()),
            notes=tuple(str(item) for item in data.get("notes", ()) or () if item),
        )


@dataclass(frozen=True)
class ExecutionUnit:
    unit_id: str
    goal: str
    capability: ExecutionUnitCapability = "qa_like"
    depends_on: tuple[str, ...] = ()
    proceed_if: str | None = None
    output_slot: str = ""
    binding_mode: BindingMode = "skip"
    retrieval_mode: str = "auto"
    stop_when: str | None = None
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "goal": self.goal,
            "capability": self.capability,
            "depends_on": list(self.depends_on),
            "proceed_if": self.proceed_if,
            "output_slot": self.output_slot,
            "binding_mode": self.binding_mode,
            "retrieval_mode": self.retrieval_mode,
            "stop_when": self.stop_when,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "ExecutionUnit":
        data = dict(payload or {})
        return cls(
            unit_id=str(data.get("unit_id", "")),
            goal=str(data.get("goal", "")),
            capability=str(data.get("capability", "qa_like")),  # type: ignore[arg-type]
            depends_on=tuple(str(item) for item in data.get("depends_on", ()) or () if item),
            proceed_if=str(data["proceed_if"]) if data.get("proceed_if") is not None else None,
            output_slot=str(data.get("output_slot", "")),
            binding_mode=str(data.get("binding_mode", "skip")),  # type: ignore[arg-type]
            retrieval_mode=str(data.get("retrieval_mode", "auto")),
            stop_when=str(data["stop_when"]) if data.get("stop_when") is not None else None,
            notes=tuple(str(item) for item in data.get("notes", ()) or () if item),
        )


@dataclass(frozen=True)
class ExecutionEdge:
    from_unit_id: str
    to_unit_id: str
    edge_type: ExecutionEdgeType = "depends_on"
    condition: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_unit_id": self.from_unit_id,
            "to_unit_id": self.to_unit_id,
            "edge_type": self.edge_type,
            "condition": self.condition,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "ExecutionEdge":
        data = dict(payload or {})
        return cls(
            from_unit_id=str(data.get("from_unit_id", "")),
            to_unit_id=str(data.get("to_unit_id", "")),
            edge_type=str(data.get("edge_type", "depends_on")),  # type: ignore[arg-type]
            condition=str(data["condition"]) if data.get("condition") is not None else None,
        )


@dataclass(frozen=True)
class ExecutionGraph:
    units: tuple[ExecutionUnit | dict[str, Any], ...] = ()
    edges: tuple[ExecutionEdge | dict[str, Any], ...] = ()
    graph_notes: tuple[str, ...] = ()

    def unit_objs(self) -> tuple[ExecutionUnit, ...]:
        return tuple(
            item if isinstance(item, ExecutionUnit) else ExecutionUnit.from_dict(item)
            for item in self.units
        )

    def edge_objs(self) -> tuple[ExecutionEdge, ...]:
        return tuple(
            item if isinstance(item, ExecutionEdge) else ExecutionEdge.from_dict(item)
            for item in self.edges
        )

    def entry_unit_ids(self) -> tuple[str, ...]:
        inbound = {edge.to_unit_id for edge in self.edge_objs() if edge.to_unit_id}
        return tuple(unit.unit_id for unit in self.unit_objs() if unit.unit_id and unit.unit_id not in inbound)

    def is_dag(self) -> bool:
        units = {unit.unit_id for unit in self.unit_objs() if unit.unit_id}
        adjacency: dict[str, set[str]] = {unit_id: set() for unit_id in units}
        indegree: dict[str, int] = {unit_id: 0 for unit_id in units}
        for edge in self.edge_objs():
            if edge.from_unit_id not in units or edge.to_unit_id not in units:
                continue
            if edge.to_unit_id in adjacency[edge.from_unit_id]:
                continue
            adjacency[edge.from_unit_id].add(edge.to_unit_id)
            indegree[edge.to_unit_id] += 1
        queue = [unit_id for unit_id, degree in indegree.items() if degree == 0]
        visited = 0
        while queue:
            current = queue.pop(0)
            visited += 1
            for next_unit in adjacency[current]:
                indegree[next_unit] -= 1
                if indegree[next_unit] == 0:
                    queue.append(next_unit)
        return visited == len(units)

    def topological_unit_ids(self) -> tuple[str, ...]:
        units = {unit.unit_id for unit in self.unit_objs() if unit.unit_id}
        adjacency: dict[str, set[str]] = {unit_id: set() for unit_id in units}
        indegree: dict[str, int] = {unit_id: 0 for unit_id in units}
        for edge in self.edge_objs():
            if edge.from_unit_id not in units or edge.to_unit_id not in units:
                continue
            if edge.to_unit_id in adjacency[edge.from_unit_id]:
                continue
            adjacency[edge.from_unit_id].add(edge.to_unit_id)
            indegree[edge.to_unit_id] += 1
        queue = [unit_id for unit_id, degree in indegree.items() if degree == 0]
        ordered: list[str] = []
        while queue:
            current = queue.pop(0)
            ordered.append(current)
            for next_unit in adjacency[current]:
                indegree[next_unit] -= 1
                if indegree[next_unit] == 0:
                    queue.append(next_unit)
        if len(ordered) != len(units):
            return tuple(unit.unit_id for unit in self.unit_objs())
        return tuple(ordered)

    def summary_dict(self) -> dict[str, Any]:
        edge_objs = self.edge_objs()
        return {
            "unit_count": len(self.unit_objs()),
            "edge_count": len(edge_objs),
            "entry_unit_count": len(self.entry_unit_ids()),
            "dag": self.is_dag(),
            "conditional_edge_count": sum(1 for edge in edge_objs if edge.edge_type == "conditional"),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "units": [item.to_dict() for item in self.unit_objs()],
            "edges": [item.to_dict() for item in self.edge_objs()],
            "graph_notes": list(self.graph_notes),
            "execution_summary": self.summary_dict(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "ExecutionGraph":
        data = dict(payload or {})
        return cls(
            units=tuple(dict(item) for item in data.get("units", ()) or ()),
            edges=tuple(dict(item) for item in data.get("edges", ()) or ()),
            graph_notes=tuple(str(item) for item in data.get("graph_notes", ()) or () if item),
        )


@dataclass(frozen=True)
class UnitResult:
    unit_id: str
    capability: ExecutionUnitCapability
    state: UnitState = "pending"
    binding_mode: BindingMode = "skip"
    used_binding: bool = False
    retrieval_quality_status: str = "not_applicable"
    output_slot: str = ""
    skipped_reason: str | None = None
    result_payload: dict[str, Any] = field(default_factory=dict)
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "capability": self.capability,
            "state": self.state,
            "binding_mode": self.binding_mode,
            "used_binding": self.used_binding,
            "retrieval_quality_status": self.retrieval_quality_status,
            "output_slot": self.output_slot,
            "skipped_reason": self.skipped_reason,
            "result_payload": dict(self.result_payload),
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "UnitResult":
        data = dict(payload or {})
        return cls(
            unit_id=str(data.get("unit_id", "")),
            capability=str(data.get("capability", "qa_like")),  # type: ignore[arg-type]
            state=str(data.get("state", "pending")),  # type: ignore[arg-type]
            binding_mode=str(data.get("binding_mode", "skip")),  # type: ignore[arg-type]
            used_binding=bool(data.get("used_binding", False)),
            retrieval_quality_status=str(data.get("retrieval_quality_status", "not_applicable")),
            output_slot=str(data.get("output_slot", "")),
            skipped_reason=str(data["skipped_reason"]) if data.get("skipped_reason") is not None else None,
            result_payload=dict(data.get("result_payload", {})),
            notes=tuple(str(item) for item in data.get("notes", ()) or () if item),
        )
