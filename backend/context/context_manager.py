"""
上下文管理器 - 三层防线（轮次截断→记忆注入→Token预算组装→压缩）
"""
from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable, Tuple

try:
    import tiktoken
    _HAS_TIKTOKEN = True
except ImportError:
    _HAS_TIKTOKEN = False

from context.session_manager import SessionManager
from context.memory_system import MemorySystem
from context.dataclasses import TranscriptEntry


@dataclass
class ContextConfig:
    """上下文管理配置"""
    # 第一道防线
    max_turns: int = 8  # 保留最近 N 轮（知识库场景用 8-10）

    # 第二道防线
    reserve_tokens: int = 20000  # 为响应预留的 token
    tool_result_max_chars: int = 8000  # 单条工具结果最大字符数
    image_max_dimension_px: int = 1200  # 图片最大边长

    # 记忆注入配置
    memory_search_enabled: bool = True
    memory_top_k: int = 5  # 检索多少条记忆
    memory_time_decay_half_life: int = 30  # 时间衰减半衰期（天）
    memory_use_mmr: bool = True  # 是否使用 MMR 去重
    memory_mmr_lambda: float = 0.7  # MMR 相关性权重

    # 第三道防线
    compaction_enabled: bool = True
    soft_threshold_tokens: int = 40000  # 触发压缩的 token 阈值
    keep_recent_tokens: int = 20000  # 压缩后保留的 token 数
    compaction_model: Optional[str] = None

    # Memory Flush
    memory_flush_enabled: bool = True
    memory_flush_threshold: int = 38000  # 略低于压缩阈值


class ContextManager:
    """
    上下文管理器（集成会话管理和记忆系统）

    职责：
    1. 从会话管理获取历史对话
    2. 从记忆系统检索相关记忆
    3. 执行三层防线压缩
    4. 生成准备发送给 LLM 的上下文
    """

    def __init__(
        self,
        session_manager: SessionManager,
        memory_system: MemorySystem
    ) -> None:
        self.session_mgr = session_manager
        self.memory_sys = memory_system

        if _HAS_TIKTOKEN:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        else:
            # 简单回退：按字符数估算（1 token ≈ 4 字符）
            self.tokenizer = None

        # 配置（可运行时修改）
        self.config = ContextConfig()

        # LLM 调用接口（由外部注入，仅用于 compaction）
        self.llm_call: Optional[Callable] = None

    def set_llm_call(self, llm_call: Callable) -> None:
        """设置 LLM 调用函数（用于压缩和记忆提取）"""
        self.llm_call = llm_call

    async def _call_llm_text(self, prompt: str) -> str:
        """调用外部注入的 LLM，并统一提取文本。"""
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
            parts: list[str] = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(str(block.get("text", "")))
                else:
                    parts.append(str(block))
            return "".join(parts)
        return str(content or "")

    def _count_tokens(self, text: str) -> int:
        """计算 token 数量"""
        if not text:
            return 0
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        # 回退：按字符数估算
        return max(1, len(text) // 4)

    def _count_messages_tokens(self, messages: List[Dict]) -> int:
        """计算消息列表的总 token 数"""
        total = 0
        for msg in messages:
            if msg.get("content"):
                total += self._count_tokens(str(msg["content"]))
            if msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    total += self._count_tokens(str(tc))
        return total

    def _limit_history_turns(self, messages: List[Dict]) -> List[Dict]:
        """第一道防线：按轮次硬截断"""
        if self.config.max_turns <= 0:
            return messages

        user_indices = [
            i for i, msg in enumerate(messages) if msg.get("role") == "user"
        ]
        if len(user_indices) <= self.config.max_turns:
            return messages

        keep_from = user_indices[-self.config.max_turns]
        leading_system = [
            msg for msg in messages[:keep_from] if msg.get("role") == "system"
        ]
        return leading_system + messages[keep_from:]

    def _entry_to_message(self, entry: TranscriptEntry) -> Dict[str, Any]:
        """将转录条目转换为 LLM 消息。"""
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
        """从转录中恢复有效上下文，只展开最近一次压缩后的消息。"""
        latest_compaction_index: Optional[int] = None
        for index, entry in enumerate(entries):
            if entry.entry_type == "compaction" and entry.content:
                latest_compaction_index = index

        messages: List[Dict[str, Any]] = []
        start_index = 0
        if latest_compaction_index is not None:
            compaction = entries[latest_compaction_index]
            messages.append({
                "role": "system",
                "content": f"[以下是之前对话的摘要]\n{compaction.content}",
            })
            start_index = latest_compaction_index + 1

        for entry in entries[start_index:]:
            if entry.entry_type == "compaction":
                continue
            messages.append(self._entry_to_message(entry))

        if extra_messages:
            messages.extend(extra_messages)

        return messages

    def _inject_memories(
        self,
        group_id: str,
        agent_id: str,
        query: str,
        messages: List[Dict]
    ) -> List[Dict]:
        """
        注入相关记忆

        在截断后，根据当前对话内容检索相关记忆并注入上下文
        """
        if not self.config.memory_search_enabled:
            return messages

        # 检索相关记忆
        memories = self.memory_sys.search(
            group_id=group_id,
            agent_id=agent_id,
            query=query,
            top_k=self.config.memory_top_k,
            time_decay_half_life=self.config.memory_time_decay_half_life,
            use_mmr=self.config.memory_use_mmr,
            mmr_lambda=self.config.memory_mmr_lambda
        )

        if not memories:
            return messages

        # 构建记忆注入的 system 消息
        memory_content = "## 相关记忆（供参考）\n\n"
        for mem in memories:
            mem_time = mem.timestamp.strftime("%Y-%m-%d") if mem.timestamp else "unknown"
            memory_content += f"**来源: {mem.source}** ({mem_time})\n"
            memory_content += f"{mem.content}\n\n"

        # 插入到消息列表开头（系统消息之后）
        # 假设第一条是 system 消息，在其后插入
        if messages and messages[0].get("role") == "system":
            messages.insert(1, {
                "role": "system",
                "content": memory_content
            })
        else:
            messages.insert(0, {
                "role": "system",
                "content": memory_content
            })

        return messages

    def _assemble_context(
        self,
        messages: List[Dict]
    ) -> Tuple[List[Dict], bool]:
        """第二道防线：Token 预算感知组装"""
        # 裁剪过长的工具结果
        for msg in messages:
            if msg.get("role") == "tool" and "content" in msg:
                content = msg["content"]
                if len(content) > self.config.tool_result_max_chars:
                    msg["content"] = content[:self.config.tool_result_max_chars] + "...[truncated]"

        current_tokens = self._count_messages_tokens(messages)
        model_window = self._get_model_window_size()
        model_budget = max(0, model_window - self.config.reserve_tokens)
        threshold = min(self.config.soft_threshold_tokens, model_budget)
        needs_compaction = current_tokens > threshold

        return messages, needs_compaction

    def _fallback_summary(self, messages: List[Dict[str, Any]]) -> str:
        """无外部 LLM 时的确定性摘要回退，保证压缩流程可完成。"""
        if not messages:
            return ""
        lines = []
        for message in messages[:12]:
            role = message.get("role", "assistant")
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
        messages: List[Dict]
    ) -> Dict[str, Any]:
        """第三道防线：触发压缩"""
        if not self.config.compaction_enabled:
            return {"success": False, "reason": "compaction disabled"}

        original_tokens = self._count_messages_tokens(messages)

        # 1. Pre-Compaction Memory Flush
        memory_flushed = False
        if self.config.memory_flush_enabled:
            try:
                # 提取重要信息
                context_str = json.dumps(messages[-50:], ensure_ascii=False)
                flush_prompt = f"""
你即将失去当前上下文。请从中提取对你主人重要的信息：
- 用户偏好（查询风格、格式要求）
- 已做出的决策
- 重要的事实或约束

将这些以 Markdown 列表格式输出。
如果没有任何值得记录的内容，回复 NO_REPLY。

上下文：
{context_str[:8000]}
"""
                important_info = await self._call_llm_text(flush_prompt)
                if important_info and important_info.strip() != "NO_REPLY":
                    self.memory_sys.write_to_daily_log(
                        group_id, agent_id, important_info
                    )
                    memory_flushed = True
            except Exception as e:
                print(f"Memory flush failed: {e}")

        # 2. 寻找压缩边界
        keep_from_index = 0
        keep_tokens = 0
        for i in range(len(messages) - 1, -1, -1):
            msg_tokens = self._count_messages_tokens([messages[i]])
            if keep_tokens + msg_tokens > self.config.keep_recent_tokens:
                keep_from_index = i + 1
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

        # 3. 生成摘要
        summary = ""
        if to_summarize:
            try:
                summarize_prompt = f"""
请将以下对话总结为一段简洁的摘要（不超过 500 字），保留关键信息和决策：

{json.dumps(to_summarize, ensure_ascii=False)}

摘要：
"""
                summary = await self._call_llm_text(summarize_prompt)
            except Exception as e:
                print(f"Compaction failed: {e}")
                summary = f"[Compaction failed: {e}]"
        if not summary:
            summary = self._fallback_summary(to_summarize)

        # 4. 写回会话转录
        if summary:
            # 获取会话信息
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
                    token_count=self._count_tokens(summary)
                )
                self.session_mgr.append_entry(group_id, agent_id, compaction_entry)

        compressed_tokens = self._count_messages_tokens([{"content": summary}]) + keep_tokens

        return {
            "success": True,
            "summary": summary,
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "memory_flushed": memory_flushed
        }

    def _get_model_window_size(self) -> int:
        """获取当前模型的上下文窗口大小"""
        # 从配置或环境变量获取
        return 128000  # 默认 128K

    def _extract_query_from_messages(self, messages: List[Dict]) -> str:
        """从消息列表中提取当前查询（用于记忆检索）"""
        # 取最后一条 user 消息作为查询
        for msg in reversed(messages):
            if msg.get("role") == "user" and msg.get("content"):
                content = msg["content"]
                if len(content) > 200:
                    content = content[:200]
                return content
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
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        准备上下文（主入口）

        执行完整的预处理管道：
        1. 获取转录
        2. 第一道防线（轮次截断）
        3. 记忆检索与注入
        4. 第二道防线（Token 组装）
        5. 如需压缩，递归重试
        """
        # 覆盖配置
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

        # 1. 获取原始转录
        entries = self.session_mgr.get_transcript(
            group_id, agent_id, session_id, include_compacted=True
        )
        messages = self._entries_to_messages(entries, extra_messages)

        if not messages:
            return {
                "messages": [],
                "total_tokens": 0,
                "needs_compaction": False
            }

        # 2. 第一道防线：轮次截断
        messages = self._limit_history_turns(messages)

        # 3. 提取查询并注入记忆
        active_query = query or self._extract_query_from_messages(messages)
        if active_query:
            messages = self._inject_memories(group_id, agent_id, active_query, messages)

        # 4. 第二道防线：Token 预算组装
        messages, needs_compaction = self._assemble_context(messages)

        # 5. 检查是否需要压缩
        compaction_result: Optional[Dict[str, Any]] = None
        if (
            allow_compaction
            and needs_compaction
            and self.config.compaction_enabled
            and _compaction_attempt < 1
        ):
            # 执行压缩
            compaction_result = await self._trigger_compaction(
                group_id, agent_id, session_id, messages
            )

            # 递归重试（压缩后重新准备上下文）
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
        }

    async def prepare_messages(
        self,
        group_id: str,
        agent_id: str,
        messages: List[Dict[str, Any]],
        query: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """优化一组内存中的消息，供旧会话接口或测试直接使用。"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

        prepared = list(messages)
        if not prepared:
            return {
                "messages": [],
                "total_tokens": 0,
                "needs_compaction": False,
            }

        prepared = self._limit_history_turns(prepared)
        active_query = query or self._extract_query_from_messages(prepared)
        if active_query:
            prepared = self._inject_memories(group_id, agent_id, active_query, prepared)
        prepared, needs_compaction = self._assemble_context(prepared)
        return {
            "messages": prepared,
            "total_tokens": self._count_messages_tokens(prepared),
            "needs_compaction": needs_compaction,
        }

    def get_status(
        self,
        group_id: str,
        agent_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """获取上下文状态（用于监控）"""
        entries = self.session_mgr.get_transcript(
            group_id, agent_id, session_id, include_compacted=True
        )
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
            "max_turns": self.config.max_turns
        }
