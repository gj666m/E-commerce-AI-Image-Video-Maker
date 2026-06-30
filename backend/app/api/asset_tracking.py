# 素材应用价值跟踪报表 API（续19 Day3）
# 汇总：总播放/点击/转化/GMV + Top 素材 + 店铺维度
# 列表：已应用素材（每行一个 application）+ 最新一期价值 + 全部历史快照
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps import get_current_user
from app.services import asset_library_store as store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/asset-tracking", tags=["asset-tracking"])


@router.get("/summary")
async def get_summary(
    shop: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None, description="YYYY-MM-DD 起始日期"),
    to_date: Optional[str] = Query(None, description="YYYY-MM-DD 结束日期"),
    user_id: Optional[int] = Query(None, description="admin 筛选指定用户"),
    current_user=Depends(get_current_user),
):
    """汇总卡片 + Top 素材 + 店铺维度（作者本人；admin 可看全部或按 user_id 筛选）"""
    is_admin = current_user["role"] == "admin"
    # 非 admin 强制忽略 user_id 参数（只能看自己）
    target = user_id if (is_admin and user_id is not None) else None
    summary = await store.get_tracking_summary(
        user_id=current_user["id"],
        include_all_for_admin=is_admin,
        target_user_id=target,
        shop=shop or None,
        tag=tag or None,
        from_dt=from_date or None,
        to_dt=to_date or None,
    )
    return {"success": True, "summary": summary}


@router.get("/list")
async def get_list(
    shop: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    current_user=Depends(get_current_user),
):
    """已应用素材列表（每行一个 application，带最新一期价值 + 全部历史快照）"""
    is_admin = current_user["role"] == "admin"
    target = user_id if (is_admin and user_id is not None) else None
    items = await store.list_applications_with_tracking(
        user_id=current_user["id"],
        include_all_for_admin=is_admin,
        target_user_id=target,
        shop=shop or None,
        tag=tag or None,
        from_dt=from_date or None,
        to_dt=to_date or None,
    )
    return {"success": True, "items": items, "count": len(items)}


@router.get("/shops")
async def list_shops_for_filter(current_user=Depends(get_current_user)):
    """店铺联想下拉（用于筛选器，去重 + 计数）"""
    is_admin = current_user["role"] == "admin"
    shops = await store.list_shops(
        current_user["id"], include_all_for_admin=is_admin
    )
    return {"success": True, "shops": shops}
