from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


UserStatus = Literal["active", "disabled"]
GroupStatus = Literal["active", "archived"]
MemberRole = Literal["owner", "admin", "member", "viewer"]
MemberStatus = Literal["active", "removed"]


@dataclass
class UserRecord:
    id: str
    display_name: str
    status: UserStatus
    created_at: str
    updated_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "UserRecord":
        return cls(
            id=str(payload["id"]),
            display_name=str(payload.get("display_name") or payload["id"]),
            status=payload.get("status", "active"),
            created_at=str(payload.get("created_at", "")),
            updated_at=str(payload.get("updated_at", "")),
            metadata=dict(payload.get("metadata") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }


@dataclass
class GroupRecord:
    id: str
    name: str
    description: str
    status: GroupStatus
    default_agent_id: str
    created_by: str
    created_at: str
    updated_at: str
    knowledge: dict[str, Any] = field(default_factory=dict)
    memory_policy: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GroupRecord":
        return cls(
            id=str(payload["id"]),
            name=str(payload.get("name") or payload["id"]),
            description=str(payload.get("description") or ""),
            status=payload.get("status", "active"),
            default_agent_id=str(payload.get("default_agent_id") or "default"),
            created_by=str(payload.get("created_by") or ""),
            created_at=str(payload.get("created_at", "")),
            updated_at=str(payload.get("updated_at", "")),
            knowledge=dict(payload.get("knowledge") or {}),
            memory_policy=dict(payload.get("memory_policy") or {}),
            metadata=dict(payload.get("metadata") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "default_agent_id": self.default_agent_id,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "knowledge": self.knowledge,
            "memory_policy": self.memory_policy,
            "metadata": self.metadata,
        }


@dataclass
class MembershipRecord:
    group_id: str
    user_id: str
    role: MemberRole
    status: MemberStatus
    created_at: str
    updated_at: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MembershipRecord":
        return cls(
            group_id=str(payload["group_id"]),
            user_id=str(payload["user_id"]),
            role=payload.get("role", "member"),
            status=payload.get("status", "active"),
            created_at=str(payload.get("created_at", "")),
            updated_at=str(payload.get("updated_at", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "user_id": self.user_id,
            "role": self.role,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
