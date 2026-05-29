from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DEFAULT_GLOBAL_BINDING_PROMPT = """你是一个 orchestration global binding framing 助手。

目标：
1. 判断当前请求是否整体依赖最近上下文。
2. 判断依赖范围是 global / partial / none。
3. 给出 shared target 候选和 binding strategy hint。
4. 不做 deep binding，不要假装唯一确定最终 target。

要求：
1. 只输出 JSON。
2. 可以利用 rule_frame、最近对话、working memory hints、memory anchor hints、候选对象。
3. 如果没有足够证据，不要过度推断；优先输出 conservative frame。
4. 如果只有局部片段依赖上下文，必须输出 segment_hints。
5. 单句请求也允许输出 segment_hints；segment_hints 表示局部上下文依赖分布，不等于 execution unit。
6. `segment_hints` 只做 framing，不做 deep resolution；你可以标出依赖类型、重写 hint、继承上下文范围，但不要假装唯一确定 referent。
6. 不要直接输出 deep binding result，不要假装已经唯一确定最终 target。
7. `recommended_binding_mode` 只表达 binding strategy hint：
   - `skip`: 整体不建议 binding
   - `global_only`: 整体像共享同一上下文/target
   - `selective_per_unit`: 只有局部片段或后续 unit 需要 binding
8. 如果 `binding_scope_hint=partial`，应优先输出 `recommended_binding_mode=selective_per_unit`。
9. 如果 `binding_scope_hint=none`，应优先输出 `recommended_binding_mode=skip`。

输出 JSON：
{
  "query_is_context_dependent": true,
  "binding_scope_hint": "global|partial|none",
  "shared_target_candidates": ["target_id"],
  "recommended_binding_mode": "skip|global_only|selective_per_unit",
  "segment_hints": [
    {
      "text": "片段文本",
      "needs_context": true,
      "segment_type": "fresh_task|follow_up_targeted|continuation|comparison_branch|synthesis_branch",
      "context_need_type": "target_resolution|task_continuity|reference_recovery|none",
      "shared_target_candidate_ids": ["target_id"],
      "reason": "简短原因",
      "confidence": "high|medium|low",
      "rewrite_hint": "可选，给后续 binding/planning 的重写提示",
      "inherited_context_span": "可选，描述继承哪一段上下文"
    }
  ],
  "notes": ["简短说明"]
}

rule_frame:
{rule_frame_json}

recent_messages:
{recent_messages_json}

working_memory_hints:
{working_memory_hints_json}

memory_anchor_hints:
{memory_anchor_hints_json}

binding_candidates:
{binding_candidates_json}

query:
{query}
"""


class GlobalBindingPromptHelper:
    def load_prompt(self, base_dir: Path | None) -> str:
        return self._load_prompt(base_dir, filename="global_binding_frame_prompt.md", fallback=_DEFAULT_GLOBAL_BINDING_PROMPT)

    def render_prompt(
        self,
        *,
        base_dir: Path | None,
        query: str,
        rule_frame: dict[str, Any],
        recent_messages: list[dict[str, Any]],
        working_memory_hints: list[dict[str, Any]],
        memory_anchor_hints: list[dict[str, Any]],
        binding_candidates: list[dict[str, Any]],
    ) -> str:
        template = self.load_prompt(base_dir)
        return (
            template.replace("{query}", query)
            .replace("{rule_frame_json}", self._json(rule_frame))
            .replace("{recent_messages_json}", self._json(recent_messages[-6:]))
            .replace("{working_memory_hints_json}", self._json(working_memory_hints[:6]))
            .replace("{memory_anchor_hints_json}", self._json(memory_anchor_hints[:6]))
            .replace("{binding_candidates_json}", self._json(binding_candidates[:8]))
        )

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

    def validate_payload(self, payload: dict[str, Any], *, fallback_scope: str = "none") -> dict[str, Any]:
        data = dict(payload or {})
        scope = str(data.get("binding_scope_hint", fallback_scope)).strip().lower()
        if scope not in {"global", "partial", "none"}:
            scope = fallback_scope if fallback_scope in {"global", "partial", "none"} else "none"
        mode = str(data.get("recommended_binding_mode", "skip")).strip().lower()
        if mode not in {"skip", "global_only", "selective_per_unit"}:
            mode = "skip"
        segment_hints = []
        for item in data.get("segment_hints", ()) or ():
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            segment_type = str(item.get("segment_type") or "fresh_task").strip().lower()
            if segment_type not in {"fresh_task", "follow_up_targeted", "continuation", "comparison_branch", "synthesis_branch"}:
                segment_type = "fresh_task"
            context_need_type = str(item.get("context_need_type") or "none").strip().lower()
            if context_need_type not in {"target_resolution", "task_continuity", "reference_recovery", "none"}:
                context_need_type = "none"
            confidence = str(item.get("confidence") or "medium").strip().lower()
            if confidence not in {"high", "medium", "low"}:
                confidence = "medium"
            segment_hints.append(
                {
                    "text": text,
                    "needs_context": bool(item.get("needs_context", False)),
                    "segment_type": segment_type,
                    "context_need_type": context_need_type,
                    "shared_target_candidate_ids": [
                        str(candidate).strip()
                        for candidate in item.get("shared_target_candidate_ids", ()) or ()
                        if str(candidate).strip()
                    ],
                    "reason": str(item.get("reason") or "").strip(),
                    "confidence": confidence,
                    "rewrite_hint": str(item.get("rewrite_hint") or "").strip(),
                    "inherited_context_span": str(item.get("inherited_context_span") or "").strip(),
                }
            )
        if scope == "none":
            mode = "skip"
            segment_hints = []
        elif scope == "partial" and mode == "global_only":
            mode = "selective_per_unit"
        elif scope == "global" and not data.get("shared_target_candidates"):
            mode = "selective_per_unit" if segment_hints else "skip"
        return {
            "query_is_context_dependent": bool(data.get("query_is_context_dependent", False)),
            "binding_scope_hint": scope,
            "shared_target_candidates": [
                str(item).strip()
                for item in data.get("shared_target_candidates", ()) or ()
                if str(item).strip()
            ],
            "recommended_binding_mode": mode,
            "segment_hints": segment_hints,
            "notes": [str(item).strip() for item in data.get("notes", ()) or () if str(item).strip()],
        }

    def _load_prompt(self, base_dir: Path | None, *, filename: str, fallback: str) -> str:
        if base_dir is None:
            return fallback
        candidate_paths = (
            base_dir / "workflow" / "orchestrated" / "binding" / "prompts" / filename,
            base_dir / "prompts" / "workflow" / filename,
        )
        for prompt_path in candidate_paths:
            if prompt_path.exists():
                return prompt_path.read_text(encoding="utf-8").strip()
        return fallback

    def _json(self, payload: Any) -> str:
        return json.dumps(payload, ensure_ascii=False, indent=2)
