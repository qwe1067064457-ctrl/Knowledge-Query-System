"""
Context manager for transcript normalization, memory injection, budget-aware assembly,
and compaction.
"""
from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import tiktoken

    _HAS_TIKTOKEN = True
except ImportError:  # pragma: no cover - optional dependency
    _HAS_TIKTOKEN = False

from context.context_policy import ContextPolicyLoader
from context.dataclasses import TranscriptEntry
from context.session_manager import SessionManager
from memory_system import MemorySystem


@dataclass
class ContextConfig:
    # History
    max_turns: int = 8

    # Budget
    total_tokens: int = 6000
    core_reserved_tokens: int = 300
    core_max_tokens: int = 600
    retrieved_target_tokens: int = 800
    retrieved_max_tokens: int = 1400
    recent_turns_target_tokens: int = 2000
    recent_turns_max_tokens: int = 3200
    tool_results_target_tokens: int = 400
    tool_results_max_tokens: int = 1000
    tool_result_max_chars: int = 4000

    # Legacy compatibility knobs
    reserve_tokens: int = 20000
    soft_threshold_tokens: int = 5400
    keep_recent_tokens: int = 2000
    image_max_dimension_px: int = 1200

    # Memory
    memory_search_enabled: bool = True
    memory_top_k: int = 5
    memory_time_decay_half_life: int = 30
    memory_use_mmr: bool = True
    memory_mmr_lambda: float = 0.7

    # Compaction
    compaction_enabled: bool = True
    compaction_trigger_ratio: float = 0.9
    compaction_model: Optional[str] = None

    # Memory flush
    memory_flush_enabled: bool = True
    memory_flush_threshold: int = 5400

    # Prompt
    system_prompt_path: str = "prompts/system_prompt.md"

    @classmethod
    def from_policy(cls, policy: Dict[str, Any]) -> "ContextConfig":
        history = policy.get("history", {})
        budget = policy.get("budget", {})
        core = budget.get("core", {})
        retrieved = budget.get("retrieved_memories", {})
        recent = budget.get("recent_turns", {})
        tools = budget.get("tool_results", {})
        compaction = policy.get("compaction", {})
        memory = policy.get("memory", {})
        prompt = policy.get("prompt", {})

        total_tokens = int(budget.get("total_tokens", 6000))
        trigger_ratio = float(compaction.get("trigger_ratio", 0.9))
        soft_threshold = max(1, min(total_tokens, int(total_tokens * trigger_ratio)))

        return cls(
            max_turns=int(history.get("max_recent_turns", 8)),
            total_tokens=total_tokens,
            core_reserved_tokens=int(core.get("reserved", 300)),
            core_max_tokens=int(core.get("max", 600)),
            retrieved_target_tokens=int(retrieved.get("target", 800)),
            retrieved_max_tokens=int(retrieved.get("max", 1400)),
            recent_turns_target_tokens=int(recent.get("target", 2000)),
            recent_turns_max_tokens=int(recent.get("max", 3200)),
            tool_results_target_tokens=int(tools.get("target", 400)),
            tool_results_max_tokens=int(tools.get("max", 1000)),
            tool_result_max_chars=int(tools.get("max_chars_per_message", 4000)),
            soft_threshold_tokens=soft_threshold,
            keep_recent_tokens=int(compaction.get("keep_recent_tokens", 2000)),
            memory_search_enabled=bool(memory.get("search_enabled", True)),
            memory_top_k=int(memory.get("top_k", 5)),
            memory_time_decay_half_life=int(memory.get("time_decay_half_life", 30)),
            memory_use_mmr=bool(memory.get("use_mmr", True)),
            memory_mmr_lambda=float(memory.get("mmr_lambda", 0.7)),
            compaction_enabled=bool(compaction.get("enabled", True)),
            compaction_trigger_ratio=trigger_ratio,
            memory_flush_enabled=bool(memory.get("flush_enabled", True)),
            memory_flush_threshold=int(memory.get("flush_threshold", soft_threshold)),
            system_prompt_path=str(prompt.get("system_prompt_path", "prompts/system_prompt.md")),
        )


class ContextManager:
    def __init__(self, session_manager: SessionManager, memory_system: MemorySystem) -> None:
        self.session_mgr = session_manager
        self.memory_sys = memory_system
        self.policy_loader = ContextPolicyLoader(self.session_mgr.base_storage_path.parent / "context" / "context_policy.json")
        self.config = ContextConfig.from_policy(self.policy_loader.load_policy())
        self.llm_call: Optional[Callable[..., Any]] = None

        if _HAS_TIKTOKEN:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        else:
            self.tokenizer = None

    def reload_policy(self) -> None:
        self.config = ContextConfig.from_policy(self.policy_loader.load_policy())

    def set_llm_call(self, llm_call: Callable[..., Any]) -> None:
        self.llm_call = llm_call

    async def _call_llm_text(self, prompt: str) -> str:
        if self.llm_call is None:
            return ""
        try:
            result = self.llm_call(prompt)
        except TypeError:
            result = self.llm_call()

        if inspect.isawaitable(result):
            result = await result

        if hasattr(result, "ainvoke"):
            result = await result.ainvoke([{"role": "user", "content": prompt}])

        content = getattr(result, "content", result)
        if isinstance(content, list):
            parts: List[str] = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(str(block.get("text", "")))
                else:
                    parts.append(str(block))
            return "".join(parts)
        return str(content or "")

    def _apply_runtime_overrides(self, kwargs: Dict[str, Any]) -> None:
        if not kwargs:
            return
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

    def _count_tokens(self, text: str) -> int:
        if not text:
            return 0
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        return max(1, len(text) // 4)

    def _count_messages_tokens(self, messages: List[Dict[str, Any]]) -> int:
        total = 0
        for message in messages:
            total += self._count_tokens(str(message.get("content", "") or ""))
            for tool_call in message.get("tool_calls", []) or []:
                total += self._count_tokens(str(tool_call))
        return total

    def _trim_text_to_tokens(self, text: str, max_tokens: int) -> str:
        if max_tokens <= 0 or not text:
            return ""
        if self._count_tokens(text) <= max_tokens:
            return text
        if self.tokenizer:
            token_ids = self.tokenizer.encode(text)[:max_tokens]
            trimmed = self.tokenizer.decode(token_ids)
        else:
            approx_chars = max_tokens * 4
            trimmed = text[:approx_chars]
        return trimmed.rstrip() + "...[truncated]"

    def _entry_to_message(self, entry: TranscriptEntry) -> Dict[str, Any]:
        message: Dict[str, Any] = {
            "role": entry.role,
            "content": entry.content,
        }
        if entry.tool_calls:
            message["tool_calls"] = [
                {"id": tc.id, "type": tc.type, "function": tc.function}
                for tc in entry.tool_calls
            ]
        if entry.tool_call_id:
            message["tool_call_id"] = entry.tool_call_id
        return {key: value for key, value in message.items() if value is not None}

    def _entries_to_messages(
        self,
        entries: List[TranscriptEntry],
        extra_messages: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        latest_compaction_index: Optional[int] = None
        for index, entry in enumerate(entries):
            if entry.entry_type == "compaction" and entry.content:
                latest_compaction_index = index

        messages: List[Dict[str, Any]] = []
        start_index = 0
        if latest_compaction_index is not None:
            compaction = entries[latest_compaction_index]
            messages.append(
                {
                    "role": "system",
                    "content": f"[以下是之前对话的摘要]\n{compaction.content}",
                    "_context_block": "compaction_summary",
                }
            )
            start_index = latest_compaction_index + 1

        for entry in entries[start_index:]:
            if entry.entry_type == "compaction":
                continue
            messages.append(self._entry_to_message(entry))

        if extra_messages:
            messages.extend(extra_messages)
        return messages

    def _normalize_transcript(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not messages:
            return []

        leading_system: List[Dict[str, Any]] = []
        turn_messages: List[Dict[str, Any]] = []
        turns: List[List[Dict[str, Any]]] = []
        seen_user = False

        for message in messages:
            role = message.get("role")
            if not seen_user and role == "system":
                leading_system.append(message)
                continue
            if role == "user":
                seen_user = True
                if turn_messages:
                    turns.append(turn_messages)
                turn_messages = [message]
                continue
            if not seen_user:
                continue
            if not turn_messages:
                continue
            turn_messages.append(message)

        if turn_messages:
            turns.append(turn_messages)

        normalized: List[Dict[str, Any]] = list(leading_system)
        for turn in turns:
            normalized.extend(turn)
        return normalized

    def _split_turns(self, messages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[List[Dict[str, Any]]]]:
        leading_system: List[Dict[str, Any]] = []
        turns: List[List[Dict[str, Any]]] = []
        current_turn: List[Dict[str, Any]] = []

        for message in messages:
            role = message.get("role")
            if not turns and not current_turn and role == "system":
                leading_system.append(message)
                continue
            if role == "user":
                if current_turn:
                    turns.append(current_turn)
                current_turn = [message]
                continue
            if current_turn:
                current_turn.append(message)

        if current_turn:
            turns.append(current_turn)
        return leading_system, turns

    def _limit_history_turns(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if self.config.max_turns <= 0:
            return messages
        normalized = self._normalize_transcript(messages)
        leading_system, turns = self._split_turns(normalized)
        if len(turns) <= self.config.max_turns:
            return normalized

        kept_turns = turns[-self.config.max_turns :]
        flattened: List[Dict[str, Any]] = list(leading_system)
        for turn in kept_turns:
            flattened.extend(turn)
        return flattened

    def _build_core_memory_message(self, memories: List[Any]) -> Optional[Dict[str, Any]]:
        if not memories:
            return None
        lines = ["## 核心记忆（高优先级）", ""]
        for memory in memories:
            label = "全局用户" if memory.scope == "user_global" else "当前组用户"
            title = f"{memory.title}: " if memory.title else ""
            lines.append(f"- [{label}] {title}{memory.content}")
        content = "\n".join(lines).strip()
        return {"role": "system", "content": content, "_context_block": "core_memory"}

    def _build_retrieved_memory_message(self, memories: List[Any]) -> Optional[Dict[str, Any]]:
        if not memories:
            return None
        lines = ["## 相关记忆（供参考）", ""]
        for memory in memories:
            mem_time = memory.timestamp.strftime("%Y-%m-%d") if memory.timestamp else "unknown"
            title = f"{memory.title}\n" if memory.title else ""
            lines.append(f"**来源: {memory.source}** ({mem_time})")
            if title:
                lines.append(title.rstrip())
            lines.append(memory.content)
            lines.append("")
        content = "\n".join(lines).strip()
        return {"role": "system", "content": content, "_context_block": "retrieved_memory"}

    def _inject_memories(
        self,
        group_id: str,
        agent_id: str,
        query: str,
        messages: List[Dict[str, Any]],
        user_id: str,
    ) -> List[Dict[str, Any]]:
        if not self.config.memory_search_enabled:
            return messages

        core_memories = self.memory_sys.get_core_memories(user_id=user_id, group_id=group_id)
        retrieved_memories = self.memory_sys.search(
            group_id=group_id,
            agent_id=agent_id,
            query=query,
            top_k=self.config.memory_top_k,
            time_decay_half_life=self.config.memory_time_decay_half_life,
            use_mmr=self.config.memory_use_mmr,
            mmr_lambda=self.config.memory_mmr_lambda,
            user_id=user_id,
            include_core=False,
        )

        injections: List[Dict[str, Any]] = []
        core_block = self._build_core_memory_message(core_memories)
        related_block = self._build_retrieved_memory_message(retrieved_memories)
        if core_block:
            injections.append(core_block)
        if related_block:
            injections.append(related_block)
        if not injections:
            return messages

        if messages and messages[0].get("role") == "system":
            return [messages[0], *injections, *messages[1:]]
        return [*injections, *messages]

    def _trim_block_to_budget(self, messages: List[Dict[str, Any]], block_name: str, max_tokens: int) -> None:
        if max_tokens <= 0:
            return
        for message in messages:
            if message.get("_context_block") != block_name:
                continue
            content = str(message.get("content", "") or "")
            message["content"] = self._trim_text_to_tokens(content, max_tokens)

    @staticmethod
    def _reduce_budget(allocation: Dict[str, int], key: str, amount: int) -> int:
        reducible = min(allocation.get(key, 0), max(0, amount))
        allocation[key] = max(0, allocation.get(key, 0) - reducible)
        return amount - reducible

    @staticmethod
    def _expand_budget(
        allocation: Dict[str, int],
        key: str,
        desired: Dict[str, int],
        remaining: int,
    ) -> int:
        if remaining <= 0:
            return 0
        current = allocation.get(key, 0)
        target = desired.get(key, current)
        room = max(0, target - current)
        delta = min(room, remaining)
        allocation[key] = current + delta
        return remaining - delta

    def _plan_context_budget(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        core_messages = [msg for msg in messages if msg.get("_context_block") == "core_memory"]
        retrieved_messages = [msg for msg in messages if msg.get("_context_block") == "retrieved_memory"]
        conversation_messages = [
            msg
            for msg in messages
            if msg.get("_context_block") not in {"core_memory", "retrieved_memory"}
        ]

        actual = {
            "core": self._count_messages_tokens(core_messages),
            "retrieved_memories": self._count_messages_tokens(retrieved_messages),
            "recent_turns": sum(
                self._count_tokens(str(msg.get("content", "") or ""))
                for msg in conversation_messages
                if msg.get("role") != "tool"
            ),
            "tool_results": sum(
                self._count_tokens(str(msg.get("content", "") or ""))
                for msg in conversation_messages
                if msg.get("role") == "tool"
            ),
        }

        total_budget = min(
            self._get_model_window_size() - self.config.reserve_tokens,
            self.config.total_tokens,
        )
        total_budget = max(0, total_budget)

        allocation = {
            "core": min(actual["core"], self.config.core_reserved_tokens),
            "retrieved_memories": min(actual["retrieved_memories"], self.config.retrieved_target_tokens),
            "recent_turns": min(actual["recent_turns"], self.config.recent_turns_target_tokens),
            "tool_results": min(actual["tool_results"], self.config.tool_results_target_tokens),
        }

        floor_sum = sum(allocation.values())
        if floor_sum > total_budget:
            overflow = floor_sum - total_budget
            for key in ("tool_results", "retrieved_memories", "recent_turns", "core"):
                overflow = self._reduce_budget(allocation, key, overflow)
                if overflow <= 0:
                    break

        remaining = max(0, total_budget - sum(allocation.values()))
        desired = {
            "core": min(actual["core"], self.config.core_max_tokens),
            "retrieved_memories": min(actual["retrieved_memories"], self.config.retrieved_max_tokens),
            "recent_turns": min(actual["recent_turns"], self.config.recent_turns_max_tokens),
            "tool_results": min(actual["tool_results"], self.config.tool_results_max_tokens),
        }
        for key in ("recent_turns", "retrieved_memories", "tool_results", "core"):
            remaining = self._expand_budget(allocation, key, desired, remaining)
            if remaining <= 0:
                break

        return {
            "total_budget": total_budget,
            "actual": actual,
            "allocation": allocation,
            "remaining": remaining,
        }

    def _trim_tool_messages(self, messages: List[Dict[str, Any]]) -> None:
        for message in messages:
            if message.get("role") != "tool":
                continue
            content = str(message.get("content", "") or "")
            if len(content) > self.config.tool_result_max_chars:
                message["content"] = content[: self.config.tool_result_max_chars].rstrip() + "...[truncated]"

    def _trim_tool_budget(self, messages: List[Dict[str, Any]]) -> None:
        tool_indices = [index for index, msg in enumerate(messages) if msg.get("role") == "tool"]
        if not tool_indices:
            return
        total = sum(self._count_tokens(str(messages[index].get("content", "") or "")) for index in tool_indices)
        if total <= self.config.tool_results_max_tokens:
            return

        remaining = self.config.tool_results_max_tokens
        kept: List[int] = []
        for index in reversed(tool_indices):
            content = str(messages[index].get("content", "") or "")
            token_count = self._count_tokens(content)
            if remaining <= 0:
                messages[index]["content"] = ""
                continue
            if token_count <= remaining:
                kept.append(index)
                remaining -= token_count
                continue
            messages[index]["content"] = self._trim_text_to_tokens(content, remaining)
            remaining = 0
            kept.append(index)
        for index in tool_indices:
            if index not in kept and not str(messages[index].get("content", "") or "").strip():
                messages[index]["content"] = "[tool result omitted due to budget]"

    def _trim_tool_messages_to_budget(self, messages: List[Dict[str, Any]], max_tokens: int) -> None:
        if max_tokens < 0:
            max_tokens = 0
        tool_indices = [index for index, msg in enumerate(messages) if msg.get("role") == "tool"]
        if not tool_indices:
            return
        total = sum(self._count_tokens(str(messages[index].get("content", "") or "")) for index in tool_indices)
        if total <= max_tokens:
            return

        remaining = max_tokens
        kept: List[int] = []
        for index in reversed(tool_indices):
            content = str(messages[index].get("content", "") or "")
            token_count = self._count_tokens(content)
            if remaining <= 0:
                messages[index]["content"] = "[tool result omitted due to budget]"
                continue
            if token_count <= remaining:
                kept.append(index)
                remaining -= token_count
                continue
            messages[index]["content"] = self._trim_text_to_tokens(content, remaining)
            kept.append(index)
            remaining = 0
        for index in tool_indices:
            if index not in kept and str(messages[index].get("content", "") or "").strip():
                messages[index]["content"] = "[tool result omitted due to budget]"

    def _trim_message_sequence_to_budget(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int,
    ) -> List[Dict[str, Any]]:
        trimmed = [dict(message) for message in messages]

        def non_tool_total() -> int:
            return sum(
                self._count_tokens(str(msg.get("content", "") or ""))
                for msg in trimmed
                if msg.get("role") != "tool"
            )

        current = non_tool_total()
        if current <= max_tokens:
            return trimmed

        for preferred_roles in ({"assistant", "system"}, {"user"}):
            for msg in trimmed:
                role = str(msg.get("role", "assistant"))
                if role == "tool" or role not in preferred_roles:
                    continue
                content = str(msg.get("content", "") or "")
                old_tokens = self._count_tokens(content)
                if old_tokens <= 0:
                    continue
                overflow = current - max_tokens
                if overflow <= 0:
                    break
                if old_tokens <= overflow:
                    msg["content"] = ""
                    current -= old_tokens
                    continue
                msg["content"] = self._trim_text_to_tokens(content, old_tokens - overflow)
                current = non_tool_total()
                if current <= max_tokens:
                    break
            if current <= max_tokens:
                break
        return trimmed

    def _trim_recent_conversation(
        self,
        messages: List[Dict[str, Any]],
        recent_budget: int,
    ) -> List[Dict[str, Any]]:
        if recent_budget <= 0:
            return [dict(message) for message in messages if message.get("role") == "tool"]

        leading_system, turns = self._split_turns(messages)
        kept_turns: List[List[Dict[str, Any]]] = []
        remaining = recent_budget

        leading_trimmed = self._trim_message_sequence_to_budget(leading_system, recent_budget)
        leading_tokens = sum(
            self._count_tokens(str(msg.get("content", "") or ""))
            for msg in leading_trimmed
            if msg.get("role") != "tool"
        )
        remaining = max(0, recent_budget - leading_tokens)

        for turn in reversed(turns):
            turn_non_tool_tokens = sum(
                self._count_tokens(str(msg.get("content", "") or ""))
                for msg in turn
                if msg.get("role") != "tool"
            )
            if turn_non_tool_tokens <= remaining:
                kept_turns.append([dict(message) for message in turn])
                remaining -= turn_non_tool_tokens
                continue
            if not kept_turns:
                kept_turns.append(self._trim_message_sequence_to_budget(turn, remaining))
                remaining = 0
            break

        kept_turns.reverse()
        flattened: List[Dict[str, Any]] = list(leading_trimmed)
        for turn in kept_turns:
            flattened.extend(turn)

        return self._trim_message_sequence_to_budget(flattened, recent_budget)

    def _assemble_context(self, messages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], bool, Dict[str, Any]]:
        prepared = [dict(message) for message in messages]
        for index, message in enumerate(prepared):
            message["_message_index"] = index

        self._trim_tool_messages(prepared)
        budget_plan = self._plan_context_budget(prepared)
        allocation = budget_plan["allocation"]

        self._trim_block_to_budget(prepared, "core_memory", allocation["core"])
        self._trim_block_to_budget(prepared, "retrieved_memory", allocation["retrieved_memories"])

        conversation_messages = [
            dict(msg)
            for msg in prepared
            if msg.get("_context_block") not in {"core_memory", "retrieved_memory"}
        ]
        conversation_messages = self._trim_recent_conversation(
            conversation_messages,
            allocation["recent_turns"],
        )
        self._trim_tool_messages_to_budget(conversation_messages, allocation["tool_results"])

        trimmed_by_index = {
            int(msg["_message_index"]): msg
            for msg in conversation_messages
        }

        rebuilt: List[Dict[str, Any]] = []
        for message in prepared:
            index = int(message["_message_index"])
            if message.get("_context_block") in {"core_memory", "retrieved_memory"}:
                rebuilt.append(message)
                continue
            if index in trimmed_by_index:
                rebuilt.append(trimmed_by_index[index])

        for message in rebuilt:
            message.pop("_message_index", None)

        current_tokens = self._count_messages_tokens(rebuilt)
        hard_budget = min(self._get_model_window_size() - self.config.reserve_tokens, self.config.total_tokens)
        threshold = min(hard_budget, self.config.soft_threshold_tokens)
        needs_compaction = current_tokens > threshold
        return rebuilt, needs_compaction, {
            "total": budget_plan["total_budget"],
            "used": current_tokens,
            "remaining": max(0, budget_plan["total_budget"] - current_tokens),
            "actual": budget_plan["actual"],
            "blocks": allocation,
        }

    def _fallback_summary(self, messages: List[Dict[str, Any]]) -> str:
        if not messages:
            return ""
        lines: List[str] = []
        for message in messages[:12]:
            role = str(message.get("role", "assistant"))
            content = str(message.get("content", "") or "").strip()
            if content:
                lines.append(f"{role}: {content[:180]}")
        if len(messages) > 12:
            lines.append(f"...已省略 {len(messages) - 12} 条较早消息")
        return "\n".join(lines)[:1000]

    async def _trigger_compaction(
        self,
        group_id: str,
        agent_id: str,
        session_id: str,
        messages: List[Dict[str, Any]],
        user_id: str,
    ) -> Dict[str, Any]:
        if not self.config.compaction_enabled:
            return {"success": False, "reason": "compaction disabled"}

        original_tokens = self._count_messages_tokens(messages)
        memory_flushed = False

        if self.config.memory_flush_enabled:
            try:
                context_str = json.dumps(messages[-50:], ensure_ascii=False)
                flush_prompt = (
                    "提取对你主人重要的信息\n"
                    "你即将失去当前上下文。请提取对后续对话有长期价值的要点，"
                    "优先关注用户偏好、已确认决策、重要事实和当前约束。\n\n"
                    "如果没有值得记录的内容，回复 NO_REPLY。\n\n"
                    f"上下文：\n{context_str[:8000]}"
                )
                important_info = await self._call_llm_text(flush_prompt)
                if important_info and important_info.strip() != "NO_REPLY":
                    flush_result = await self.memory_sys.flush_from_context(
                        group_id,
                        agent_id,
                        important_info,
                        user_id=user_id,
                        source_session_id=session_id,
                        messages=messages,
                    )
                    memory_flushed = bool(flush_result.get("flushed"))
            except Exception as exc:  # pragma: no cover - best effort
                print(f"Memory flush failed: {exc}")

        keep_from_index = 0
        keep_tokens = 0
        for index in range(len(messages) - 1, -1, -1):
            msg_tokens = self._count_messages_tokens([messages[index]])
            if keep_tokens + msg_tokens > self.config.keep_recent_tokens:
                keep_from_index = index + 1
                break
            keep_tokens += msg_tokens

        to_summarize = messages[:keep_from_index]
        to_keep = messages[keep_from_index:]
        if not to_summarize and len(messages) > 1:
            to_summarize = messages[:-1]
            to_keep = messages[-1:]
            keep_tokens = self._count_messages_tokens(to_keep)

        if not to_summarize:
            return {
                "success": False,
                "reason": "no messages to summarize",
                "original_tokens": original_tokens,
                "compressed_tokens": original_tokens,
                "memory_flushed": memory_flushed,
            }

        summary = ""
        try:
            summarize_prompt = (
                "请将以下对话总结为一段简洁摘要，保留用户目标、关键事实、已确认决策、"
                "未完成事项和必要约束。控制在 500 字以内。\n\n"
                f"{json.dumps(to_summarize, ensure_ascii=False)}\n\n摘要："
            )
            summary = await self._call_llm_text(summarize_prompt)
        except Exception as exc:  # pragma: no cover - best effort
            print(f"Compaction failed: {exc}")

        if not summary:
            summary = self._fallback_summary(to_summarize)

        if summary:
            session = self.session_mgr.get_session(session_id, group_id, agent_id)
            if session:
                compaction_entry = TranscriptEntry(
                    id=f"compaction_{int(datetime.now().timestamp() * 1000)}",
                    session_id=session_id,
                    group_id=group_id,
                    timestamp=int(datetime.now().timestamp() * 1000),
                    role="system",
                    entry_type="compaction",
                    content=summary,
                    token_count=self._count_tokens(summary),
                )
                self.session_mgr.append_entry(group_id, agent_id, compaction_entry)

        compressed_tokens = self._count_messages_tokens([{"content": summary}]) + keep_tokens
        return {
            "success": True,
            "summary": summary,
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "memory_flushed": memory_flushed,
        }

    def _get_model_window_size(self) -> int:
        return 128000

    def _extract_query_from_messages(self, messages: List[Dict[str, Any]]) -> str:
        for message in reversed(messages):
            if message.get("role") == "user" and message.get("content"):
                content = str(message["content"])
                return content[:200]
        return ""

    async def prepare(
        self,
        group_id: str,
        agent_id: str,
        session_id: str,
        extra_messages: Optional[List[Dict[str, Any]]] = None,
        query: Optional[str] = None,
        allow_compaction: bool = True,
        _compaction_attempt: int = 0,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        self.reload_policy()
        self._apply_runtime_overrides(kwargs)

        entries = self.session_mgr.get_transcript(group_id, agent_id, session_id, include_compacted=True)
        messages = self._entries_to_messages(entries, extra_messages)
        session = self.session_mgr.get_session(session_id, group_id, agent_id)
        user_id = session.user_id if session else str(kwargs.get("user_id", "default"))

        if not messages:
            return {"messages": [], "total_tokens": 0, "needs_compaction": False}

        messages = self._normalize_transcript(messages)
        messages = self._limit_history_turns(messages)

        active_query = query or self._extract_query_from_messages(messages)
        if active_query:
            messages = self._inject_memories(group_id, agent_id, active_query, messages, user_id=user_id)

        messages, needs_compaction, budget_info = self._assemble_context(messages)

        compaction_result: Optional[Dict[str, Any]] = None
        if allow_compaction and needs_compaction and self.config.compaction_enabled and _compaction_attempt < 1:
            compaction_result = await self._trigger_compaction(group_id, agent_id, session_id, messages, user_id)
            if compaction_result.get("success"):
                return await self.prepare(
                    group_id,
                    agent_id,
                    session_id,
                    extra_messages=extra_messages,
                    query=query,
                    allow_compaction=False,
                    _compaction_attempt=_compaction_attempt + 1,
                    **kwargs,
                )

        return {
            "messages": messages,
            "total_tokens": self._count_messages_tokens(messages),
            "needs_compaction": needs_compaction,
            "compaction": compaction_result,
            "budget": budget_info,
        }

    async def prepare_messages(
        self,
        group_id: str,
        agent_id: str,
        messages: List[Dict[str, Any]],
        query: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        self.reload_policy()
        user_id = str(kwargs.pop("user_id", "default"))
        self._apply_runtime_overrides(kwargs)

        prepared = list(messages)
        if not prepared:
            return {"messages": [], "total_tokens": 0, "needs_compaction": False}

        prepared = self._normalize_transcript(prepared)
        prepared = self._limit_history_turns(prepared)
        active_query = query or self._extract_query_from_messages(prepared)
        if active_query:
            prepared = self._inject_memories(group_id, agent_id, active_query, prepared, user_id=user_id)
        prepared, needs_compaction, budget_info = self._assemble_context(prepared)
        return {
            "messages": prepared,
            "total_tokens": self._count_messages_tokens(prepared),
            "needs_compaction": needs_compaction,
            "budget": budget_info,
        }

    def get_status(self, group_id: str, agent_id: str, session_id: str) -> Dict[str, Any]:
        self.reload_policy()
        entries = self.session_mgr.get_transcript(group_id, agent_id, session_id, include_compacted=True)
        messages = self._entries_to_messages(entries)
        current_tokens = self._count_messages_tokens(messages)
        return {
            "session_id": session_id,
            "group_id": group_id,
            "agent_id": agent_id,
            "current_tokens": current_tokens,
            "needs_compaction": current_tokens > self.config.soft_threshold_tokens,
            "compaction_threshold": self.config.soft_threshold_tokens,
            "memory_flush_threshold": self.config.memory_flush_threshold,
            "max_turns": self.config.max_turns,
            "total_tokens_budget": self.config.total_tokens,
            "system_prompt_path": self.config.system_prompt_path,
        }
