# Prompt 复用库 API
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.deps import get_current_user, require_admin
from app.services import prompt_library_store as store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/prompt-library", tags=["prompt-library"])


class CreatePromptRequest(BaseModel):
    task_type: str
    title: str
    description: Optional[str] = None
    full_prompt: str
    model_used: Optional[str] = None
    aspect_ratio: Optional[str] = None
    sample_image: Optional[str] = None
    sample_kind: Optional[str] = "image"
    tags: Optional[list[str]] = None
    is_shared: Optional[bool] = False


class UpdatePromptRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    full_prompt: Optional[str] = None
    model_used: Optional[str] = None
    aspect_ratio: Optional[str] = None
    tags: Optional[list[str]] = None
    is_shared: Optional[bool] = None


# 允许的 task_type 白名单
_ALLOWED_TASK_TYPES = {
    "quick", "outfit", "model_gen", "seed_grass", "product_main", "aplus",
    "video", "video_shots",
}


@router.get("")
async def list_prompts(
    task_type: Optional[str] = None,
    current_user=Depends(get_current_user),
):
    """列表：自己的 + 他人共享的"""
    rows = await store.list_prompts(
        user_id=current_user["id"],
        task_type=task_type,
        include_shared=True,
    )
    return {"success": True, "items": rows, "count": len(rows)}


@router.post("")
async def create_prompt(req: CreatePromptRequest, current_user=Depends(get_current_user)):
    """创建（收藏）"""
    if req.task_type not in _ALLOWED_TASK_TYPES:
        raise HTTPException(400, f"task_type 仅允许: {sorted(_ALLOWED_TASK_TYPES)}")
    if not req.title.strip():
        raise HTTPException(400, "标题不能为空")
    if not req.full_prompt.strip():
        raise HTTPException(400, "完整 prompt 不能为空")

    data = await store.create_prompt({
        "user_id": current_user["id"],
        "task_type": req.task_type,
        "title": req.title.strip()[:100],
        "description": (req.description or "").strip()[:500] or None,
        "full_prompt": req.full_prompt.strip(),
        "model_used": req.model_used,
        "aspect_ratio": req.aspect_ratio,
        "sample_image": req.sample_image,
        "sample_kind": req.sample_kind or "image",
        "tags": req.tags or [],
        "is_shared": req.is_shared,
    })
    logger.info(f"用户 {current_user['username']} 收藏 Prompt: {data['id']}")
    return {"success": True, "item": data}


@router.put("/{prompt_id}")
async def update_prompt(
    prompt_id: str,
    req: UpdatePromptRequest,
    current_user=Depends(get_current_user),
):
    """更新（仅作者）"""
    updates = req.model_dump(exclude_none=True)
    item = await store.update_prompt(prompt_id, current_user["id"], updates)
    if item is None:
        raise HTTPException(404, "记录不存在或无权修改")
    return {"success": True, "item": item}


@router.delete("/{prompt_id}")
async def delete_prompt(
    prompt_id: str,
    current_user=Depends(get_current_user),
):
    """删除（作者或 admin）"""
    if current_user["role"] == "admin":
        ok = await store.delete_prompt_admin(prompt_id)
    else:
        ok = await store.delete_prompt(prompt_id, current_user["id"])
    if not ok:
        raise HTTPException(404, "记录不存在或无权删除")
    logger.info(f"删除 Prompt: {prompt_id} by {current_user['username']}")
    return {"success": True}


@router.post("/{prompt_id}/use")
async def mark_used(prompt_id: str, _user=Depends(get_current_user)):
    """标记被复用（use_count += 1）"""
    await store.increment_use_count(prompt_id)
    return {"success": True}
