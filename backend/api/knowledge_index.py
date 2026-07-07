from __future__ import annotations

import asyncio
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Query

from config import get_settings
from group_management import GroupManagementService
from knowledge_retrieval import knowledge_indexer

router = APIRouter()


@lru_cache(maxsize=1)
def _group_service() -> GroupManagementService:
    return GroupManagementService(get_settings().backend_dir)


def _known_group(group_id: str) -> bool:
    try:
        _group_service().get_group(group_id)
        return True
    except Exception:
        return group_id in knowledge_indexer.list_groups()


def _serialize_index_status(*, group_id: str | None) -> dict:
    status = knowledge_indexer.status(group_id=group_id).to_dict()
    if group_id is None:
        return {
            "scope": "all_groups",
            "group_ids": knowledge_indexer.list_groups(),
            **status,
        }
    return {
        "scope": "group",
        "group_id": group_id,
        "source_file_count": knowledge_indexer.count_group_sources(group_id),
        **status,
    }


@router.get("/knowledge/index/status")
async def get_index_status(group_id: str | None = Query(default=None)) -> dict:
    if group_id is not None and not _known_group(group_id):
        raise HTTPException(status_code=404, detail=f"Group not found: {group_id}")
    return _serialize_index_status(group_id=group_id)


@router.post("/knowledge/index/rebuild")
async def rebuild_index(group_id: str | None = Query(default=None)) -> dict[str, object]:
    if group_id is not None and not _known_group(group_id):
        raise HTTPException(status_code=404, detail=f"Group not found: {group_id}")
    if knowledge_indexer.is_building():
        return {"accepted": True, "group_id": group_id, "queued": False}
    asyncio.create_task(asyncio.to_thread(knowledge_indexer.rebuild_index, group_id))
    return {"accepted": True, "group_id": group_id, "queued": True}


@router.get("/groups/{group_id}/knowledge/index/status")
async def get_group_index_status(group_id: str) -> dict:
    if not _known_group(group_id):
        raise HTTPException(status_code=404, detail=f"Group not found: {group_id}")
    return _serialize_index_status(group_id=group_id)


@router.post("/groups/{group_id}/knowledge/index/rebuild")
async def rebuild_group_index(group_id: str) -> dict[str, object]:
    if not _known_group(group_id):
        raise HTTPException(status_code=404, detail=f"Group not found: {group_id}")
    if knowledge_indexer.is_building():
        return {"accepted": True, "group_id": group_id, "queued": False}
    asyncio.create_task(asyncio.to_thread(knowledge_indexer.rebuild_index, group_id))
    return {"accepted": True, "group_id": group_id, "queued": True}
