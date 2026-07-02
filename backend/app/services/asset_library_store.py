# 素材资产库存储服务（续19）
# asset_library 是已生成图/视频的沉淀池。运营把好图好视频沉淀下来，
# 加自定义标签，后续用于店铺应用追踪 + 价值数据回填。
#
# 不存文件：直接 JOIN generation_history / video_tasks 取 file/thumbnail。
# 视频素材额外抽首帧 jpg 落盘（thumbnail_path），避免依赖浏览器解码 mp4。
# 文件保留：history/video 清理任务用 NOT IN 跳过已沉淀素材（永久保留）。
import asyncio
import json
import logging
import time
from pathlib import Path

from app.config import settings
from app.database import get_db
from app.services.video_thumbnail import extract_first_frame
from app.services.video_utils import get_video_abs_path

logger = logging.getLogger(__name__)

# 老素材懒加载回填防重集
_thumb_backfill_in_progress: set[str] = set()


def _now_iso() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


# === 视频首帧缩略图 ===

def _thumb_rel_path(user_id: int, asset_id: str) -> str:
    return f"{user_id}/{asset_id}.jpg"


def _thumb_abs_path(rel_path: str) -> Path:
    return Path(settings.asset_thumb_dir).resolve() / rel_path


async def _generate_video_thumbnail(asset_id: str, user_id: int, video_url: str) -> str | None:
    """抽视频首帧存 jpg。成功返相对路径，失败返 None（不抛异常）。"""
    abs_video = get_video_abs_path(video_url)
    if abs_video is None or not abs_video.exists():
        return None
    rel = _thumb_rel_path(user_id, asset_id)
    out = _thumb_abs_path(rel)
    ok = await extract_first_frame(abs_video, out)
    return rel if ok else None


async def _persist_thumbnail(asset_id: str, rel_path: str) -> None:
    db = await get_db()
    try:
        await db.execute(
            "UPDATE asset_library SET thumbnail_path = ? WHERE id = ?",
            (rel_path, asset_id),
        )
        await db.commit()
    finally:
        await db.close()


async def _backfill_thumbnail_async(asset_id: str, user_id: int, video_url: str) -> None:
    """后台抽帧 + 写 DB。fire-and-forget，失败静默。"""
    if asset_id in _thumb_backfill_in_progress:
        return
    _thumb_backfill_in_progress.add(asset_id)
    try:
        rel = await _generate_video_thumbnail(asset_id, user_id, video_url)
        if rel:
            await _persist_thumbnail(asset_id, rel)
            logger.info(f"已回填视频缩略图 {asset_id}")
    except Exception as e:
        logger.warning(f"回填视频缩略图失败 {asset_id}: {e}")
    finally:
        _thumb_backfill_in_progress.discard(asset_id)


def _maybe_kick_backfill(asset_id: str, user_id: int, video_url: str | None, has_thumb: bool) -> None:
    """懒加载回填：缺缩略图 + 源文件在 → fire-and-forget 异步抽帧。"""
    if has_thumb or not video_url:
        return
    abs_video = get_video_abs_path(video_url)
    if abs_video is None or not abs_video.exists():
        return
    try:
        asyncio.create_task(_backfill_thumbnail_async(asset_id, user_id, video_url))
    except RuntimeError:
        # 无事件循环（不应发生在 FastAPI 请求中），静默
        pass


def _generate_id(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000)}"


def _row_to_dict(r) -> dict:
    """行转 dict + 解析 tags JSON"""
    keys = r.keys() if hasattr(r, "keys") else []
    d = {
        "id": r["id"],
        "user_id": r["user_id"],
        "source_type": r["source_type"],
        "source_id": r["source_id"],
        "title": r["title"],
        "description": r["description"],
        "tags": json.loads(r["tags"]) if r["tags"] else [],
        "created_at": r["created_at"],
    }
    if "thumbnail_path" in keys:
        d["thumbnail_path"] = r["thumbnail_path"]
    return d


def _apply_thumb_url(d: dict, r, asset_id: str, user_id: int) -> None:
    """根据 source_type + thumbnail_path 拼 thumbnail_url + thumbnail_is_image。

    - image 类：用 generation_history.thumbnail（jpg），is_image=True
    - video 类：有 thumbnail_path（沉淀时抽的首帧 jpg）→ is_image=True；
                否则降级用原视频 URL，is_image=False（前端走 video preload）
    """
    keys = r.keys() if hasattr(r, "keys") else []
    if r["source_type"] == "image":
        d["thumbnail_url"] = f"/gen-files/{user_id}/{r['img_thumb']}" if r["img_thumb"] else None
        d["file_expired"] = bool(r["img_expired"]) if r["img_expired"] is not None else True
        d["thumbnail_is_image"] = bool(d["thumbnail_url"])
    elif r["source_type"] == "video":
        thumb_path = r["thumbnail_path"] if "thumbnail_path" in keys else None
        if thumb_path:
            d["thumbnail_url"] = f"/api/file/asset-thumbs/{thumb_path}"
            d["file_expired"] = False
            d["thumbnail_is_image"] = True
        else:
            # vid_url 已是 /video-files/... 完整 URL，不再拼前缀（否则双 // 导致路径校验失败）
            d["thumbnail_url"] = r["vid_url"] or None
            d["file_expired"] = bool(r["vid_expired"]) if r["vid_expired"] is not None else True
            d["thumbnail_is_image"] = False
            # 懒加载回填：源文件还在就异步抽首帧
            _maybe_kick_backfill(asset_id, user_id, d["thumbnail_url"], has_thumb=False)
    else:
        d["thumbnail_url"] = None
        d["file_expired"] = True
        d["thumbnail_is_image"] = False


# === 沉淀池 CRUD ===

async def create_asset(data: dict) -> dict:
    """加入素材库。
    data 必填：user_id, source_type ('image'/'video'), source_id, title
    可选：description, tags
    """
    asset_id = _generate_id("al")
    db = await get_db()
    try:
        # 重复沉淀校验（同 user + 同 source）
        cursor = await db.execute(
            """SELECT id FROM asset_library
            WHERE user_id = ? AND source_type = ? AND source_id = ?""",
            (data["user_id"], data["source_type"], data["source_id"]),
        )
        if await cursor.fetchone():
            raise ValueError("该素材已加入素材库")

        await db.execute(
            """INSERT INTO asset_library
            (id, user_id, source_type, source_id, title, description, tags, thumbnail_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                asset_id,
                data["user_id"],
                data["source_type"],
                data["source_id"],
                data["title"][:100],
                (data.get("description") or "").strip()[:500] or None,
                json.dumps(data.get("tags") or [], ensure_ascii=False),
                None,
            ),
        )
        await db.commit()

        # 视频类：抽首帧 jpg（同步，沉淀是一次性动作，等待可接受）
        if data["source_type"] == "video":
            # 先查 video_url（沉淀入口已传 source_id，但我们这里再去 video_tasks 取）
            vcur = await db.execute(
                "SELECT video_url FROM video_tasks WHERE id = ?",
                (data["source_id"],),
            )
            vrow = await vcur.fetchone()
            if vrow and vrow["video_url"]:
                try:
                    rel = await _generate_video_thumbnail(asset_id, data["user_id"], vrow["video_url"])
                    if rel:
                        await db.execute(
                            "UPDATE asset_library SET thumbnail_path = ? WHERE id = ?",
                            (rel, asset_id),
                        )
                        await db.commit()
                except Exception as e:
                    logger.warning(f"沉淀视频抽首帧失败 {asset_id}: {e}")

        cursor = await db.execute("SELECT * FROM asset_library WHERE id = ?", (asset_id,))
        return _row_to_dict(await cursor.fetchone())
    finally:
        await db.close()


async def list_assets(
    user_id: int,
    source_type: str | None = None,
    tag: str | None = None,
    q: str | None = None,
    include_all_for_admin: bool = False,
    target_user_id: int | None = None,
) -> list[dict]:
    """列出沉淀素材。
    - source_type：'image' / 'video' 筛选
    - tag：标签精确匹配（tags JSON 数组包含）
    - q：标题/描述模糊搜索
    - admin 模式：include_all_for_admin=True + target_user_id 可筛指定用户
    返回每条带 thumbnail_url / file_expired / applied_count / owner_name
    """
    db = await get_db()
    try:
        where = []
        params: list = []

        if include_all_for_admin:
            # admin 看所有人（可选 target_user_id 筛选）
            if target_user_id is not None:
                where.append("a.user_id = ?")
                params.append(target_user_id)
        else:
            where.append("a.user_id = ?")
            params.append(user_id)

        if source_type:
            where.append("a.source_type = ?")
            params.append(source_type)
        if q:
            where.append("(a.title LIKE ? OR a.description LIKE ?)")
            params.extend([f"%{q}%", f"%{q}%"])

        where_clause = " AND ".join(where) if where else "1=1"

        # tag 筛选（JSON 数组 LIKE，简单实现：找 '"tag"' 子串）
        # 注意：tag 内容可能含特殊字符，简单场景下用 LIKE 够用
        if tag:
            where_clause += " AND a.tags LIKE ?"
            params.append(f'%"{tag}"%')

        # JOIN 取缩略图 + applied_count + owner_name
        cursor = await db.execute(
            f"""SELECT a.*,
                   u.username AS owner_name,
                   img.file AS img_file, img.thumbnail AS img_thumb, img.file_expired AS img_expired,
                   vid.video_url AS vid_url, vid.file_expired AS vid_expired,
                   (SELECT COUNT(*) FROM asset_applications ap WHERE ap.asset_id = a.id) AS applied_count
            FROM asset_library a
            JOIN users u ON a.user_id = u.id
            LEFT JOIN generation_history img
                  ON a.source_type = 'image' AND a.source_id = img.id
            LEFT JOIN video_tasks vid
                  ON a.source_type = 'video' AND a.source_id = vid.id
            WHERE {where_clause}
            ORDER BY a.created_at DESC""",
            params,
        )
        rows = await cursor.fetchall()
        result = []
        for r in rows:
            d = _row_to_dict(r)
            d["owner_name"] = r["owner_name"]
            d["is_owner"] = r["user_id"] == user_id
            d["applied_count"] = r["applied_count"] or 0
            _apply_thumb_url(d, r, r["id"], r["user_id"])
            result.append(d)
        return result
    finally:
        await db.close()


async def get_asset(asset_id: str) -> dict | None:
    """单条详情（带 thumbnail_url）"""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT a.*, u.username AS owner_name,
                   img.file AS img_file, img.thumbnail AS img_thumb, img.file_expired AS img_expired,
                   vid.video_url AS vid_url, vid.file_expired AS vid_expired
            FROM asset_library a
            JOIN users u ON a.user_id = u.id
            LEFT JOIN generation_history img
                  ON a.source_type = 'image' AND a.source_id = img.id
            LEFT JOIN video_tasks vid
                  ON a.source_type = 'video' AND a.source_id = vid.id
            WHERE a.id = ?""",
            (asset_id,),
        )
        r = await cursor.fetchone()
        if not r:
            return None
        d = _row_to_dict(r)
        d["owner_name"] = r["owner_name"]
        _apply_thumb_url(d, r, r["id"], r["user_id"])
        return d
    finally:
        await db.close()


async def update_asset(asset_id: str, user_id: int, updates: dict) -> dict | None:
    """更新（仅作者 + admin 通过 user_id=-1 旁路）"""
    db = await get_db()
    try:
        # 权限校验（user_id=-1 表示 admin 旁路）
        if user_id != -1:
            cursor = await db.execute(
                "SELECT user_id FROM asset_library WHERE id = ?",
                (asset_id,),
            )
            row = await cursor.fetchone()
            if not row or row["user_id"] != user_id:
                return None

        set_parts = []
        params = []
        for key in ("title", "description"):
            if key in updates and updates[key] is not None:
                set_parts.append(f"{key} = ?")
                params.append(updates[key][:500] if key == "description" else updates[key][:100])
        if "tags" in updates:
            set_parts.append("tags = ?")
            params.append(json.dumps(updates["tags"] or [], ensure_ascii=False))

        if not set_parts:
            cursor = await db.execute("SELECT * FROM asset_library WHERE id = ?", (asset_id,))
            r = await cursor.fetchone()
            return _row_to_dict(r) if r else None

        params.append(asset_id)
        await db.execute(
            f"UPDATE asset_library SET {', '.join(set_parts)} WHERE id = ?",
            params,
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM asset_library WHERE id = ?", (asset_id,))
        return _row_to_dict(await cursor.fetchone())
    finally:
        await db.close()


async def delete_asset(asset_id: str, user_id: int) -> bool:
    """删除（作者或 admin）。
    级联：先删 asset_tracking_records → asset_applications → asset_library
    不删源文件（源文件由 generation_history / video_tasks 管理）
    """
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT user_id FROM asset_library WHERE id = ?",
            (asset_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return False
        if row["user_id"] != user_id and user_id != -1:
            return False  # 无权删

        # 级联删（应用记录 → 价值数据）
        cursor = await db.execute(
            "SELECT id FROM asset_applications WHERE asset_id = ?",
            (asset_id,),
        )
        app_ids = [r["id"] for r in await cursor.fetchall()]
        if app_ids:
            placeholders = ",".join("?" * len(app_ids))
            await db.execute(
                f"DELETE FROM asset_tracking_records WHERE application_id IN ({placeholders})",
                app_ids,
            )
            await db.execute(
                f"DELETE FROM asset_applications WHERE id IN ({placeholders})",
                app_ids,
            )
        await db.execute("DELETE FROM asset_library WHERE id = ?", (asset_id,))
        await db.commit()
        return True
    finally:
        await db.close()


async def delete_asset_admin(asset_id: str) -> bool:
    """admin 强删"""
    return await delete_asset(asset_id, -1)


async def list_tags(user_id: int) -> list[dict]:
    """聚合用户的所有标签 + 出现次数（用于筛选 UI）"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT tags FROM asset_library WHERE user_id = ?",
            (user_id,),
        )
        rows = await cursor.fetchall()
        counter: dict[str, int] = {}
        for r in rows:
            try:
                tags = json.loads(r["tags"]) if r["tags"] else []
            except (json.JSONDecodeError, TypeError):
                tags = []
            for t in tags:
                counter[t] = counter.get(t, 0) + 1
        # 按次数倒序
        return [{"name": k, "count": v} for k, v in sorted(counter.items(), key=lambda x: -x[1])]
    finally:
        await db.close()


# === 检查是否已沉淀（给前端按钮状态用）===

async def is_preserved(user_id: int, source_type: str, source_id: str) -> bool:
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT 1 FROM asset_library
            WHERE user_id = ? AND source_type = ? AND source_id = ? LIMIT 1""",
            (user_id, source_type, source_id),
        )
        return await cursor.fetchone() is not None
    finally:
        await db.close()


# === 应用记录（asset_applications）CRUD ===
# 一个素材可被多个店铺应用 → 每次应用一条独立记录（用户拍板方式 B）

def _app_row_to_dict(r) -> dict:
    return {
        "id": r["id"],
        "asset_id": r["asset_id"],
        "user_id": r["user_id"],
        "shop_name": r["shop_name"],
        "applied_url": r["applied_url"],
        "applied_at": r["applied_at"],
        "notes": r["notes"],
        "created_at": r["created_at"],
    }


async def create_application(data: dict) -> dict:
    """新增应用记录。
    data 必填：asset_id, user_id, shop_name
    可选：applied_url, notes
    会校验 asset_id 归属（必须是本人的素材）
    """
    app_id = _generate_id("aa")
    db = await get_db()
    try:
        # 归属校验
        cursor = await db.execute(
            "SELECT user_id FROM asset_library WHERE id = ?",
            (data["asset_id"],),
        )
        asset_row = await cursor.fetchone()
        if not asset_row:
            raise ValueError("素材不存在")
        asset_owner = asset_row["user_id"]
        # 仅作者或 admin 可标记应用
        if data["user_id"] != asset_owner and data["user_id"] != -1:
            raise PermissionError("无权为他人素材添加应用记录")

        await db.execute(
            """INSERT INTO asset_applications
            (id, asset_id, user_id, shop_name, applied_url, notes)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                app_id,
                data["asset_id"],
                asset_owner,  # 应用记录归素材作者所有
                (data.get("shop_name") or "").strip()[:200],
                (data.get("applied_url") or "").strip()[:1000] or None,
                (data.get("notes") or "").strip()[:1000] or None,
            ),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM asset_applications WHERE id = ?", (app_id,))
        return _app_row_to_dict(await cursor.fetchone())
    finally:
        await db.close()


async def list_applications(
    asset_id: str | None = None,
    user_id: int | None = None,
    shop_name: str | None = None,
    include_all_for_admin: bool = False,
    target_user_id: int | None = None,
) -> list[dict]:
    """列出应用记录。
    - asset_id：按素材筛
    - shop_name：按店铺精确筛
    - admin 模式：include_all_for_admin=True 看所有人
    """
    db = await get_db()
    try:
        where = []
        params: list = []
        if asset_id:
            where.append("asset_id = ?")
            params.append(asset_id)
        if shop_name:
            where.append("shop_name = ?")
            params.append(shop_name)
        if include_all_for_admin:
            if target_user_id is not None:
                where.append("user_id = ?")
                params.append(target_user_id)
        elif user_id is not None:
            where.append("user_id = ?")
            params.append(user_id)

        where_clause = " AND ".join(where) if where else "1=1"
        cursor = await db.execute(
            f"""SELECT * FROM asset_applications
            WHERE {where_clause}
            ORDER BY applied_at DESC, created_at DESC""",
            params,
        )
        rows = await cursor.fetchall()
        return [_app_row_to_dict(r) for r in rows]
    finally:
        await db.close()


async def update_application(app_id: str, user_id: int, updates: dict) -> dict | None:
    """更新（仅作者 + admin 旁路 user_id=-1）"""
    db = await get_db()
    try:
        if user_id != -1:
            cursor = await db.execute(
                "SELECT user_id FROM asset_applications WHERE id = ?",
                (app_id,),
            )
            row = await cursor.fetchone()
            if not row or row["user_id"] != user_id:
                return None

        set_parts = []
        params = []
        for key in ("shop_name", "applied_url", "notes"):
            if key in updates and updates[key] is not None:
                set_parts.append(f"{key} = ?")
                v = updates[key]
                if key == "shop_name":
                    v = v.strip()[:200]
                elif key == "applied_url":
                    v = (v or "").strip()[:1000] or None
                elif key == "notes":
                    v = (v or "").strip()[:1000] or None
                params.append(v)

        if not set_parts:
            cursor = await db.execute("SELECT * FROM asset_applications WHERE id = ?", (app_id,))
            r = await cursor.fetchone()
            return _app_row_to_dict(r) if r else None

        params.append(app_id)
        await db.execute(
            f"UPDATE asset_applications SET {', '.join(set_parts)} WHERE id = ?",
            params,
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM asset_applications WHERE id = ?", (app_id,))
        return _app_row_to_dict(await cursor.fetchone())
    finally:
        await db.close()


async def delete_application(app_id: str, user_id: int) -> bool:
    """删除应用记录（级联删 tracking_records）"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT user_id FROM asset_applications WHERE id = ?",
            (app_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return False
        if row["user_id"] != user_id and user_id != -1:
            return False

        await db.execute("DELETE FROM asset_tracking_records WHERE application_id = ?", (app_id,))
        await db.execute("DELETE FROM asset_applications WHERE id = ?", (app_id,))
        await db.commit()
        return True
    finally:
        await db.close()


async def list_shops(user_id: int, include_all_for_admin: bool = False) -> list[str]:
    """聚合所有店铺名（去重，用于下拉筛选）"""
    db = await get_db()
    try:
        if include_all_for_admin:
            cursor = await db.execute(
                "SELECT DISTINCT shop_name FROM asset_applications ORDER BY shop_name"
            )
        else:
            cursor = await db.execute(
                "SELECT DISTINCT shop_name FROM asset_applications WHERE user_id = ? ORDER BY shop_name",
                (user_id,),
            )
        return [r[0] for r in await cursor.fetchall()]
    finally:
        await db.close()


# === 价值数据快照（asset_tracking_records）CRUD ===
# 每条应用记录可有多期价值数据（时间序列）。运营定期回填播放/点击/转化/GMV。

def _tracking_row_to_dict(r) -> dict:
    return {
        "id": r["id"],
        "application_id": r["application_id"],
        "user_id": r["user_id"],
        "views": r["views"],
        "clicks": r["clicks"],
        "conversions": r["conversions"],
        "gmv": r["gmv"],
        "extra_metrics": json.loads(r["extra_metrics"]) if r["extra_metrics"] else [],
        "notes": r["notes"],
        "recorded_at": r["recorded_at"],
        "created_at": r["created_at"],
    }


async def create_tracking(data: dict) -> dict:
    """新增价值数据快照。
    data 必填：application_id, user_id
    可选：views/clicks/conversions/gmv/extra_metrics/notes/recorded_at
    会校验 application 归属（必须是本人的应用记录）
    """
    tr_id = _generate_id("tr")
    db = await get_db()
    try:
        # 归属校验
        cursor = await db.execute(
            "SELECT user_id FROM asset_applications WHERE id = ?",
            (data["application_id"],),
        )
        app_row = await cursor.fetchone()
        if not app_row:
            raise ValueError("应用记录不存在")
        app_owner = app_row["user_id"]
        if data["user_id"] != app_owner and data["user_id"] != -1:
            raise PermissionError("无权为他人应用记录添加价值数据")

        # 数值字段 NULL 兜底
        def _int(v):
            if v is None or v == "":
                return None
            try:
                return int(v)
            except (ValueError, TypeError):
                return None

        # gmv 是 REAL，其余是 INTEGER
        gmv = None
        if data.get("gmv") not in (None, ""):
            try:
                gmv = float(data["gmv"])
            except (ValueError, TypeError):
                gmv = None

        extra = data.get("extra_metrics") or []
        if not isinstance(extra, list):
            extra = []

        await db.execute(
            """INSERT INTO asset_tracking_records
            (id, application_id, user_id, views, clicks, conversions, gmv,
             extra_metrics, notes, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                tr_id,
                data["application_id"],
                app_owner,
                _int(data.get("views")),
                _int(data.get("clicks")),
                _int(data.get("conversions")),
                gmv,
                json.dumps(extra, ensure_ascii=False),
                (data.get("notes") or "").strip()[:1000] or None,
                data.get("recorded_at") or _now_iso(),
            ),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM asset_tracking_records WHERE id = ?", (tr_id,))
        return _tracking_row_to_dict(await cursor.fetchone())
    finally:
        await db.close()


async def list_tracking(application_id: str) -> list[dict]:
    """列某应用记录的所有价值快照（按录入时间倒序）"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM asset_tracking_records WHERE application_id = ? ORDER BY recorded_at DESC, created_at DESC",
            (application_id,),
        )
        return [_tracking_row_to_dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()


async def update_tracking(record_id: str, user_id: int, updates: dict) -> dict | None:
    """更新（仅作者 + admin 旁路 user_id=-1）"""
    db = await get_db()
    try:
        if user_id != -1:
            cursor = await db.execute(
                "SELECT user_id FROM asset_tracking_records WHERE id = ?",
                (record_id,),
            )
            row = await cursor.fetchone()
            if not row or row["user_id"] != user_id:
                return None

        set_parts = []
        params = []

        def _int(v):
            if v is None or v == "":
                return None
            try:
                return int(v)
            except (ValueError, TypeError):
                return None

        for key in ("views", "clicks", "conversions"):
            if key in updates and updates[key] is not None:
                set_parts.append(f"{key} = ?")
                params.append(_int(updates[key]))
        if "gmv" in updates and updates["gmv"] is not None:
            set_parts.append("gmv = ?")
            v = updates["gmv"]
            try:
                params.append(float(v) if v not in (None, "") else None)
            except (ValueError, TypeError):
                params.append(None)
        if "extra_metrics" in updates and updates["extra_metrics"] is not None:
            set_parts.append("extra_metrics = ?")
            extra = updates["extra_metrics"] or []
            params.append(json.dumps(extra if isinstance(extra, list) else [], ensure_ascii=False))
        if "notes" in updates and updates["notes"] is not None:
            set_parts.append("notes = ?")
            params.append((updates["notes"] or "").strip()[:1000] or None)
        if "recorded_at" in updates and updates["recorded_at"] is not None:
            set_parts.append("recorded_at = ?")
            params.append(updates["recorded_at"])

        if not set_parts:
            cursor = await db.execute("SELECT * FROM asset_tracking_records WHERE id = ?", (record_id,))
            r = await cursor.fetchone()
            return _tracking_row_to_dict(r) if r else None

        params.append(record_id)
        await db.execute(
            f"UPDATE asset_tracking_records SET {', '.join(set_parts)} WHERE id = ?",
            params,
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM asset_tracking_records WHERE id = ?", (record_id,))
        return _tracking_row_to_dict(await cursor.fetchone())
    finally:
        await db.close()


async def delete_tracking(record_id: str, user_id: int) -> bool:
    """删除某条价值快照"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT user_id FROM asset_tracking_records WHERE id = ?",
            (record_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return False
        if row["user_id"] != user_id and user_id != -1:
            return False
        await db.execute("DELETE FROM asset_tracking_records WHERE id = ?", (record_id,))
        await db.commit()
        return True
    finally:
        await db.close()


# === 报表聚合（asset_tracking 页消费）===
# summary：总播放/点击/转化/GMV + Top 素材 + 店铺维度
# list：已应用素材列表，每条带 asset 信息 + 最新一期价值快照

def _build_tracking_where(
    user_id: int,
    include_all_for_admin: bool,
    target_user_id: int | None,
    shop: str | None,
    tag: str | None,
    from_dt: str | None,
    to_dt: str | None,
) -> tuple[str, list]:
    """组装报表筛选 WHERE 子句（基于 application + asset + tracking 三表）"""
    where = []
    params: list = []

    if include_all_for_admin:
        if target_user_id is not None:
            where.append("ap.user_id = ?")
            params.append(target_user_id)
    else:
        where.append("ap.user_id = ?")
        params.append(user_id)

    if shop:
        where.append("ap.shop_name = ?")
        params.append(shop)
    if tag:
        where.append("a.tags LIKE ?")
        params.append(f'%"{tag}"%')
    if from_dt:
        where.append("tr.recorded_at >= ?")
        params.append(from_dt)
    if to_dt:
        where.append("tr.recorded_at <= ?")
        params.append(to_dt)

    return (" AND ".join(where) if where else "1=1"), params


async def get_tracking_summary(
    user_id: int,
    include_all_for_admin: bool = False,
    target_user_id: int | None = None,
    shop: str | None = None,
    tag: str | None = None,
    from_dt: str | None = None,
    to_dt: str | None = None,
) -> dict:
    """报表汇总：总数 + Top 素材（按 GMV）+ 店铺维度"""
    db = await get_db()
    try:
        where, params = _build_tracking_where(
            user_id, include_all_for_admin, target_user_id, shop, tag, from_dt, to_dt
        )

        # 总数（注意：tracking 可能为空，LEFT JOIN 保证 application 行也计入「已应用素材数」）
        cursor = await db.execute(
            f"""SELECT
                COUNT(DISTINCT ap.id) AS application_count,
                COUNT(DISTINCT ap.asset_id) AS asset_count,
                COALESCE(SUM(tr.views), 0) AS total_views,
                COALESCE(SUM(tr.clicks), 0) AS total_clicks,
                COALESCE(SUM(tr.conversions), 0) AS total_conversions,
                COALESCE(SUM(tr.gmv), 0) AS total_gmv
            FROM asset_applications ap
            JOIN asset_library a ON ap.asset_id = a.id
            LEFT JOIN asset_tracking_records tr ON tr.application_id = ap.id
            WHERE {where}""",
            params,
        )
        totals = await cursor.fetchone()

        # Top 素材（按 GMV 倒序，前 10）
        cursor = await db.execute(
            f"""SELECT a.id, a.title, a.source_type,
                   COALESCE(SUM(tr.views), 0) AS sum_views,
                   COALESCE(SUM(tr.conversions), 0) AS sum_conversions,
                   COALESCE(SUM(tr.gmv), 0) AS sum_gmv,
                   COUNT(DISTINCT ap.id) AS app_count
            FROM asset_applications ap
            JOIN asset_library a ON ap.asset_id = a.id
            LEFT JOIN asset_tracking_records tr ON tr.application_id = ap.id
            WHERE {where}
            GROUP BY a.id
            ORDER BY sum_gmv DESC, sum_views DESC
            LIMIT 10""",
            params,
        )
        top_assets = [
            {
                "id": r["id"],
                "title": r["title"],
                "source_type": r["source_type"],
                "sum_views": r["sum_views"],
                "sum_conversions": r["sum_conversions"],
                "sum_gmv": r["sum_gmv"],
                "app_count": r["app_count"],
            }
            for r in await cursor.fetchall()
        ]

        # 店铺维度（按 GMV 倒序）
        cursor = await db.execute(
            f"""SELECT ap.shop_name,
                   COUNT(DISTINCT ap.id) AS app_count,
                   COALESCE(SUM(tr.views), 0) AS sum_views,
                   COALESCE(SUM(tr.conversions), 0) AS sum_conversions,
                   COALESCE(SUM(tr.gmv), 0) AS sum_gmv
            FROM asset_applications ap
            JOIN asset_library a ON ap.asset_id = a.id
            LEFT JOIN asset_tracking_records tr ON tr.application_id = ap.id
            WHERE {where}
            GROUP BY ap.shop_name
            ORDER BY sum_gmv DESC, sum_views DESC""",
            params,
        )
        by_shop = [
            {
                "shop_name": r["shop_name"],
                "app_count": r["app_count"],
                "sum_views": r["sum_views"],
                "sum_conversions": r["sum_conversions"],
                "sum_gmv": r["sum_gmv"],
            }
            for r in await cursor.fetchall()
        ]

        return {
            "application_count": totals["application_count"] or 0,
            "asset_count": totals["asset_count"] or 0,
            "total_views": totals["total_views"] or 0,
            "total_clicks": totals["total_clicks"] or 0,
            "total_conversions": totals["total_conversions"] or 0,
            "total_gmv": totals["total_gmv"] or 0.0,
            "top_assets": top_assets,
            "by_shop": by_shop,
        }
    finally:
        await db.close()


async def list_applications_with_tracking(
    user_id: int,
    include_all_for_admin: bool = False,
    target_user_id: int | None = None,
    shop: str | None = None,
    tag: str | None = None,
    from_dt: str | None = None,
    to_dt: str | None = None,
) -> list[dict]:
    """已应用素材列表，每行 = 一个 application，带 asset 信息 + 最新一期价值快照 + 全部历史累计"""
    db = await get_db()
    try:
        # 注意：这里 WHERE 用 application 维度（不用 tr 的 recorded_at 过滤，
        # 否则没录过价值的 application 会被滤掉）。时间区间在 Python 里对 latest 过滤。
        where = []
        params: list = []
        if include_all_for_admin:
            if target_user_id is not None:
                where.append("ap.user_id = ?")
                params.append(target_user_id)
        else:
            where.append("ap.user_id = ?")
            params.append(user_id)
        if shop:
            where.append("ap.shop_name = ?")
            params.append(shop)
        if tag:
            where.append("a.tags LIKE ?")
            params.append(f'%"{tag}"%')

        where_clause = " AND ".join(where) if where else "1=1"

        cursor = await db.execute(
            f"""SELECT ap.id AS app_id, ap.asset_id, ap.shop_name, ap.applied_url,
                   ap.applied_at, ap.notes AS app_notes, ap.user_id AS app_user_id,
                   a.title, a.description, a.source_type, a.tags,
                   img.thumbnail AS img_thumb, img.file_expired AS img_expired,
                   vid.video_url AS vid_url, vid.file_expired AS vid_expired,
                   u.username AS owner_name
            FROM asset_applications ap
            JOIN asset_library a ON ap.asset_id = a.id
            JOIN users u ON ap.user_id = u.id
            LEFT JOIN generation_history img
                  ON a.source_type = 'image' AND a.source_id = img.id
            LEFT JOIN video_tasks vid
                  ON a.source_type = 'video' AND a.source_id = vid.id
            WHERE {where_clause}
            ORDER BY ap.applied_at DESC""",
            params,
        )
        rows = await cursor.fetchall()

        # 批量取这些 application 的全部 tracking 记录
        app_ids = [r["app_id"] for r in rows]
        tracking_map: dict[str, list[dict]] = {}
        if app_ids:
            placeholders = ",".join("?" * len(app_ids))
            cursor = await db.execute(
                f"""SELECT * FROM asset_tracking_records
                WHERE application_id IN ({placeholders})
                ORDER BY recorded_at DESC, created_at DESC""",
                app_ids,
            )
            for tr in await cursor.fetchall():
                tracking_map.setdefault(tr["application_id"], []).append(_tracking_row_to_dict(tr))

        result = []
        for r in rows:
            records = tracking_map.get(r["app_id"], [])
            # 时间区间过滤（针对 latest；若 latest 被过滤掉则该行仍保留但 latest=null）
            if from_dt or to_dt:
                filtered = [
                    t for t in records
                    if (not from_dt or (t.get("recorded_at") or "") >= from_dt)
                    and (not to_dt or (t.get("recorded_at") or "") <= to_dt)
                ]
            else:
                filtered = records

            latest = filtered[0] if filtered else None
            # 全部历史累计（不受时间区间影响，反映该 application 累计价值）
            cumulative_views = sum((t.get("views") or 0) for t in records)
            cumulative_clicks = sum((t.get("clicks") or 0) for t in records)
            cumulative_conversions = sum((t.get("conversions") or 0) for t in records)
            cumulative_gmv = sum((t.get("gmv") or 0) for t in records)

            # 缩略图
            if r["source_type"] == "image":
                thumb = f"/gen-files/{r['app_user_id']}/{r['img_thumb']}" if r["img_thumb"] else None
                file_expired = bool(r["img_expired"]) if r["img_expired"] is not None else True
                thumb_is_image = bool(thumb)
            elif r["source_type"] == "video":
                # vid_url 已是 /video-files/... 完整 URL，不再拼前缀
                thumb = r["vid_url"] or None
                file_expired = bool(r["vid_expired"]) if r["vid_expired"] is not None else True
                thumb_is_image = False
            else:
                thumb = None
                file_expired = True
                thumb_is_image = False

            result.append({
                "app_id": r["app_id"],
                "asset_id": r["asset_id"],
                "shop_name": r["shop_name"],
                "applied_url": r["applied_url"],
                "applied_at": r["applied_at"],
                "app_notes": r["app_notes"],
                "asset": {
                    "id": r["asset_id"],
                    "title": r["title"],
                    "description": r["description"],
                    "source_type": r["source_type"],
                    "tags": json.loads(r["tags"]) if r["tags"] else [],
                    "thumbnail_url": thumb,
                    "thumbnail_is_image": thumb_is_image,
                    "file_expired": file_expired,
                },
                "owner_name": r["owner_name"],
                "is_owner": r["app_user_id"] == user_id,
                "tracking_count": len(records),
                "latest_tracking": latest,
                "cumulative": {
                    "views": cumulative_views,
                    "clicks": cumulative_clicks,
                    "conversions": cumulative_conversions,
                    "gmv": cumulative_gmv,
                },
                "history": records,  # 全部历史快照（用于录入弹窗内编辑/删除）
            })
        return result
    finally:
        await db.close()

