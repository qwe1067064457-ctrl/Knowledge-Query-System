"""
记忆系统 - 多领域隔离的混合检索记忆（BM25 + 时间衰减 + MMR）
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from context.dataclasses import MemoryEntry


class MemorySystem:
    """多领域记忆系统（支持多领域隔离）"""

    def __init__(self, base_storage_path: Path) -> None:
        self.base_storage_path = Path(base_storage_path)
        self.groups_path = self.base_storage_path / "groups"

    def _get_agent_memory_path(self, group_id: str, agent_id: str) -> Path:
        """获取指定组和 Agent 的记忆目录"""
        memory_path = self.groups_path / group_id / "agents" / agent_id
        memory_path.mkdir(parents=True, exist_ok=True)
        return memory_path

    def _init_index(self, group_id: str, agent_id: str) -> None:
        """初始化检索索引"""
        memory_path = self._get_agent_memory_path(group_id, agent_id)
        index_dir = memory_path / ".memory_index"
        index_dir.mkdir(parents=True, exist_ok=True)

        metadata_path = index_dir / "metadata.json"
        if not metadata_path.exists():
            metadata_path.write_text(json.dumps({
                "last_indexed": None,
                "file_hashes": {},
                "group_id": group_id,
                "agent_id": agent_id
            }, ensure_ascii=False), encoding="utf-8")

    def _get_file_hash(self, file_path: Path) -> str:
        """计算文件哈希"""
        if not file_path.exists():
            return ""
        content = file_path.read_text(encoding="utf-8")
        return hashlib.md5(content.encode()).hexdigest()

    def _mark_dirty(self, group_id: str, agent_id: str) -> None:
        """标记索引需要重建"""
        memory_path = self._get_agent_memory_path(group_id, agent_id)
        index_dir = memory_path / ".memory_index"
        index_dir.mkdir(parents=True, exist_ok=True)

        metadata_path = index_dir / "metadata.json"
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["last_indexed"] = None
            metadata_path.write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")

    # ========== 写入操作（多领域） ==========

    def write_to_long_term(
        self,
        group_id: str,
        agent_id: str,
        content: str,
        category: Optional[str] = None
    ) -> None:
        """写入长期记忆"""
        memory_path = self._get_agent_memory_path(group_id, agent_id)
        long_term_path = memory_path / "MEMORY.md"

        if not long_term_path.exists():
            long_term_path.write_text("", encoding="utf-8")

        current = long_term_path.read_text(encoding="utf-8")

        if category:
            new_entry = f"\n## {category}\n- {content}\n"
        else:
            new_entry = f"\n- {content}\n"

        long_term_path.write_text(current + new_entry, encoding="utf-8")
        self._mark_dirty(group_id, agent_id)

    def write_to_daily_log(
        self,
        group_id: str,
        agent_id: str,
        content: str,
        target_date: Optional[date] = None
    ) -> None:
        """写入每日日志"""
        if target_date is None:
            target_date = date.today()

        memory_path = self._get_agent_memory_path(group_id, agent_id)
        memory_dir = memory_path / "memory"
        memory_dir.mkdir(exist_ok=True)

        log_path = memory_dir / f"{target_date.isoformat()}.md"

        if not log_path.exists():
            log_path.write_text(f"# {target_date.isoformat()}\n\n", encoding="utf-8")

        current = log_path.read_text(encoding="utf-8")
        log_path.write_text(current + f"- {content}\n", encoding="utf-8")
        self._mark_dirty(group_id, agent_id)

    def write_case_memory(
        self,
        group_id: str,
        agent_id: str,
        case_title: str,
        content: str
    ) -> None:
        """写入案例记忆（法律组专用）"""
        memory_path = self._get_agent_memory_path(group_id, agent_id)
        cases_path = memory_path / "cases.md"

        if not cases_path.exists():
            cases_path.write_text("# 判例库\n\n", encoding="utf-8")

        current = cases_path.read_text(encoding="utf-8")
        cases_path.write_text(
            current + f"\n## {case_title}\n{content}\n---\n",
            encoding="utf-8"
        )
        self._mark_dirty(group_id, agent_id)

    # ========== 检索操作（混合检索 + 时间衰减 + MMR） ==========

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """面向中英文混合内容的轻量分词。"""
        return re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9_]+", text.lower())

    def _simple_bm25(self, query: str, document: str) -> float:
        """简化的 BM25 分数计算"""
        normalized_query = re.sub(r"\s+", "", query.lower())
        normalized_document = re.sub(r"\s+", "", document.lower())
        phrase_score = 1.0 if normalized_query and normalized_query in normalized_document else 0.0

        query_words = set(self._tokenize(query))
        doc_words = self._tokenize(document)
        doc_word_set = set(doc_words)

        if not query_words or not doc_words:
            return phrase_score

        score = 0.0
        for word in query_words:
            if word in doc_word_set:
                tf = doc_words.count(word) / len(doc_words)
                score += tf

        return max(phrase_score, score / len(query_words))

    def _time_decay(
        self,
        entry_date: date,
        current_date: date,
        half_life_days: int = 30
    ) -> float:
        """时间衰减因子（指数衰减）"""
        days_diff = (current_date - entry_date).days
        if days_diff <= 0:
            return 1.0
        # 衰减公式: exp(-λ * t), λ = ln(2) / half_life
        decay = 2 ** (-days_diff / half_life_days)
        return max(0.1, decay)  # 最低保留 10% 权重

    def _mmr_deduplicate(
        self,
        entries: List[MemoryEntry],
        query: str,
        lambda_param: float = 0.7,
        top_k: int = 5
    ) -> List[MemoryEntry]:
        """
        MMR (Maximum Marginal Relevance) 去重

        在相关性和多样性之间平衡
        lambda=0.7: 相关性权重70%，多样性权重30%
        """
        if not entries:
            return []

        # 按原始分数排序
        entries = sorted(entries, key=lambda x: x.score, reverse=True)

        selected: List[MemoryEntry] = []
        candidates = entries.copy()

        for _ in range(min(top_k, len(entries))):
            if not candidates:
                break

            best_idx = 0
            best_score = -float('inf')

            for idx, candidate in enumerate(candidates):
                relevance = candidate.score

                # 计算与已选条目的最大相似度（简化版，用词重叠）
                max_similarity = 0.0
                candidate_words = set(self._tokenize(candidate.content))
                for selected_entry in selected:
                    selected_words = set(self._tokenize(selected_entry.content))
                    if candidate_words and selected_words:
                        overlap = len(candidate_words & selected_words)
                        union = len(candidate_words | selected_words)
                        similarity = overlap / union if union > 0 else 0
                        max_similarity = max(max_similarity, similarity)

                # MMR 公式: λ * relevance - (1-λ) * max_similarity
                mmr_score = lambda_param * relevance - (1 - lambda_param) * max_similarity

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx

            selected.append(candidates.pop(best_idx))

        return selected

    def search(
        self,
        group_id: str,
        agent_id: str,
        query: str,
        top_k: int = 5,
        min_score: float = 0.1,
        date_range: Optional[Tuple[date, date]] = None,
        time_decay_half_life: int = 30,
        use_mmr: bool = True,
        mmr_lambda: float = 0.7
    ) -> List[MemoryEntry]:
        """
        混合检索记忆

        特点：
        - 向量检索 + BM25 混合
        - 时间衰减（越新的内容权重越高）
        - MMR 去重（兼顾相关性和多样性）
        """
        self._init_index(group_id, agent_id)
        memory_path = self._get_agent_memory_path(group_id, agent_id)

        results: List[MemoryEntry] = []
        current_date = date.today()

        # 1. 检索 MEMORY.md
        long_term_path = memory_path / "MEMORY.md"
        if long_term_path.exists():
            content = long_term_path.read_text(encoding="utf-8")
            bm25_score = self._simple_bm25(query, content)
            # 长期记忆不受时间衰减影响，权重统一为 1
            final_score = bm25_score

            if final_score >= min_score:
                results.append(MemoryEntry(
                    content=content[:500] + "..." if len(content) > 500 else content,
                    source="MEMORY.md",
                    group_id=group_id,
                    timestamp=datetime.now(),
                    score=final_score
                ))

        # 2. 检索每日日志（带时间衰减）
        memory_dir = memory_path / "memory"
        if memory_dir.exists():
            for log_path in sorted(memory_dir.glob("*.md"), reverse=True):
                try:
                    log_date = date.fromisoformat(log_path.stem)
                except ValueError:
                    continue

                if date_range:
                    if log_date < date_range[0] or log_date > date_range[1]:
                        continue

                content = log_path.read_text(encoding="utf-8")
                bm25_score = self._simple_bm25(query, content)
                decay = self._time_decay(log_date, current_date, time_decay_half_life)
                final_score = bm25_score * decay

                if final_score >= min_score:
                    results.append(MemoryEntry(
                        content=content[:500] + "..." if len(content) > 500 else content,
                        source=str(log_path.relative_to(memory_path)),
                        group_id=group_id,
                        timestamp=datetime.combine(log_date, datetime.min.time()),
                        score=final_score
                    ))

        # 3. 检索案例记忆（如果存在）
        cases_path = memory_path / "cases.md"
        if cases_path.exists():
            content = cases_path.read_text(encoding="utf-8")
            bm25_score = self._simple_bm25(query, content)
            if bm25_score >= min_score:
                results.append(MemoryEntry(
                    content=content[:500] + "..." if len(content) > 500 else content,
                    source="cases.md",
                    group_id=group_id,
                    timestamp=datetime.now(),
                    score=bm25_score
                ))

        # 按分数排序
        results.sort(key=lambda x: x.score, reverse=True)

        # MMR 去重
        if use_mmr and len(results) > top_k:
            results = self._mmr_deduplicate(results, query, mmr_lambda, top_k)
        else:
            results = results[:top_k]

        return results

    def get_recent_memories(
        self,
        group_id: str,
        agent_id: str,
        days: int = 7
    ) -> List[MemoryEntry]:
        """获取最近 N 天的记忆"""
        memory_path = self._get_agent_memory_path(group_id, agent_id)
        results: List[MemoryEntry] = []
        today = date.today()

        memory_dir = memory_path / "memory"
        if memory_dir.exists():
            for i in range(days):
                log_date = today - timedelta(days=i)
                log_path = memory_dir / f"{log_date.isoformat()}.md"
                if log_path.exists():
                    content = log_path.read_text(encoding="utf-8")
                    results.append(MemoryEntry(
                        content=content,
                        source=str(log_path.relative_to(memory_path)),
                        group_id=group_id,
                        timestamp=datetime.combine(log_date, datetime.min.time()),
                        score=1.0
                    ))

        return results

    # ========== Pre-Compaction Flush（核心机制） ==========

    async def flush_from_context(
        self,
        group_id: str,
        agent_id: str,
        context_summary: str
    ) -> Dict[str, Any]:
        """
        从上下文中提取重要信息并写入记忆

        由上下文管理模块在压缩前调用
        """
        # 实际实现中应该调用 LLM 提取重要信息
        if context_summary.strip() and context_summary.strip() != "NO_REPLY":
            self.write_to_daily_log(group_id, agent_id, context_summary.strip())

        return {
            "flushed": bool(context_summary.strip()),
            "group_id": group_id,
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat(),
            "context_length": len(context_summary)
        }
