from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from file_management import file_management_agent

router = APIRouter()


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
    result = file_management_agent.propose_ai_edit(
        file_path=proposal.file_path,
        new_content=proposal.new_content,
        source_ai=proposal.source_ai,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    
    return result


@router.get("/review/tasks", response_model=list[dict[str, Any]])
async def list_pending_reviews() -> list[dict[str, Any]]:
    return file_management_agent.get_pending_reviews()


@router.get("/review/tasks/{task_id}", response_model=dict[str, Any])
async def get_review_task(task_id: str) -> dict[str, Any]:
    task = file_management_agent.get_review_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="审查任务不存在")
    return task


@router.post("/review/tasks/{task_id}/approve", response_model=dict[str, Any])
async def approve_review(task_id: str) -> dict[str, Any]:
    result = file_management_agent.approve_review_task(task_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/review/tasks/{task_id}/reject", response_model=dict[str, Any])
async def reject_review(task_id: str) -> dict[str, Any]:
    result = file_management_agent.reject_review_task(task_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.put("/review/tasks/{task_id}/edit", response_model=dict[str, Any])
async def edit_and_approve_review(task_id: str, request: EditAndApproveRequest) -> dict[str, Any]:
    result = file_management_agent.edit_and_approve_review_task(
        task_id=task_id,
        edited_content=request.edited_content,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.get("/review/pending-count", response_model=dict[str, int])
async def get_pending_review_count() -> dict[str, int]:
    return {"count": len(file_management_agent.get_pending_reviews())}
