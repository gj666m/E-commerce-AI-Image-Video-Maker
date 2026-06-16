# 图片生成历史接口
import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps import get_current_user, require_admin
from app.services import history_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("")
async def list_history(
    current_user=Depends(get_current_user),
    task_type: str | None = Query(None, description="按任务类型筛选"),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """获取生成历史列表（admin 可看所有人，user 只看自己）"""
    if current_user["role"] == "admin":
        items = await history_store.list_all_history(task_type=task_type, limit=limit, offset=offset)
    else:
        items = await history_store.list_history(
            user_id=current_user["id"],
            task_type=task_type,
            limit=limit,
            offset=offset,
        )
    return {"success": True, "items": items, "count": len(items)}


@router.delete("/{history_id}")
async def delete_one(history_id: str, current_user=Depends(get_current_user)):
    """删除单条历史（admin 可删任何人的，user 只能删自己的）"""
    ok = await history_store.delete_history(current_user["id"], history_id)
    if not ok:
        # 管理员回退：直接按 id 删（不限 user_id）
        if current_user["role"] == "admin":
            ok = await history_store.delete_history_any(history_id)
        if not ok:
            raise HTTPException(404, "历史记录不存在或无权删除")
    return {"success": True, "message": "已删除"}


@router.post("/clear")
async def clear_mine(current_user=Depends(get_current_user)):
    """清空当前用户的全部历史"""
    count = await history_store.clear_user_history(current_user["id"])
    logger.info(f"用户 {current_user['username']} 清空历史，共 {count} 条")
    return {"success": True, "message": f"已清空 {count} 条历史", "deleted": count}
