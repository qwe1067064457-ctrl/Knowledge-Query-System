from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from config import get_settings
from group_management import ConflictError, GroupManagementService, NotFoundError, ValidationError
from group_management.models import MemberRole

router = APIRouter()


class CreateGroupRequest(BaseModel):
    id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=120)
    created_by: str = Field(..., min_length=1, max_length=100)
    description: str = ""
    default_agent_id: str = "default"
    memory_policy: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpdateGroupRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    default_agent_id: str | None = None
    memory_policy: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    status: str | None = None


class AddMemberRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    role: MemberRole = "member"


@lru_cache(maxsize=1)
def _service() -> GroupManagementService:
    return GroupManagementService(get_settings().backend_dir)


def _raise_http(error: Exception) -> None:
    if isinstance(error, ValidationError):
        raise HTTPException(status_code=400, detail=str(error))
    if isinstance(error, NotFoundError):
        raise HTTPException(status_code=404, detail=str(error))
    if isinstance(error, ConflictError):
        raise HTTPException(status_code=409, detail=str(error))
    raise HTTPException(status_code=500, detail=str(error))


@router.get("/groups")
async def list_groups(include_archived: bool = Query(False)) -> list[dict[str, Any]]:
    return _service().list_groups(include_archived=include_archived)


@router.post("/groups")
async def create_group(payload: CreateGroupRequest) -> dict[str, Any]:
    try:
        return _service().create_group(
            group_id=payload.id,
            name=payload.name,
            created_by=payload.created_by,
            description=payload.description,
            default_agent_id=payload.default_agent_id,
            memory_policy=payload.memory_policy,
            metadata=payload.metadata,
        )
    except Exception as exc:
        _raise_http(exc)


@router.get("/groups/{group_id}")
async def get_group(group_id: str) -> dict[str, Any]:
    try:
        return _service().get_group(group_id)
    except Exception as exc:
        _raise_http(exc)


@router.put("/groups/{group_id}")
async def update_group(group_id: str, payload: UpdateGroupRequest) -> dict[str, Any]:
    try:
        return _service().update_group(
            group_id,
            name=payload.name,
            description=payload.description,
            default_agent_id=payload.default_agent_id,
            memory_policy=payload.memory_policy,
            metadata=payload.metadata,
            status=payload.status,
        )
    except Exception as exc:
        _raise_http(exc)


@router.delete("/groups/{group_id}")
async def delete_group(group_id: str) -> dict[str, Any]:
    try:
        return _service().delete_group(group_id)
    except Exception as exc:
        _raise_http(exc)


@router.post("/groups/{group_id}/archive")
async def archive_group(group_id: str) -> dict[str, Any]:
    try:
        return _service().archive_group(group_id)
    except Exception as exc:
        _raise_http(exc)


@router.post("/groups/{group_id}/restore")
async def restore_group(group_id: str) -> dict[str, Any]:
    try:
        return _service().restore_group(group_id)
    except Exception as exc:
        _raise_http(exc)


@router.get("/groups/{group_id}/members")
async def list_group_members(
    group_id: str,
    include_removed: bool = Query(False),
) -> list[dict[str, Any]]:
    try:
        return _service().list_members(group_id, include_removed=include_removed)
    except Exception as exc:
        _raise_http(exc)


@router.post("/groups/{group_id}/members")
async def add_group_member(group_id: str, payload: AddMemberRequest) -> dict[str, Any]:
    try:
        return _service().add_member(group_id, payload.user_id, payload.role)
    except Exception as exc:
        _raise_http(exc)


@router.delete("/groups/{group_id}/members/{user_id}")
async def remove_group_member(group_id: str, user_id: str) -> dict[str, Any]:
    try:
        return _service().remove_member(group_id, user_id)
    except Exception as exc:
        _raise_http(exc)
