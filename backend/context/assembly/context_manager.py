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

from context.assembly.context_policy import ContextPolicyLoader
from context.models import TranscriptEntry
from context.registry.registry import ContextRegistryManager
from context.registry.registry_types import ContextRegistry, ContextRegistryEntry
from context.session.session_manager import SessionManager
from memory_system.memory_service import MemorySystem

_PRE_COMPACTION_EXTRACTOR_VERSION = "pre_compaction_v1"
_PRE_COMPACTION_STATE_KEY = "_pre_compaction_extractions"


@dataclass
class ContextConfig:
    max_turns: int = 8
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
    reserve_tokens: int = 20000
    soft_threshold_tokens: int = 5400
    keep_recent_tokens: int = 2000
    image_max_dimension_px: int = 1200
    memory_search_enabled: bool = True
    memory_top_k: int = 5
    memory_time_decay_half_life: int = 30
    memory_use_mmr: bool = True
    memory_mmr_lambda: float = 0.7
    compaction_enabled: bool = True
    compaction_trigger_ratio: float = 0.9
    compaction_model: Optional[str] = None
    memory_flush_enabled: bool = True
    memory_flush_threshold: int = 5400
    system_prompt_path: str = "prompts/system/answer_system_prompt.md"

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
            system_prompt_path=str(prompt.get("system_prompt_path", "prompts/system/answer_system_prompt.md")),
        )


class ContextManager:
    def __init__(self, session_manager: SessionManager, memory_system: MemorySystem) -> None:
        self.session_mgr = session_manager
        self.memory_sys = memory_system
        self.registry_mgr = ContextRegistryManager(session_manager)
        self.policy_loader = ContextPolicyLoader(
            self.session_mgr.base_storage_path.parent / "context" / "assembly" / "context_policy.json"
        )
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
            "id": entry.id,
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
            if role in {"assistant", "tool", "system"}:
                if not turn_messages:
                    turn_messages = [message]
                else:
                    turn_messages.append(message)

        if turn_messages:
            turns.append(turn_messages)

        normalized: List[Dict[str, Any]] = list(leading_system)
        for turn in turns:
            normalized.extend(turn)
        return normalized

    def _limit_history_turns(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if self.config.max_turns <= 0:
            return messages

        system_messages: List[Dict[str, Any]] = []
        turns: List[List[Dict[str, Any]]] = []
        current_turn: List[Dict[str, Any]] = []
        seen_user = False

        for message in messages:
            role = message.get("role")
            if not seen_user and role == "system":
                system_messages.append(message)
                continue
            if role == "user":
                seen_user = True
                if current_turn:
                    turns.append(current_turn)
                current_turn = [message]
                continue
            if not seen_user:
                continue
            current_turn.append(message)

        if current_turn:
            turns.append(current_turn)

        if len(turns) <= self.config.max_turns:
            return messages

        kept_turns = turns[-self.config.max_turns:]
        limited: List[Dict[str, Any]] = list(system_messages)
        for turn in kept_turns:
            limited.extend(turn)
        return limited

    def _collect_tool_results(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            message
            for message in messages
            if message.get("role") == "tool" or message.get("tool_call_id")
        ]

    def _normalize_block_name(self, message: Dict[str, Any]) -> str:
        if message.get("role") == "tool":
            return "tool_results"
        block = str(message.get("_context_block") or "")
        if block in {"core_memory", "core"}:
            return "core"
        if block in {"retrieved_memory", "retrieved_memories"}:
            return "retrieved_memories"
        return "recent_turns"

    def _classify_message_block(self, message: Dict[str, Any]) -> str:
        return self._normalize_block_name(message)

    def _plan_context_budget(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        totals = {
            "core": 0,
            "retrieved_memories": 0,
            "recent_turns": 0,
            "tool_results": 0,
        }
        for message in messages:
            totals[self._normalize_block_name(message)] += self._count_messages_tokens([message])

        allocation = {
            "core": min(self.config.core_reserved_tokens, self.config.core_max_tokens),
            "retrieved_memories": min(self.config.retrieved_target_tokens, self.config.retrieved_max_tokens),
            "recent_turns": min(self.config.recent_turns_target_tokens, self.config.recent_turns_max_tokens),
            "tool_results": min(self.config.tool_results_target_tokens, self.config.tool_results_max_tokens),
        }

        remaining = max(0, self.config.total_tokens - sum(allocation.values()))
        growth_order = (
            ("recent_turns", self.config.recent_turns_max_tokens),
            ("retrieved_memories", self.config.retrieved_max_tokens),
            ("core", self.config.core_max_tokens),
            ("tool_results", self.config.tool_results_max_tokens),
        )
        for block, limit in growth_order:
            if remaining <= 0:
                break
            wanted = min(max(0, totals[block] - allocation[block]), max(0, limit - allocation[block]))
            if wanted <= 0:
                continue
            grant = min(remaining, wanted)
            allocation[block] += grant
            remaining -= grant

        return {
            "total": sum(totals.values()),
            "allocation": allocation,
            "required": totals,
            "remaining": remaining,
        }

    def _inject_memories(
        self,
        group_id: str,
        agent_id: str,
        query: str,
        messages: List[Dict[str, Any]],
        *,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        if not self.config.memory_search_enabled:
            return messages
        injected: List[Dict[str, Any]] = []
        core_message = self._build_core_memory_message(group_id=group_id, user_id=user_id)
        if core_message:
            injected.append(core_message)
        retrieved_message = self._build_retrieved_memory_message(
            group_id=group_id,
            agent_id=agent_id,
            query=query,
            user_id=user_id,
        )
        if retrieved_message:
            injected.append(retrieved_message)
        if not injected:
            return messages
        return [*injected, *messages]

    def _build_core_memory_message(
        self,
        *,
        group_id: str,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        memories = self.memory_sys.get_core_memories(user_id=user_id, group_id=group_id)
        if not memories:
            return None
        lines = ["[Core memory]"]
        for index, memory in enumerate(memories, start=1):
            title = f"{memory.title}\n" if memory.title else ""
            lines.append(f"{index}. {memory.scope}\n{title}{memory.content}".strip())
        return {
            "role": "system",
            "content": self._trim_text_to_tokens(
                "\n\n".join(lines),
                self.config.core_max_tokens,
            ),
            "_context_block": "core",
        }

    def _build_retrieved_memory_message(
        self,
        *,
        group_id: str,
        agent_id: str,
        query: str,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        memories = self.memory_sys.search_memories(
            group_id=group_id,
            agent_id=agent_id,
            query=query,
            top_k=self.config.memory_top_k,
            user_id=user_id,
            include_core=False,
            include_daily_logs=True,
            include_domain_cases=True,
        )
        if not memories:
            return None
        lines = ["[Memory context]"]
        for index, memory in enumerate(memories, start=1):
            title = f"{memory.title}\n" if memory.title else ""
            lines.append(f"{index}. {memory.source}\n{title}{memory.content}".strip())
        return {
            "role": "system",
            "content": self._trim_text_to_tokens(
                "\n\n".join(lines),
                self.config.retrieved_max_tokens,
            ),
            "_context_block": "retrieved_memories",
        }

    def _assemble_context(
        self,
        messages: List[Dict[str, Any]],
    ) -> tuple[List[Dict[str, Any]], bool, Dict[str, Any]]:
        total_tokens = self._count_messages_tokens(messages)
        needs_compaction = total_tokens > self.config.soft_threshold_tokens
        plan = self._plan_context_budget(messages)
        block_used = {
            "core": 0,
            "retrieved_memories": 0,
            "recent_turns": 0,
            "tool_results": 0,
        }

        if total_tokens <= self.config.total_tokens:
            for message in messages:
                block = self._normalize_block_name(message)
                block_used[block] += self._count_messages_tokens([message])
            budget_info = {
                "total": total_tokens,
                "used": total_tokens,
                "blocks": block_used,
                "allocation": plan["allocation"],
                "remaining": max(0, self.config.total_tokens - total_tokens),
                "soft_threshold_tokens": self.config.soft_threshold_tokens,
                "window_size": self._get_model_window_size(),
            }
            return messages, needs_compaction, budget_info

        assembled: List[Dict[str, Any]] = []
        used_tokens = 0
        for message in messages:
            block = self._classify_message_block(message)
            block_cap = int(plan["allocation"].get(block, 0))
            remaining_for_block = max(0, block_cap - block_used[block])
            remaining_total = max(0, self.config.total_tokens - used_tokens)
            trimmed = dict(message)
            if remaining_for_block <= 0 and block == "tool_results":
                trimmed["content"] = "[tool result omitted due to budget]"
            else:
                trimmed["content"] = self._trim_text_to_tokens(
                    str(message.get("content", "") or ""),
                    min(remaining_for_block, remaining_total),
                )
            message_tokens = self._count_messages_tokens([trimmed])
            if not trimmed["content"]:
                continue
            if used_tokens + message_tokens > self.config.total_tokens:
                if block == "tool_results":
                    trimmed["content"] = "[tool result omitted due to budget]"
                    message_tokens = self._count_messages_tokens([trimmed])
                else:
                    continue
            assembled.append(trimmed)
            used_tokens += message_tokens
            block_used[block] += message_tokens

        budget_info = {
            "total": total_tokens,
            "used": used_tokens,
            "blocks": block_used,
            "allocation": plan["allocation"],
            "remaining": max(0, self.config.total_tokens - used_tokens),
            "soft_threshold_tokens": self.config.soft_threshold_tokens,
            "window_size": self._get_model_window_size(),
        }
        return assembled, needs_compaction, budget_info

    def _fallback_summary(self, messages: List[Dict[str, Any]]) -> str:
        lines: List[str] = []
        for message in messages[-12:]:
            role = str(message.get("role", "assistant"))
            content = str(message.get("content", "") or "")
            if content:
                lines.append(f"{role}: {content}")
        return self._trim_text_to_tokens("\n".join(lines), 500)

    def _compute_pre_compaction_slice(
        self,
        entries: List[TranscriptEntry],
    ) -> Tuple[List[Dict[str, Any]], Optional[str], Optional[str]]:
        active_entries = self._active_entries_after_latest_compaction(entries)
        if len(active_entries) <= 1:
            return [], None, None

        keep_from_index = 0
        keep_tokens = 0
        for index in range(len(active_entries) - 1, -1, -1):
            entry = active_entries[index]
            message = self._entry_to_message(entry)
            msg_tokens = self._count_messages_tokens([message])
            if keep_tokens + msg_tokens > self.config.keep_recent_tokens:
                keep_from_index = index + 1
                break
            keep_tokens += msg_tokens

        slice_entries = active_entries[:keep_from_index]
        if not slice_entries and len(active_entries) > 1:
            slice_entries = active_entries[:-1]
        if not slice_entries:
            return [], None, None
        slice_messages = [self._entry_to_message(entry) for entry in slice_entries]
        return slice_messages, slice_entries[0].id, slice_entries[-1].id

    def _active_entries_after_latest_compaction(
        self,
        entries: List[TranscriptEntry],
    ) -> List[TranscriptEntry]:
        latest_compaction_index: Optional[int] = None
        for index, entry in enumerate(entries):
            if entry.entry_type == "compaction":
                latest_compaction_index = index

        return [
            entry
            for entry in entries[(latest_compaction_index + 1) if latest_compaction_index is not None else 0 :]
            if entry.entry_type != "compaction"
        ]

    def _build_extraction_key(
        self,
        *,
        session_id: str,
        slice_start_entry_id: str,
        slice_end_entry_id: str,
    ) -> str:
        return ":".join(
            (
                session_id,
                slice_start_entry_id,
                slice_end_entry_id,
                _PRE_COMPACTION_EXTRACTOR_VERSION,
            )
        )

    def _load_pre_compaction_state(
        self,
        *,
        session_id: str,
        group_id: str,
        agent_id: str,
    ) -> Dict[str, Any]:
        session = self.session_mgr.get_session(session_id, group_id, agent_id)
        if not session:
            return {}
        metadata = dict(session.metadata or {})
        payload = metadata.get(_PRE_COMPACTION_STATE_KEY)
        return dict(payload) if isinstance(payload, dict) else {}

    def _persist_pre_compaction_state(
        self,
        *,
        session_id: str,
        group_id: str,
        agent_id: str,
        extraction_key: str,
        slice_start_entry_id: str,
        slice_end_entry_id: str,
        status: str,
    ) -> None:
        session = self.session_mgr.get_session(session_id, group_id, agent_id)
        if not session:
            return
        metadata = dict(session.metadata or {})
        state = dict(metadata.get(_PRE_COMPACTION_STATE_KEY) or {})
        state[extraction_key] = {
            "slice_start_entry_id": slice_start_entry_id,
            "slice_end_entry_id": slice_end_entry_id,
            "extractor_version": _PRE_COMPACTION_EXTRACTOR_VERSION,
            "status": status,
            "processed_at": datetime.now().isoformat(),
        }
        metadata[_PRE_COMPACTION_STATE_KEY] = state
        self.session_mgr.update_session_metadata(session_id, group_id, agent_id, metadata)

    async def _trigger_compaction(
        self,
        group_id: str,
        agent_id: str,
        session_id: str,
        entries: List[TranscriptEntry],
        user_id: str,
    ) -> Dict[str, Any]:
        original_messages = self._entries_to_messages(entries)
        original_tokens = self._count_messages_tokens(original_messages)
        slice_messages, slice_start_entry_id, slice_end_entry_id = self._compute_pre_compaction_slice(entries)
        if not slice_messages or not slice_start_entry_id or not slice_end_entry_id:
            return {
                "success": False,
                "reason": "no messages to summarize",
                "original_tokens": original_tokens,
                "compressed_tokens": original_tokens,
                "memory_flushed": False,
            }

        extraction_key = self._build_extraction_key(
            session_id=session_id,
            slice_start_entry_id=slice_start_entry_id,
            slice_end_entry_id=slice_end_entry_id,
        )
        extraction_state = self._load_pre_compaction_state(
            session_id=session_id,
            group_id=group_id,
            agent_id=agent_id,
        )
        extraction_processed = bool(
            isinstance(extraction_state.get(extraction_key), dict)
            and extraction_state[extraction_key].get("status") == "success"
        )
        memory_flushed = False

        if self.config.memory_flush_enabled and not extraction_processed:
            try:
                flush_result = await self.memory_sys.flush_from_context(
                    group_id,
                    agent_id,
                    "",
                    user_id=user_id,
                    source_session_id=session_id,
                    messages=slice_messages,
                    slice_start_entry_id=slice_start_entry_id,
                    slice_end_entry_id=slice_end_entry_id,
                    extractor_version=_PRE_COMPACTION_EXTRACTOR_VERSION,
                )
                memory_flushed = bool(
                    flush_result.get("flushed")
                    or flush_result.get("core_written")
                    or flush_result.get("domain_case_written")
                )
                self._persist_pre_compaction_state(
                    session_id=session_id,
                    group_id=group_id,
                    agent_id=agent_id,
                    extraction_key=extraction_key,
                    slice_start_entry_id=slice_start_entry_id,
                    slice_end_entry_id=slice_end_entry_id,
                    status="success",
                )
                extraction_processed = True
            except Exception as exc:  # pragma: no cover
                return {
                    "success": False,
                    "reason": f"memory flush failed: {exc}",
                    "original_tokens": original_tokens,
                    "compressed_tokens": original_tokens,
                    "memory_flushed": False,
                }

        active_entries = self._active_entries_after_latest_compaction(entries)
        keep_tokens = self._count_messages_tokens(
            [self._entry_to_message(entry) for entry in active_entries]
        ) - self._count_messages_tokens(slice_messages)

        summary = ""
        try:
            summarize_prompt = (
                "请将以下对话总结为一段简洁摘要，保留用户目标、关键事实、已确认决策、"
                "未完成事项和必要约束。控制在 500 字以内。\n\n"
                f"{json.dumps(slice_messages, ensure_ascii=False)}\n\n摘要："
            )
            summary = await self._call_llm_text(summarize_prompt)
        except Exception as exc:  # pragma: no cover
            print(f"Compaction failed: {exc}")

        if not summary:
            summary = self._fallback_summary(slice_messages)

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
            "memory_flushed": memory_flushed or extraction_processed,
        }

    def _get_model_window_size(self) -> int:
        return 128000

    def _extract_query_from_messages(self, messages: List[Dict[str, Any]]) -> str:
        for message in reversed(messages):
            if message.get("role") == "user" and message.get("content"):
                return str(message["content"])[:200]
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
            compaction_result = await self._trigger_compaction(group_id, agent_id, session_id, entries, user_id)
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

    async def compact_session(
        self,
        group_id: str,
        agent_id: str,
        session_id: str,
    ) -> Dict[str, Any]:
        entries = self.session_mgr.get_transcript(group_id, agent_id, session_id, include_compacted=True)
        session = self.session_mgr.get_session(session_id, group_id, agent_id)
        user_id = session.user_id if session else "default"
        return await self._trigger_compaction(group_id, agent_id, session_id, entries, user_id)

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

    def load_registry(
        self,
        *,
        tenant_id: str,
        group_id: str,
        agent_id: str,
        session_id: str,
    ) -> ContextRegistry:
        return self.registry_mgr.load_registry(session_id, tenant_id, group_id, agent_id)

    def append_registry_entries(
        self,
        *,
        tenant_id: str,
        group_id: str,
        agent_id: str,
        session_id: str,
        entries: list[ContextRegistryEntry],
    ) -> ContextRegistry:
        return self.registry_mgr.append_entries(
            session_id=session_id,
            tenant_id=tenant_id,
            group_id=group_id,
            agent_id=agent_id,
            entries=entries,
        )

    def list_recent_registry_entries(
        self,
        *,
        tenant_id: str,
        group_id: str,
        agent_id: str,
        session_id: str,
        limit: int = 20,
    ) -> list[ContextRegistryEntry]:
        return self.registry_mgr.list_recent_entries(
            session_id=session_id,
            tenant_id=tenant_id,
            group_id=group_id,
            agent_id=agent_id,
            limit=limit,
        )
