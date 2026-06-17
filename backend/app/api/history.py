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
    include_deleted: bool = Query(False, description="admin 专属：包含用户已软删的记录"),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """获取生成历史列表（admin 可看所有人，user 只看自己）

    admin 默认看不到用户已软删的，传 include_deleted=true 可见（审计用）
    """
    if current_user["role"] == "admin":
        items = await history_store.list_all_history(
            task_type=task_type,
            include_deleted=include_deleted,
            limit=limit,
            offset=offset,
        )
    else:
        # 普通用户：强制 include_deleted=False（看不到自己软删的）
        items = await history_store.list_history(
            user_id=current_user["id"],
            task_type=task_type,
            limit=limit,
            offset=offset,
        )
    return {"success": True, "items": items, "count": len(items)}


@router.delete("/{history_id}")
async def delete_one(history_id: str, current_user=Depends(get_current_user)):
    """删除单条历史

    - admin：硬删（真删，不可恢复），可删任何人的
    - user：软删（自己看不到了，admin 仍可见），只能删自己的
    """
    if current_user["role"] == "admin":
        # admin 始终硬删
        ok = await history_store.delete_history_any(history_id)
        action = "硬删"
    else:
        # user 软删自己的
        ok = await history_store.delete_history(current_user["id"], history_id)
        action = "软删"
    if not ok:
        raise HTTPException(404, "历史记录不存在或无权删除")
    logger.info(f"用户 {current_user['username']} {action} 历史 {history_id}")
    return {"success": True, "message": "已删除", "action": action}


@router.post("/clear")
async def clear_mine(current_user=Depends(get_current_user)):
    """清空当前用户的全部历史（软删：admin 仍可见）"""
    count = await history_store.clear_user_history(current_user["id"])
    logger.info(f"用户 {current_user['username']} 清空历史（软删），共 {count} 条")
    return {
        "success": True,
        "message": f"已清空 {count} 条历史（管理员仍可查看）",
        "deleted": count,
    }
