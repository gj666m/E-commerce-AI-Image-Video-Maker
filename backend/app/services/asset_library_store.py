# 素材资产库存储服务（续19）
# asset_library 是已生成图/视频的沉淀池。运营把好图好视频沉淀下来，
# 加自定义标签，后续用于店铺应用追踪 + 价值数据回填。
#
# 不存文件：直接 JOIN generation_history / video_tasks 取 file/thumbnail。
# 文件保留：history/video 清理任务用 NOT IN 跳过已沉淀素材（永久保留）。
import json
import logging
import time

from app.database import get_db

logger = logging.getLogger(__name__)


def _generate_id(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000)}"


def _row_to_dict(r) -> dict:
    """行转 dict + 解析 tags JSON"""
    return {
        "id": r["id"],
        "user_id": r["user_id"],
        "source_type": r["source_type"],
        "source_id": r["source_id"],
        "title": r["title"],
        "description": r["description"],
        "tags": json.loads(r["tags"]) if r["tags"] else [],
        "created_at": r["created_at"],
    }


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
            (id, user_id, source_type, source_id, title, description, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                asset_id,
                data["user_id"],
                data["source_type"],
                data["source_id"],
                data["title"][:100],
                (data.get("description") or "").strip()[:500] or None,
                json.dumps(data.get("tags") or [], ensure_ascii=False),
            ),
        )
        await db.commit()
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
            # 拼 thumbnail_url + file_expired
            if r["source_type"] == "image":
                d["thumbnail_url"] = f"/gen-files/{r['user_id']}/{r['img_thumb']}" if r["img_thumb"] else None
                d["file_expired"] = bool(r["img_expired"]) if r["img_expired"] is not None else True
            elif r["source_type"] == "video":
                d["thumbnail_url"] = f"/video-files/{r['vid_url']}" if r["vid_url"] else None
                d["file_expired"] = bool(r["vid_expired"]) if r["vid_expired"] is not None else True
            else:
                d["thumbnail_url"] = None
                d["file_expired"] = True
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
        if r["source_type"] == "image":
            d["thumbnail_url"] = f"/gen-files/{r['user_id']}/{r['img_thumb']}" if r["img_thumb"] else None
            d["file_expired"] = bool(r["img_expired"]) if r["img_expired"] is not None else True
        elif r["source_type"] == "video":
            d["thumbnail_url"] = f"/video-files/{r['vid_url']}" if r["vid_url"] else None
            d["file_expired"] = bool(r["vid_expired"]) if r["vid_expired"] is not None else True
        else:
            d["thumbnail_url"] = None
            d["file_expired"] = True
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
