from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import GroupRecord, MemberRole, MembershipRecord, UserRecord


class GroupManagementError(Exception):
    """Base exception for group management failures."""


class NotFoundError(GroupManagementError):
    pass


class ConflictError(GroupManagementError):
    pass


class ValidationError(GroupManagementError):
    pass


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base)
    for key, value in override.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(existing, value)
        else:
            merged[key] = value
    return merged


class GroupManagementService:
    def __init__(self, backend_dir: Path) -> None:
        self.backend_dir = Path(backend_dir)
        self.storage_dir = self.backend_dir / "storage"
        self.users_dir = self.storage_dir / "users"
        self.groups_dir = self.storage_dir / "groups"
        self.knowledge_groups_dir = self.backend_dir / "knowledge" / "groups"
        self._lock = threading.RLock()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _safe_segment(value: str, field_name: str) -> str:
        if not value or not re.fullmatch(r"[A-Za-z0-9_.@-]+", value):
            raise ValidationError(
                f"{field_name} must only contain letters, numbers, dot, dash, underscore or @"
            )
        return value

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
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _users_registry_path(self) -> Path:
        return self.users_dir / "registry.json"

    def _groups_registry_path(self) -> Path:
        return self.groups_dir / "registry.json"

    def _user_profile_path(self, user_id: str) -> Path:
        return self.users_dir / self._safe_segment(user_id, "user_id") / "profile.json"

    def _group_meta_path(self, group_id: str) -> Path:
        return self.groups_dir / self._safe_segment(group_id, "group_id") / "meta.json"

    def _group_members_path(self, group_id: str) -> Path:
        return self.groups_dir / self._safe_segment(group_id, "group_id") / "members.json"

    def _knowledge_group_dir(self, group_id: str) -> Path:
        return self.knowledge_groups_dir / self._safe_segment(group_id, "group_id")

    def _load_default_memory_policy(self) -> dict[str, Any]:
        policy_path = self.backend_dir / "memory_system" / "policy.default.json"
        payload = self._read_json(policy_path, {})
        policy = payload.get("memory_policy", {})
        return dict(policy) if isinstance(policy, dict) else {}

    def _load_registry(self, path: Path) -> list[dict[str, Any]]:
        payload = self._read_json(path, {"items": []})
        items = payload.get("items", []) if isinstance(payload, dict) else []
        return [item for item in items if isinstance(item, dict)]

    def _write_registry(self, path: Path, items: list[dict[str, Any]]) -> None:
        self._write_json(path, {"items": sorted(items, key=lambda item: str(item.get("id", "")))})

    def _upsert_registry_item(self, path: Path, item: dict[str, Any]) -> None:
        items = self._load_registry(path)
        updated = False
        for index, existing in enumerate(items):
            if existing.get("id") == item.get("id"):
                items[index] = item
                updated = True
                break
        if not updated:
            items.append(item)
        self._write_registry(path, items)

    def _ensure_group_layout(self, group: GroupRecord) -> None:
        group_dir = self.groups_dir / group.id
        shared_dir = group_dir / "shared"
        knowledge_dir = self._knowledge_group_dir(group.id)
        documents_dir = knowledge_dir / "documents"
        uploads_dir = knowledge_dir / "uploads"

        shared_dir.mkdir(parents=True, exist_ok=True)
        documents_dir.mkdir(parents=True, exist_ok=True)
        uploads_dir.mkdir(parents=True, exist_ok=True)
        (shared_dir / "domain_cases.jsonl").touch(exist_ok=True)
        (documents_dir / ".gitkeep").touch(exist_ok=True)
        (uploads_dir / ".gitkeep").touch(exist_ok=True)
        readme = knowledge_dir / "README.md"
        if not readme.exists():
            readme.write_text(
                f"# {group.name}\n\nGroup knowledge base for `{group.id}`.\n",
                encoding="utf-8",
            )

    def create_user(
        self,
        *,
        user_id: str,
        display_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        user_id = self._safe_segment(user_id, "user_id")
        with self._lock:
            profile_path = self._user_profile_path(user_id)
            if profile_path.exists():
                raise ConflictError(f"User already exists: {user_id}")

            now = self._now()
            record = UserRecord(
                id=user_id,
                display_name=display_name or user_id,
                status="active",
                created_at=now,
                updated_at=now,
                metadata=metadata or {},
            )
            payload = record.to_dict()
            self._write_json(profile_path, payload)
            self._upsert_registry_item(self._users_registry_path(), payload)
            return payload

    def get_user(self, user_id: str) -> dict[str, Any]:
        user_id = self._safe_segment(user_id, "user_id")
        payload = self._read_json(self._user_profile_path(user_id), None)
        if not isinstance(payload, dict):
            raise NotFoundError(f"User not found: {user_id}")
        return UserRecord.from_dict(payload).to_dict()

    def list_users(self, *, include_disabled: bool = False) -> list[dict[str, Any]]:
        with self._lock:
            users = [UserRecord.from_dict(item).to_dict() for item in self._load_registry(self._users_registry_path())]
            if include_disabled:
                return users
            return [user for user in users if user.get("status") != "disabled"]

    def update_user(
        self,
        user_id: str,
        *,
        display_name: str | None = None,
        metadata: dict[str, Any] | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            current = self.get_user(user_id)
            if status is not None and status not in {"active", "disabled"}:
                raise ValidationError("status must be active or disabled")
            if display_name is not None:
                current["display_name"] = display_name
            if metadata is not None:
                current["metadata"] = metadata
            if status is not None:
                current["status"] = status
            current["updated_at"] = self._now()
            self._write_json(self._user_profile_path(current["id"]), current)
            self._upsert_registry_item(self._users_registry_path(), current)
            return current

    def delete_user(self, user_id: str) -> dict[str, Any]:
        return self.update_user(user_id, status="disabled")

    def create_group(
        self,
        *,
        group_id: str,
        name: str,
        created_by: str,
        description: str = "",
        default_agent_id: str = "default",
        memory_policy: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        group_id = self._safe_segment(group_id, "group_id")
        created_by = self._safe_segment(created_by, "created_by")
        default_agent_id = self._safe_segment(default_agent_id, "default_agent_id")
        with self._lock:
            creator = self.get_user(created_by)
            if creator.get("status") == "disabled":
                raise ValidationError(f"User is disabled: {created_by}")
            meta_path = self._group_meta_path(group_id)
            if meta_path.exists():
                raise ConflictError(f"Group already exists: {group_id}")

            now = self._now()
            knowledge_dir = self._knowledge_group_dir(group_id)
            default_policy = self._load_default_memory_policy()
            effective_policy = _deep_merge(default_policy, memory_policy or {})
            group = GroupRecord(
                id=group_id,
                name=name,
                description=description,
                status="active",
                default_agent_id=default_agent_id,
                created_by=created_by,
                created_at=now,
                updated_at=now,
                knowledge={
                    "root": f"knowledge/groups/{group_id}",
                    "documents": f"knowledge/groups/{group_id}/documents",
                    "uploads": f"knowledge/groups/{group_id}/uploads",
                },
                memory_policy=effective_policy,
                metadata=metadata or {},
            )
            membership = MembershipRecord(
                group_id=group_id,
                user_id=created_by,
                role="owner",
                status="active",
                created_at=now,
                updated_at=now,
            )
            payload = group.to_dict()
            self._ensure_group_layout(group)
            self._write_json(meta_path, payload)
            self._write_json(self._group_members_path(group_id), {"items": [membership.to_dict()]})
            self._upsert_registry_item(self._groups_registry_path(), payload)
            knowledge_dir.mkdir(parents=True, exist_ok=True)
            return payload

    def get_group(self, group_id: str) -> dict[str, Any]:
        group_id = self._safe_segment(group_id, "group_id")
        payload = self._read_json(self._group_meta_path(group_id), None)
        if not isinstance(payload, dict):
            raise NotFoundError(f"Group not found: {group_id}")
        return GroupRecord.from_dict(payload).to_dict()

    def list_groups(self, *, include_archived: bool = False) -> list[dict[str, Any]]:
        with self._lock:
            groups = [GroupRecord.from_dict(item).to_dict() for item in self._load_registry(self._groups_registry_path())]
            if include_archived:
                return groups
            return [group for group in groups if group.get("status") != "archived"]

    def update_group(
        self,
        group_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        default_agent_id: str | None = None,
        memory_policy: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            current = self.get_group(group_id)
            if status is not None and status not in {"active", "archived"}:
                raise ValidationError("status must be active or archived")
            if name is not None:
                current["name"] = name
            if description is not None:
                current["description"] = description
            if default_agent_id is not None:
                current["default_agent_id"] = self._safe_segment(default_agent_id, "default_agent_id")
            if memory_policy is not None:
                current["memory_policy"] = _deep_merge(current.get("memory_policy", {}), memory_policy)
            if metadata is not None:
                current["metadata"] = metadata
            if status is not None:
                current["status"] = status
            current["updated_at"] = self._now()
            self._write_json(self._group_meta_path(current["id"]), current)
            self._upsert_registry_item(self._groups_registry_path(), current)
            return current

    def archive_group(self, group_id: str) -> dict[str, Any]:
        return self.update_group(group_id, status="archived")

    def restore_group(self, group_id: str) -> dict[str, Any]:
        return self.update_group(group_id, status="active")

    def delete_group(self, group_id: str) -> dict[str, Any]:
        return self.archive_group(group_id)

    def list_members(self, group_id: str, *, include_removed: bool = False) -> list[dict[str, Any]]:
        self.get_group(group_id)
        payload = self._read_json(self._group_members_path(group_id), {"items": []})
        items = payload.get("items", []) if isinstance(payload, dict) else []
        members = [MembershipRecord.from_dict(item).to_dict() for item in items if isinstance(item, dict)]
        if include_removed:
            return members
        return [member for member in members if member.get("status") != "removed"]

    def add_member(self, group_id: str, user_id: str, role: MemberRole = "member") -> dict[str, Any]:
        if role not in {"owner", "admin", "member", "viewer"}:
            raise ValidationError("role must be owner, admin, member or viewer")
        group_id = self._safe_segment(group_id, "group_id")
        user_id = self._safe_segment(user_id, "user_id")
        with self._lock:
            self.get_group(group_id)
            user = self.get_user(user_id)
            if user.get("status") == "disabled":
                raise ValidationError(f"User is disabled: {user_id}")

            now = self._now()
            members = self.list_members(group_id, include_removed=True)
            record = MembershipRecord(
                group_id=group_id,
                user_id=user_id,
                role=role,
                status="active",
                created_at=now,
                updated_at=now,
            ).to_dict()
            updated = False
            for index, existing in enumerate(members):
                if existing.get("user_id") == user_id:
                    record["created_at"] = existing.get("created_at", now)
                    members[index] = record
                    updated = True
                    break
            if not updated:
                members.append(record)
            self._write_json(self._group_members_path(group_id), {"items": members})
            return record

    def remove_member(self, group_id: str, user_id: str) -> dict[str, Any]:
        group_id = self._safe_segment(group_id, "group_id")
        user_id = self._safe_segment(user_id, "user_id")
        with self._lock:
            members = self.list_members(group_id, include_removed=True)
            for member in members:
                if member.get("user_id") == user_id:
                    member["status"] = "removed"
                    member["updated_at"] = self._now()
                    self._write_json(self._group_members_path(group_id), {"items": members})
                    return member
            raise NotFoundError(f"Group member not found: {user_id}")
