
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from file_management.ai_review_manager import propose_ai_modification, handle_user_decision
from file_management.file_operations import read_file, write_file

router = APIRouter()

# In-memory database for pending reviews (for demonstration purposes)
_pending_reviews: dict[str, dict[str, Any]] = {}


class AIEditProposal(BaseModel):
    file_path: str = Field(..., description="要修改的文件路径")
    new_content: str = Field(..., description="AI建议的新内容")
    source_ai: Optional[str] = Field(None, description="AI模型标识")


class ReviewTaskResponse(BaseModel):
    id: str
    file_path: str
    old_content: str
    new_content: str
    diff_result: dict[str, Any]
    status: str
    created_at: float
    resolved_at: Optional[float] = None
    source_ai: Optional[str] = None


class EditAndApproveRequest(BaseModel):
    edited_content: str = Field(..., description="用户编辑后的内容")


@router.post("/review/propose", response_model=dict[str, Any])
async def propose_ai_edit(proposal: AIEditProposal) -> dict[str, Any]:
    try:
        original_content = read_file(proposal.file_path)
    except FileNotFoundError:
        original_content = ""

    review_task = propose_ai_modification(
        original_content=original_content,
        modified_content=proposal.new_content,
        file_path=proposal.file_path,
        agent_id=proposal.source_ai or "unknown_ai",
    )
    _pending_reviews[review_task["proposal_id"]] = review_task
    return {"success": True, "task": review_task}


@router.get("/review/tasks", response_model=list[dict[str, Any]])
async def list_pending_reviews() -> list[dict[str, Any]]:
    return list(_pending_reviews.values())


@router.get("/review/tasks/{task_id}", response_model=dict[str, Any])
async def get_review_task(task_id: str) -> dict[str, Any]:
    task = _pending_reviews.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="审查任务不存在")
    return task


@router.post("/review/tasks/{task_id}/approve", response_model=dict[str, Any])
async def approve_review(task_id: str) -> dict[str, Any]:
    task = _pending_reviews.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="审查任务不存在")

    handle_user_decision(task_id, "accepted")
    write_file(task["file_path"], task["proposed_content"])
    del _pending_reviews[task_id]
    return {"success": True, "message": "Review approved and file updated."}


@router.post("/review/tasks/{task_id}/reject", response_model=dict[str, Any])
async def reject_review(task_id: str) -> dict[str, Any]:
    if task_id not in _pending_reviews:
        raise HTTPException(status_code=404, detail="审查任务不存在")

    handle_user_decision(task_id, "rejected")
    del _pending_reviews[task_id]
    return {"success": True, "message": "Review rejected."}


@router.put("/review/tasks/{task_id}/edit", response_model=dict[str, Any])
async def edit_and_approve_review(task_id: str, request: EditAndApproveRequest) -> dict[str, Any]:
    task = _pending_reviews.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="审查任务不存在")

    handle_user_decision(task_id, "edited")
    write_file(task["file_path"], request.edited_content)
    del _pending_reviews[task_id]
    return {"success": True, "message": "Review edited and approved."}


@router.get("/review/pending-count", response_model=dict[str, int])
async def get_pending_review_count() -> dict[str, int]:
    return {"count": len(_pending_reviews)}
