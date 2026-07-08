from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from workflow.contracts.graph import ExecutionGraph

_DEFAULT_PLANNING_PROMPT = """你是一个 orchestration planner。

目标：
根据 task frame 输出最小可执行 ExecutionGraph。

术语解释：
- `unit`：执行图中的一个最小执行单元，不是普通语义分句。
- `capability`：这是 schema 里的字段名，本质上表示 `executor type`，也就是这个 unit 交给哪类 executor 处理。
- `qa_like`：普通问答型单元，目标是产出单点回答材料。
- `chat_like`：闲聊/轻交流型单元，不做重检索和重判断。
- `reject_like`：拒答或边界说明型单元。
- `compare`：比较型单元，要求覆盖对象、维度、差异或取舍。
- `verify`：判断/核验型单元，先判断某说法、前提或条件是否成立。
- `synthesis`：汇总型单元，整合前序 unit 结果形成最终回答材料。

要求：
1. 只输出 JSON。
2. 优先生成最小可执行 graph，不要把 unit 拆得过碎。
3. 如果多个 branch 在执行上不独立，应优先合并。
4. graph 必须是 DAG。
5. `binding_mode` 只允许 `skip|pre_shared|lazy`。
6. `capability` 只允许 `qa_like|chat_like|reject_like|compare|verify|synthesis`。
7. 如果不确定，优先 conservative graph。
8. 只有在执行上真正独立时才拆 unit；不要把纯语义切句误当成 execution unit。
9. 对 staged / conditional 任务，优先表达依赖和条件，不要伪装成并列 graph。
10. 如果多个 branch 共用同一 retrieval/binding/answer slot，应优先合并而不是细切。
11. 默认把 unit 总数控制在 2~4 个；但如果用户显式提出多个独立 query，且每个 query 都需要独立执行，可以放宽到 6 个左右。不要为了形式压缩而漏掉显式 query coverage。

输出 JSON：
{
  "units": [
    {
      "unit_id": "unit_id",
      "goal": "unit goal",
      "capability": "qa_like|chat_like|reject_like|compare|verify|synthesis",
      "depends_on": ["unit_id"],
      "proceed_if": "all_dependencies_completed|null",
      "output_slot": "slot_name",
      "binding_mode": "skip|pre_shared|lazy",
      "retrieval_mode": "auto|skip",
      "stop_when": "condition|null",
      "notes": ["note"]
    }
  ],
  "edges": [
    {
      "from_unit_id": "unit_id",
      "to_unit_id": "unit_id",
      "edge_type": "depends_on|conditional",
      "condition": "condition|null"
    }
  ],
  "graph_notes": ["note"]
}

task_frame:
{task_frame_json}
"""


class PlanningPromptHelper:
    def load_prompt(self, base_dir: Path | None) -> str:
        return self._load_prompt(base_dir, filename="execution_graph_planner_prompt.md", fallback=_DEFAULT_PLANNING_PROMPT)

    def render_prompt(self, *, base_dir: Path | None, task_frame: dict[str, Any]) -> str:
        template = self.load_prompt(base_dir)
        return template.replace("{task_frame_json}", self._json(task_frame))

    def render_grouped_prompt(self, *, base_dir: Path | None, task_frame: dict[str, Any]) -> str:
        template = self._load_prompt(
            base_dir,
            filename="grouped_unit_planner_prompt.md",
            fallback=self._default_grouped_prompt(),
        )
        return template.replace("{task_frame_json}", self._json(task_frame))

    def parse_json_payload(self, content: str) -> dict[str, Any]:
        text = content.strip()
        if text.startswith("```"):
            lines = [line for line in text.splitlines() if not line.startswith("```")]
            text = "\n".join(lines).strip()
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
        return json.loads(text)

    def validate_graph_payload(self, payload: dict[str, Any], *, max_units: int = 6) -> ExecutionGraph:
        data = dict(payload or {})
        graph = ExecutionGraph.from_dict(
            {
                "units": list(data.get("units", ()) or ()),
                "edges": list(data.get("edges", ()) or ()),
                "graph_notes": list(data.get("graph_notes", ()) or ()),
            }
        )
        unit_objs = graph.unit_objs()
        if not unit_objs:
            raise ValueError("planner_graph_missing_units")
        if len(unit_objs) > max_units:
            raise ValueError("planner_graph_too_many_units")
        if not graph.is_dag():
            raise ValueError("planner_graph_cycle")
        unit_ids = {unit.unit_id for unit in unit_objs if unit.unit_id.strip()}
        for unit in unit_objs:
            if not unit.unit_id.strip():
                raise ValueError("planner_graph_missing_unit_id")
            if not unit.goal.strip():
                raise ValueError("planner_graph_missing_unit_goal")
            if unit.capability not in {"qa_like", "chat_like", "reject_like", "compare", "verify", "synthesis"}:
                raise ValueError("planner_graph_invalid_capability")
            if unit.binding_mode not in {"skip", "pre_shared", "lazy"}:
                raise ValueError("planner_graph_invalid_binding_mode")
            if unit.retrieval_mode not in {"auto", "skip"}:
                raise ValueError("planner_graph_invalid_retrieval_mode")
            if not unit.output_slot.strip():
                raise ValueError("planner_graph_missing_output_slot")
            for dep in unit.depends_on:
                if dep not in unit_ids:
                    raise ValueError("planner_graph_unknown_dependency")
        for edge in graph.edge_objs():
            if not edge.from_unit_id.strip() or not edge.to_unit_id.strip():
                raise ValueError("planner_graph_missing_edge_endpoint")
            if edge.from_unit_id not in unit_ids or edge.to_unit_id not in unit_ids:
                raise ValueError("planner_graph_unknown_edge_endpoint")
            if edge.edge_type not in {"depends_on", "conditional"}:
                raise ValueError("planner_graph_invalid_edge_type")
            if edge.edge_type == "conditional" and not str(edge.condition or "").strip():
                raise ValueError("planner_graph_missing_condition")
        return graph

    def _load_prompt(self, base_dir: Path | None, *, filename: str, fallback: str) -> str:
        if base_dir is None:
            return fallback
        prompt_path = base_dir / "workflow" / "orchestrated" / "planning" / "prompts" / filename
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8").strip()
        return fallback

    def _json(self, payload: Any) -> str:
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def _default_grouped_prompt(self) -> str:
        path = Path(__file__).resolve().parents[1] / "orchestrated" / "planning" / "prompts" / "grouped_unit_planner_prompt.md"
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
        return _DEFAULT_PLANNING_PROMPT
