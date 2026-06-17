# 视频生成历史接口
import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps import get_current_user
from app.services import video_history_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/video/history", tags=["video-history"])


@router.get("")
async def list_video_history(
    current_user=Depends(get_current_user),
    include_deleted: bool = Query(False, description="admin 专属：包含用户已软删的记录"),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """获取视频历史列表（admin 可看所有人，user 只看自己）"""
    if current_user["role"] == "admin":
        items = await video_history_store.list_all_video_history(
            include_deleted=include_deleted,
            limit=limit,
            offset=offset,
        )
    else:
        items = await video_history_store.list_video_history(
            user_id=current_user["id"],
            limit=limit,
            offset=offset,
        )
    return {"success": True, "items": items, "count": len(items)}


@router.delete("/{task_id}")
async def delete_one(task_id: str, current_user=Depends(get_current_user)):
    """删除单条视频历史

    - admin：硬删（真删，不可恢复），可删任何人的
    - user：软删（自己看不到了，admin 仍可见），只能删自己的
    """
    if current_user["role"] == "admin":
        ok = await video_history_store.delete_video_history_any(task_id)
        action = "硬删"
    else:
        ok = await video_history_store.delete_video_history(current_user["id"], task_id)
        action = "软删"
    if not ok:
        raise HTTPException(404, "视频记录不存在或无权删除")
    logger.info(f"用户 {current_user['username']} {action} 视频历史 {task_id}")
    return {"success": True, "message": "已删除", "action": action}


@router.post("/clear")
async def clear_mine(current_user=Depends(get_current_user)):
    """清空当前用户的全部视频历史（软删：admin 仍可见）"""
    count = await video_history_store.clear_user_video_history(current_user["id"])
    logger.info(f"用户 {current_user['username']} 清空视频历史（软删），共 {count} 条")
    return {
        "success": True,
        "message": f"已清空 {count} 条视频历史（管理员仍可查看）",
        "deleted": count,
    }
