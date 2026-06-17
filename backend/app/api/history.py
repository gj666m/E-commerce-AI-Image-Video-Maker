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
    普通用户无删除权限，但历史可见只读
    """
    if current_user["role"] == "admin":
        items = await history_store.list_all_history(
            task_type=task_type,
            include_deleted=include_deleted,
            limit=limit,
            offset=offset,
        )
    else:
        # 普通用户：只看自己未软删的（旧 user_deleted=1 仍隐藏）
        items = await history_store.list_history(
            user_id=current_user["id"],
            task_type=task_type,
            limit=limit,
            offset=offset,
        )
    return {"success": True, "items": items, "count": len(items)}


@router.delete("/{history_id}")
async def delete_one(
    history_id: str,
    admin=Depends(require_admin),
):
    """硬删单条历史（仅 admin）

    用户无删除权限。admin 硬删任意一条（真删，不可恢复）。
    """
    ok = await history_store.delete_history_any(history_id)
    if not ok:
        raise HTTPException(404, "历史记录不存在")
    logger.info(f"管理员 {admin['username']} 硬删历史 {history_id}")
    return {"success": True, "message": "已硬删", "action": "硬删"}


@router.post("/clear")
async def clear_all(
    admin=Depends(require_admin),
    username: str | None = Query(None, description="指定用户名则只清该用户，不传则清所有用户"),
):
    """清空历史（仅 admin，硬删）

    用户无清空权限。admin 可清空所有用户或指定用户的历史（真删不可恢复）。
    """
    count = await history_store.clear_all_history_admin(username=username)
    target = f"用户 {username}" if username else "所有用户"
    logger.info(f"管理员 {admin['username']} 清空 {target} 历史（硬删），共 {count} 条")
    return {
        "success": True,
        "message": f"已清空 {target} 的 {count} 条历史（硬删，不可恢复）",
        "deleted": count,
    }
