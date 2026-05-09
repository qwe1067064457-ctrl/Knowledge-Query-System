"""
Scoped memory system for per-user core memory, daily logs, and group-shared cases.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

from context.dataclasses import MemoryEntry, MemoryScope, MemoryType
from memory_system.policy_loader import MemoryPolicyLoader


class MemorySystem:
    """
    Memory system with explicit scope boundaries.

    Supported memory layers:
    - core memory: user_global / user_group
    - daily log: user_group
    - domain case: group_shared
    """

    def __init__(self, base_storage_path: Path) -> None:
        self.base_storage_path = Path(base_storage_path)
        self.users_path = self.base_storage_path / "users"
        self.groups_path = self.base_storage_path / "groups"
        self.users_path.mkdir(parents=True, exist_ok=True)
        self.groups_path.mkdir(parents=True, exist_ok=True)
        self.policy_loader = MemoryPolicyLoader(self.base_storage_path)

    @staticmethod
    def _safe_segment(value: str, field_name: str) -> str:
        if not value or not re.fullmatch(r"[A-Za-z0-9_.@-]+", value):
            raise ValueError(
                f"{field_name} must only contain letters, numbers, dot, dash, underscore or @"
            )
        return value

    def _safe_group_id(self, group_id: str) -> str:
        return self._safe_segment(group_id, "group_id")

    def _safe_user_id(self, user_id: str) -> str:
        return self._safe_segment(user_id, "user_id")

    def _user_global_dir(self, user_id: str) -> Path:
        path = self.users_path / self._safe_user_id(user_id) / "global"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _user_group_dir(self, user_id: str, group_id: str) -> Path:
        path = self.users_path / self._safe_user_id(user_id) / "groups" / self._safe_group_id(group_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _group_shared_dir(self, group_id: str) -> Path:
        path = self.groups_path / self._safe_group_id(group_id) / "shared"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _core_file(self, user_id: str, scope: MemoryScope, group_id: Optional[str] = None) -> Path:
        if scope == "user_global":
            return self._user_global_dir(user_id) / "core.json"
        if scope == "user_group":
            if not group_id:
                raise ValueError("group_id is required for user_group core memory")
            return self._user_group_dir(user_id, group_id) / "core.json"
        raise ValueError("core memory does not support group_shared scope")

    def _daily_log_dir(self, user_id: str, group_id: str) -> Path:
        path = self._user_group_dir(user_id, group_id) / "daily_logs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _domain_cases_file(self, group_id: str) -> Path:
        return self._group_shared_dir(group_id) / "domain_cases.jsonl"

    @staticmethod
    def _now() -> datetime:
        return datetime.now()

    @staticmethod
    def _make_record(
        *,
        scope: MemoryScope,
        memory_type: MemoryType,
        content: str,
        group_id: str,
        user_id: Optional[str] = None,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
        source_session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        now = timestamp or datetime.now()
        return {
            "id": f"mem_{uuid.uuid4().hex}",
            "scope": scope,
            "memory_type": memory_type,
            "title": title,
            "content": content.strip(),
            "tags": tags or [],
            "group_id": group_id,
            "user_id": user_id,
            "source_session_id": source_session_id,
            "metadata": metadata or {},
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

    @staticmethod
    def _read_json(path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return default

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    @staticmethod
    def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
        if not path.exists():
            return []
        rows: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return rows

    @staticmethod
    def _dedupe_core_records(records: List[Dict[str, Any]], incoming: Dict[str, Any]) -> List[Dict[str, Any]]:
        signature = re.sub(r"\s+", " ", incoming["content"].strip())
        for record in records:
            existing = re.sub(r"\s+", " ", str(record.get("content", "")).strip())
            if existing == signature:
                record["updated_at"] = incoming["updated_at"]
                if incoming.get("title"):
                    record["title"] = incoming["title"]
                if incoming.get("tags"):
                    record["tags"] = sorted(set(record.get("tags", [])) | set(incoming["tags"]))
                if incoming.get("source_session_id"):
                    record["source_session_id"] = incoming["source_session_id"]
                if incoming.get("metadata"):
                    record["metadata"] = {**record.get("metadata", {}), **incoming["metadata"]}
                return records
        records.append(incoming)
        return records

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9_]+", text.lower())

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        parts = re.split(r"[\n。！？!?；;]+", text)
        return [part.strip(" -\t") for part in parts if part.strip()]

    def _load_policy(self, group_id: str) -> Dict[str, Any]:
        return self.policy_loader.load_policy(self._safe_group_id(group_id))

    @staticmethod
    def _enabled(memory_type: str, policy: Dict[str, Any]) -> bool:
        enabled = policy.get("enabled_memory_types", [])
        return memory_type in enabled if isinstance(enabled, list) else True

    @staticmethod
    def _core_policy(policy: Dict[str, Any]) -> Dict[str, Any]:
        return cast(Dict[str, Any], policy.get("core", {}))

    @staticmethod
    def _daily_log_policy(policy: Dict[str, Any]) -> Dict[str, Any]:
        return cast(Dict[str, Any], policy.get("daily_log", {}))

    @staticmethod
    def _domain_case_policy(policy: Dict[str, Any]) -> Dict[str, Any]:
        return cast(Dict[str, Any], policy.get("domain_case", {}))

    def _has_explicit_long_term_signal(self, text: str, policy: Dict[str, Any]) -> bool:
        markers = self._core_policy(policy).get("explicit_markers", [])
        return any(marker in text for marker in markers)

    def _classify_core_scope(self, content: str, policy: Dict[str, Any]) -> MemoryScope:
        group_keywords = self._core_policy(policy).get("group_scope_keywords", [])
        if any(keyword in content for keyword in group_keywords):
            return "user_group"
        return "user_global"

    def _extract_core_candidates(
        self,
        messages: List[Dict[str, Any]],
        policy: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        if not self._enabled("core", policy):
            return []

        min_len = int(self._core_policy(policy).get("min_candidate_length", 6))
        max_len = int(self._core_policy(policy).get("max_candidate_length", 120))
        candidates: List[Dict[str, str]] = []
        seen: set[str] = set()
        for message in messages:
            if message.get("role") != "user":
                continue
            content = str(message.get("content", "") or "").strip()
            for sentence in self._split_sentences(content):
                if not self._has_explicit_long_term_signal(sentence, policy):
                    continue
                if len(sentence) < min_len or len(sentence) > max_len:
                    continue
                scope = self._classify_core_scope(sentence, policy)
                signature = f"{scope}:{sentence}"
                if signature in seen:
                    continue
                seen.add(signature)
                candidates.append({"scope": scope, "content": sentence})
        return candidates

    def _looks_like_completed_result(self, text: str, policy: Dict[str, Any]) -> bool:
        markers = self._domain_case_policy(policy).get("completion_markers", [])
        return any(marker in text for marker in markers)

    def _looks_like_case_body(self, text: str, policy: Dict[str, Any]) -> bool:
        structural = self._domain_case_policy(policy).get("structural_markers", [])
        case_markers = self._domain_case_policy(policy).get("case_markers", [])
        hits = sum(1 for marker in structural if marker in text)
        return hits >= 2 or any(marker in text for marker in case_markers)

    def _extract_domain_case_candidate(
        self,
        group_id: str,
        messages: List[Dict[str, Any]],
        summary: str,
        policy: Dict[str, Any],
    ) -> Optional[Dict[str, str]]:
        if not self._enabled("domain_case", policy):
            return None

        source_text = summary.strip()
        if not source_text:
            for message in reversed(messages):
                if message.get("role") == "assistant" and message.get("content"):
                    source_text = str(message["content"]).strip()
                    break

        if not source_text:
            return None
        if not self._looks_like_completed_result(source_text, policy):
            return None
        if not self._looks_like_case_body(source_text, policy):
            return None

        title_seed = ""
        for message in reversed(messages):
            if message.get("role") == "user" and message.get("content"):
                title_seed = str(message["content"]).strip()
                break
        title_seed = title_seed[:24] if title_seed else "会话案例"
        return {"title": f"{group_id}::{title_seed}", "content": source_text}

    def _simple_bm25(self, query: str, document: str) -> float:
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
                score += doc_words.count(word) / len(doc_words)
        return max(phrase_score, score / len(query_words))

    @staticmethod
    def _time_decay(entry_date: date, current_date: date, half_life_days: int = 30) -> float:
        days_diff = (current_date - entry_date).days
        if days_diff <= 0:
            return 1.0
        return max(0.1, 2 ** (-days_diff / half_life_days))

    def _to_memory_entry(self, record: Dict[str, Any], *, source: str, score: float = 0.0) -> MemoryEntry:
        timestamp_raw = record.get("updated_at") or record.get("created_at") or self._now().isoformat()
        timestamp = (
            datetime.fromisoformat(timestamp_raw)
            if isinstance(timestamp_raw, str)
            else datetime.fromtimestamp(float(timestamp_raw))
        )
        return MemoryEntry(
            content=str(record.get("content", "")),
            source=source,
            group_id=str(record.get("group_id", "")),
            timestamp=timestamp,
            score=score,
            scope=record.get("scope", "user_group"),
            memory_type=record.get("memory_type", "daily_log"),
            user_id=record.get("user_id"),
            title=record.get("title"),
            tags=record.get("tags") or [],
        )

    def capture_checkpoint(
        self,
        *,
        group_id: str,
        agent_id: str,
        user_id: str,
        messages: List[Dict[str, Any]],
        summary: str,
        source_session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        policy = self._load_policy(group_id)
        summary = summary.strip()
        daily_log_written = False
        core_written = 0
        case_written = 0

        if self._enabled("daily_log", policy) and self._daily_log_policy(policy).get("checkpoint_enabled", True):
            if summary and summary != "NO_REPLY":
                self.write_daily_log(
                    group_id,
                    agent_id,
                    summary,
                    user_id=user_id,
                    source_session_id=source_session_id,
                )
                daily_log_written = True

        for candidate in self._extract_core_candidates(messages, policy):
            scope = cast(MemoryScope, candidate["scope"])
            self.write_core_memory(
                user_id=user_id,
                group_id=group_id if scope == "user_group" else None,
                scope=scope,
                content=candidate["content"],
                source_session_id=source_session_id,
            )
            core_written += 1

        case_candidate = self._extract_domain_case_candidate(group_id, messages, summary, policy)
        if case_candidate:
            self.write_domain_case(
                group_id=group_id,
                title=case_candidate["title"],
                content=case_candidate["content"],
                source_session_id=source_session_id,
            )
            case_written += 1

        return {
            "daily_log_written": daily_log_written,
            "core_written": core_written,
            "domain_case_written": case_written,
        }

    def write_core_memory(
        self,
        *,
        user_id: str,
        group_id: Optional[str],
        scope: MemoryScope,
        content: str,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
        source_session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if scope not in {"user_global", "user_group"}:
            raise ValueError("core memory only supports user_global or user_group scope")
        target = self._core_file(user_id, scope, group_id=group_id)
        payload = self._read_json(target, {"items": []})
        record = self._make_record(
            scope=scope,
            memory_type="core",
            content=content,
            group_id=group_id or "__global__",
            user_id=user_id,
            title=title,
            tags=tags,
            source_session_id=source_session_id,
            metadata=metadata,
        )
        payload["items"] = self._dedupe_core_records(payload.get("items", []), record)
        self._write_json(target, payload)

    def write_daily_log(
        self,
        group_id: str,
        agent_id: str,
        content: str,
        target_date: Optional[date] = None,
        *,
        user_id: str = "default",
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
        source_session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        del agent_id
        if target_date is None:
            target_date = date.today()
        target = self._daily_log_dir(user_id, group_id) / f"{target_date.isoformat()}.jsonl"
        record = self._make_record(
            scope="user_group",
            memory_type="daily_log",
            content=content,
            group_id=group_id,
            user_id=user_id,
            title=title,
            tags=tags,
            source_session_id=source_session_id,
            metadata=metadata,
            timestamp=datetime.combine(target_date, datetime.min.time()),
        )
        self._append_jsonl(target, record)

    def write_to_daily_log(
        self,
        group_id: str,
        agent_id: str,
        content: str,
        target_date: Optional[date] = None,
        *,
        user_id: str = "default",
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
        source_session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.write_daily_log(
            group_id,
            agent_id,
            content,
            target_date=target_date,
            user_id=user_id,
            title=title,
            tags=tags,
            source_session_id=source_session_id,
            metadata=metadata,
        )

    def write_domain_case(
        self,
        *,
        group_id: str,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
        source_session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        target = self._domain_cases_file(group_id)
        record = self._make_record(
            scope="group_shared",
            memory_type="domain_case",
            content=content,
            group_id=group_id,
            user_id=None,
            title=title,
            tags=tags,
            source_session_id=source_session_id,
            metadata=metadata,
        )
        self._append_jsonl(target, record)

    def get_core_memories(self, *, user_id: str, group_id: str) -> List[MemoryEntry]:
        entries: List[MemoryEntry] = []
        owners = [user_id]
        if user_id != "default":
            owners.append("default")

        seen: set[tuple[str, str, str]] = set()
        for owner in owners:
            global_file = self._core_file(owner, "user_global")
            for item in self._read_json(global_file, {"items": []}).get("items", []):
                entry = self._to_memory_entry(item, source=str(global_file.relative_to(self.base_storage_path)))
                key = (entry.scope, entry.title or "", entry.content)
                if key not in seen:
                    seen.add(key)
                    entries.append(entry)

            group_file = self._core_file(owner, "user_group", group_id=group_id)
            for item in self._read_json(group_file, {"items": []}).get("items", []):
                entry = self._to_memory_entry(item, source=str(group_file.relative_to(self.base_storage_path)))
                key = (entry.scope, entry.title or "", entry.content)
                if key not in seen:
                    seen.add(key)
                    entries.append(entry)
        return entries

    def _search_core_memories(self, *, user_id: str, group_id: str, query: str, min_score: float) -> List[MemoryEntry]:
        results: List[MemoryEntry] = []
        for item in self.get_core_memories(user_id=user_id, group_id=group_id):
            score = self._simple_bm25(query, f"{item.title or ''}\n{item.content}")
            boosted_score = min(1.5, score + 0.35)
            if boosted_score >= min_score:
                item.score = boosted_score
                results.append(item)
        return results

    def _search_daily_logs(
        self,
        *,
        user_id: str,
        group_id: str,
        query: str,
        min_score: float,
        date_range: Optional[Tuple[date, date]],
        time_decay_half_life: int,
    ) -> List[MemoryEntry]:
        results: List[MemoryEntry] = []
        current_date = date.today()
        daily_dir = self._daily_log_dir(user_id, group_id)
        for log_path in sorted(daily_dir.glob("*.jsonl"), reverse=True):
            try:
                log_date = date.fromisoformat(log_path.stem)
            except ValueError:
                continue
            if date_range and not (date_range[0] <= log_date <= date_range[1]):
                continue
            for item in self._read_jsonl(log_path):
                text = f"{item.get('title', '')}\n{item.get('content', '')}"
                score = self._simple_bm25(query, text) * self._time_decay(log_date, current_date, time_decay_half_life)
                if score >= min_score:
                    results.append(self._to_memory_entry(item, source=str(log_path.relative_to(self.base_storage_path)), score=score))
        return results

    def _search_domain_cases(self, *, group_id: str, query: str, min_score: float) -> List[MemoryEntry]:
        results: List[MemoryEntry] = []
        cases_path = self._domain_cases_file(group_id)
        for item in self._read_jsonl(cases_path):
            text = f"{item.get('title', '')}\n{item.get('content', '')}"
            score = self._simple_bm25(query, text)
            if score >= min_score:
                results.append(self._to_memory_entry(item, source=str(cases_path.relative_to(self.base_storage_path)), score=score))
        return results

    def _mmr_deduplicate(self, entries: List[MemoryEntry], lambda_param: float = 0.7, top_k: int = 5) -> List[MemoryEntry]:
        if not entries:
            return []

        ranked = sorted(entries, key=lambda item: item.score, reverse=True)
        selected: List[MemoryEntry] = []
        candidates = ranked.copy()

        for _ in range(min(top_k, len(ranked))):
            if not candidates:
                break
            best_index = 0
            best_score = -float("inf")
            for index, candidate in enumerate(candidates):
                relevance = candidate.score
                max_similarity = 0.0
                candidate_words = set(self._tokenize(candidate.content))
                for chosen in selected:
                    chosen_words = set(self._tokenize(chosen.content))
                    if not candidate_words or not chosen_words:
                        continue
                    overlap = len(candidate_words & chosen_words)
                    union = len(candidate_words | chosen_words)
                    similarity = overlap / union if union else 0.0
                    max_similarity = max(max_similarity, similarity)
                mmr_score = lambda_param * relevance - (1 - lambda_param) * max_similarity
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_index = index
            selected.append(candidates.pop(best_index))

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
        mmr_lambda: float = 0.7,
        *,
        user_id: str = "default",
        include_core: bool = True,
        include_daily_logs: bool = True,
        include_domain_cases: bool = True,
    ) -> List[MemoryEntry]:
        del agent_id
        group_id = self._safe_group_id(group_id)
        user_id = self._safe_user_id(user_id)

        results: List[MemoryEntry] = []
        if include_core:
            results.extend(self._search_core_memories(user_id=user_id, group_id=group_id, query=query, min_score=min_score))
        if include_daily_logs:
            results.extend(
                self._search_daily_logs(
                    user_id=user_id,
                    group_id=group_id,
                    query=query,
                    min_score=min_score,
                    date_range=date_range,
                    time_decay_half_life=time_decay_half_life,
                )
            )
        if include_domain_cases:
            results.extend(self._search_domain_cases(group_id=group_id, query=query, min_score=min_score))

        results.sort(key=lambda item: item.score, reverse=True)
        if use_mmr and len(results) > top_k:
            return self._mmr_deduplicate(results, lambda_param=mmr_lambda, top_k=top_k)
        return results[:top_k]

    def get_recent_memories(self, group_id: str, agent_id: str, days: int = 7, *, user_id: str = "default") -> List[MemoryEntry]:
        del agent_id
        results: List[MemoryEntry] = []
        today = date.today()
        log_dir = self._daily_log_dir(user_id, group_id)
        for offset in range(days):
            target = today - timedelta(days=offset)
            log_path = log_dir / f"{target.isoformat()}.jsonl"
            for item in self._read_jsonl(log_path):
                results.append(
                    self._to_memory_entry(
                        item,
                        source=str(log_path.relative_to(self.base_storage_path)),
                        score=1.0,
                    )
                )
        return results

    async def flush_from_context(
        self,
        group_id: str,
        agent_id: str,
        context_summary: str,
        *,
        user_id: str = "default",
        source_session_id: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        content = context_summary.strip()
        checkpoint = self.capture_checkpoint(
            group_id=group_id,
            agent_id=agent_id,
            user_id=user_id,
            messages=messages or [],
            summary=content,
            source_session_id=source_session_id,
        )
        return {
            "flushed": checkpoint["daily_log_written"],
            "group_id": group_id,
            "user_id": user_id,
            "timestamp": self._now().isoformat(),
            "context_length": len(context_summary),
            "core_written": checkpoint["core_written"],
            "domain_case_written": checkpoint["domain_case_written"],
        }

    def get_storage_fingerprint(self, *, group_id: str, user_id: str) -> str:
        digest = hashlib.md5()
        paths = [
            self._core_file(user_id, "user_global"),
            self._core_file(user_id, "user_group", group_id=group_id),
            *sorted(self._daily_log_dir(user_id, group_id).glob("*.jsonl")),
            self._domain_cases_file(group_id),
        ]
        for path in paths:
            if path.exists():
                digest.update(path.read_bytes())
        return digest.hexdigest()
