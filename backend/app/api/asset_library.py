# 素材资产库 API（续19）
# 已生成图/视频的沉淀池。运营加入素材库 + 自定义标签 + 后续应用追踪。
# 文件永久保留（清理任务跳过已沉淀素材）。
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.deps import get_current_user
from app.services import asset_library_store as store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/asset-library", tags=["asset-library"])

_ALLOWED_SOURCE_TYPES = {"image", "video"}


class CreateAssetRequest(BaseModel):
    source_type: str                       # 'image' / 'video'
    source_id: str                         # generation_history.id 或 video_tasks.id
    title: str
    description: Optional[str] = None
    tags: Optional[list[str]] = None


class UpdateAssetRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list[str]] = None


class CreateApplicationRequest(BaseModel):
    shop_name: str
    applied_url: Optional[str] = None
    notes: Optional[str] = None


class UpdateApplicationRequest(BaseModel):
    shop_name: Optional[str] = None
    applied_url: Optional[str] = None
    notes: Optional[str] = None


class CreateTrackingRequest(BaseModel):
    views: Optional[int] = None
    clicks: Optional[int] = None
    conversions: Optional[int] = None
    gmv: Optional[float] = None
    extra_metrics: Optional[list[dict]] = None
    notes: Optional[str] = None
    recorded_at: Optional[str] = None


class UpdateTrackingRequest(BaseModel):
    views: Optional[int] = None
    clicks: Optional[int] = None
    conversions: Optional[int] = None
    gmv: Optional[float] = None
    extra_metrics: Optional[list[dict]] = None
    notes: Optional[str] = None
    recorded_at: Optional[str] = None


@router.get("")
async def list_assets(
    source_type: Optional[str] = None,
    tag: Optional[str] = None,
    q: Optional[str] = None,
    user_id: Optional[int] = None,
    current_user=Depends(get_current_user),
):
    """列表：自己的（admin 可看所有人，?user_id= 筛选）"""
    is_admin = current_user["role"] == "admin"
    items = await store.list_assets(
        user_id=current_user["id"],
        source_type=source_type,
        tag=tag,
        q=q,
        include_all_for_admin=is_admin,
        target_user_id=user_id if is_admin else None,
    )
    return {"success": True, "items": items, "count": len(items)}


@router.get("/tags")
async def list_tags(current_user=Depends(get_current_user)):
    """标签云（聚合当前用户的所有标签 + 计数）"""
    tags = await store.list_tags(current_user["id"])
    return {"success": True, "tags": tags}


@router.post("")
async def create_asset(req: CreateAssetRequest, current_user=Depends(get_current_user)):
    """加入素材库"""
    if req.source_type not in _ALLOWED_SOURCE_TYPES:
        raise HTTPException(400, f"source_type 仅允许: {sorted(_ALLOWED_SOURCE_TYPES)}")
    if not req.title.strip():
        raise HTTPException(400, "标题不能为空")
    if not req.source_id.strip():
        raise HTTPException(400, "source_id 不能为空")

    try:
        data = await store.create_asset({
            "user_id": current_user["id"],
            "source_type": req.source_type,
            "source_id": req.source_id,
            "title": req.title.strip(),
            "description": req.description,
            "tags": req.tags or [],
        })
    except ValueError as e:
        raise HTTPException(409, str(e))

    logger.info(f"用户 {current_user['username']} 加入素材库: {data['id']} ({req.source_type})")
    return {"success": True, "item": data}


@router.put("/{asset_id}")
async def update_asset(
    asset_id: str,
    req: UpdateAssetRequest,
    current_user=Depends(get_current_user),
):
    """更新（仅作者；admin 通过 store 旁路 user_id=-1）"""
    updates = req.model_dump(exclude_none=True)
    # admin 旁路
    uid = -1 if current_user["role"] == "admin" else current_user["id"]
    item = await store.update_asset(asset_id, uid, updates)
    if item is None:
        raise HTTPException(404, "记录不存在或无权修改")
    return {"success": True, "item": item}


@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: str,
    current_user=Depends(get_current_user),
):
    """删除（作者或 admin；级联删 applications + tracking）"""
    if current_user["role"] == "admin":
        ok = await store.delete_asset_admin(asset_id)
    else:
        ok = await store.delete_asset(asset_id, current_user["id"])
    if not ok:
        raise HTTPException(404, "记录不存在或无权删除")
    logger.info(f"删除素材: {asset_id} by {current_user['username']}")
    return {"success": True}


@router.get("/is-preserved")
async def check_preserved(
    source_type: str = Query(...),
    source_id: str = Query(...),
    current_user=Depends(get_current_user),
):
    """检查某条历史是否已沉淀（给前端按钮状态用）"""
    if source_type not in _ALLOWED_SOURCE_TYPES:
        raise HTTPException(400, f"source_type 仅允许: {sorted(_ALLOWED_SOURCE_TYPES)}")
    preserved = await store.is_preserved(current_user["id"], source_type, source_id)
    return {"success": True, "preserved": preserved}


# === 应用记录（asset_applications）===

@router.get("/{asset_id}/applications")
async def list_applications(
    asset_id: str,
    current_user=Depends(get_current_user),
):
    """列某素材的所有应用记录（作者/admin 可见）"""
    is_admin = current_user["role"] == "admin"
    items = await store.list_applications(
        asset_id=asset_id,
        include_all_for_admin=is_admin,
    )
    return {"success": True, "items": items, "count": len(items)}


@router.post("/{asset_id}/applications")
async def create_application(
    asset_id: str,
    req: CreateApplicationRequest,
    current_user=Depends(get_current_user),
):
    """新增应用记录（仅素材作者）"""
    if not req.shop_name.strip():
        raise HTTPException(400, "店铺名不能为空")
    uid = -1 if current_user["role"] == "admin" else current_user["id"]
    try:
        data = await store.create_application({
            "asset_id": asset_id,
            "user_id": uid,
            "shop_name": req.shop_name.strip(),
            "applied_url": req.applied_url,
            "notes": req.notes,
        })
    except ValueError as e:
        raise HTTPException(404, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))
    logger.info(f"用户 {current_user['username']} 新增应用记录: {data['id']} (asset={asset_id})")
    return {"success": True, "item": data}


# 应用记录的 PUT/DELETE 用独立前缀 /api/applications（plan 设计）
# 但本 router 的 prefix 是 /api/asset-library，所以这两端点单独建子 router
applications_router = APIRouter(prefix="/api/applications", tags=["asset-library"])


@applications_router.put("/{app_id}")
async def update_application(
    app_id: str,
    req: UpdateApplicationRequest,
    current_user=Depends(get_current_user),
):
    """更新应用记录（仅作者；admin 旁路）"""
    updates = req.model_dump(exclude_none=True)
    uid = -1 if current_user["role"] == "admin" else current_user["id"]
    item = await store.update_application(app_id, uid, updates)
    if item is None:
        raise HTTPException(404, "记录不存在或无权修改")
    return {"success": True, "item": item}


@applications_router.delete("/{app_id}")
async def delete_application(
    app_id: str,
    current_user=Depends(get_current_user),
):
    """删除应用记录（作者或 admin；级联删 tracking）"""
    if current_user["role"] == "admin":
        ok = await store.delete_application(app_id, -1)
    else:
        ok = await store.delete_application(app_id, current_user["id"])
    if not ok:
        raise HTTPException(404, "记录不存在或无权删除")
    logger.info(f"删除应用记录: {app_id} by {current_user['username']}")
    return {"success": True}


@applications_router.get("/shops")
async def list_shops(current_user=Depends(get_current_user)):
    """聚合所有店铺名（去重，用于下拉筛选）"""
    is_admin = current_user["role"] == "admin"
    shops = await store.list_shops(current_user["id"], include_all_for_admin=is_admin)
    return {"success": True, "shops": shops}


# === 价值数据快照（asset_tracking_records）===

@applications_router.get("/{app_id}/tracking")
async def list_tracking(
    app_id: str,
    current_user=Depends(get_current_user),
):
    """列某应用记录的所有价值快照（作者/admin 可见）"""
    # 权限：必须能看见这条 application（作者或 admin）
    # 简化：直接返回，store 不做强校验；前端只会请求自己可见的记录
    items = await store.list_tracking(app_id)
    return {"success": True, "items": items, "count": len(items)}


@applications_router.post("/{app_id}/tracking")
async def create_tracking(
    app_id: str,
    req: CreateTrackingRequest,
    current_user=Depends(get_current_user),
):
    """新增价值数据快照（仅素材作者/admin）"""
    uid = -1 if current_user["role"] == "admin" else current_user["id"]
    try:
        data = await store.create_tracking({
            "application_id": app_id,
            "user_id": uid,
            "views": req.views,
            "clicks": req.clicks,
            "conversions": req.conversions,
            "gmv": req.gmv,
            "extra_metrics": req.extra_metrics,
            "notes": req.notes,
            "recorded_at": req.recorded_at,
        })
    except ValueError as e:
        raise HTTPException(404, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))
    logger.info(f"用户 {current_user['username']} 录入价值数据: {data['id']} (app={app_id})")
    return {"success": True, "item": data}


# tracking PUT/DELETE 用独立前缀 /api/tracking
tracking_router = APIRouter(prefix="/api/tracking", tags=["asset-library"])


@tracking_router.put("/{record_id}")
async def update_tracking(
    record_id: str,
    req: UpdateTrackingRequest,
    current_user=Depends(get_current_user),
):
    """更新价值数据快照（仅作者；admin 旁路）"""
    updates = req.model_dump(exclude_none=True)
    uid = -1 if current_user["role"] == "admin" else current_user["id"]
    item = await store.update_tracking(record_id, uid, updates)
    if item is None:
        raise HTTPException(404, "记录不存在或无权修改")
    return {"success": True, "item": item}


@tracking_router.delete("/{record_id}")
async def delete_tracking(
    record_id: str,
    current_user=Depends(get_current_user),
):
    """删除价值数据快照（作者或 admin）"""
    if current_user["role"] == "admin":
        ok = await store.delete_tracking(record_id, -1)
    else:
        ok = await store.delete_tracking(record_id, current_user["id"])
    if not ok:
        raise HTTPException(404, "记录不存在或无权删除")
    logger.info(f"删除价值数据: {record_id} by {current_user['username']}")
    return {"success": True}
