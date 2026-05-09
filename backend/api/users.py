from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from config import get_settings
from group_management import ConflictError, GroupManagementService, NotFoundError, ValidationError

router = APIRouter()


class CreateUserRequest(BaseModel):
    id: str = Field(..., min_length=1, max_length=100)
    display_name: str | None = Field(default=None, max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpdateUserRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=100)
    metadata: dict[str, Any] | None = None
    status: str | None = None


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


@router.get("/users")
async def list_users(include_disabled: bool = Query(False)) -> list[dict[str, Any]]:
    return _service().list_users(include_disabled=include_disabled)


@router.post("/users")
async def create_user(payload: CreateUserRequest) -> dict[str, Any]:
    try:
        return _service().create_user(
            user_id=payload.id,
            display_name=payload.display_name,
            metadata=payload.metadata,
        )
    except Exception as exc:
        _raise_http(exc)


@router.get("/users/{user_id}")
async def get_user(user_id: str) -> dict[str, Any]:
    try:
        return _service().get_user(user_id)
    except Exception as exc:
        _raise_http(exc)


@router.put("/users/{user_id}")
async def update_user(user_id: str, payload: UpdateUserRequest) -> dict[str, Any]:
    try:
        return _service().update_user(
            user_id,
            display_name=payload.display_name,
            metadata=payload.metadata,
            status=payload.status,
        )
    except Exception as exc:
        _raise_http(exc)


@router.delete("/users/{user_id}")
async def delete_user(user_id: str) -> dict[str, Any]:
    try:
        return _service().delete_user(user_id)
    except Exception as exc:
        _raise_http(exc)
