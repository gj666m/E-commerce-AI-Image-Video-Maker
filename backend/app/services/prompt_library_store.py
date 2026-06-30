# Prompt 复用库存储服务
import json
import logging
import time

from app.database import get_db

logger = logging.getLogger(__name__)


def _generate_id() -> str:
    return f"pl_{int(time.time() * 1000)}"


def _row_to_dict(r) -> dict:
    """行转 dict + 解析 tags/elements JSON + 附加 sample_image 完整相对路径"""
    sample_image = r["sample_image"]
    # elements（续18 工坊 8 要素 JSON，可空）
    raw_elements = r["elements"] if "elements" in r.keys() else None
    elements = None
    if raw_elements:
        try:
            elements = json.loads(raw_elements)
        except (json.JSONDecodeError, TypeError):
            elements = None
    return {
        "id": r["id"],
        "user_id": r["user_id"],
        "task_type": r["task_type"],
        "title": r["title"],
        "description": r["description"],
        "full_prompt": r["full_prompt"],
        "model_used": r["model_used"],
        "aspect_ratio": r["aspect_ratio"],
        "sample_image": sample_image,
        "sample_kind": r["sample_kind"] or "image",
        "tags": json.loads(r["tags"]) if r["tags"] else [],
        "elements": elements,
        "is_shared": bool(r["is_shared"]),
        "use_count": r["use_count"],
        "created_at": r["created_at"],
    }


async def create_prompt(data: dict) -> dict:
    """创建 Prompt 库记录"""
    prompt_id = _generate_id()
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO prompt_library
            (id, user_id, task_type, title, description, full_prompt, model_used,
             aspect_ratio, sample_image, sample_kind, tags, elements, is_shared)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                prompt_id,
                data["user_id"],
                data["task_type"],
                data["title"],
                data.get("description"),
                data["full_prompt"],
                data.get("model_used"),
                data.get("aspect_ratio"),
                data.get("sample_image"),
                data.get("sample_kind", "image"),
                json.dumps(data.get("tags") or [], ensure_ascii=False),
                # elements 序列化为 JSON 字符串；None → NULL（续18）
                json.dumps(data["elements"], ensure_ascii=False) if data.get("elements") else None,
                1 if data.get("is_shared") else 0,
            ),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM prompt_library WHERE id = ?", (prompt_id,))
        row = await cursor.fetchone()
        return _row_to_dict(row)
    finally:
        await db.close()


async def list_prompts(
    user_id: int,
    task_type: str | None = None,
    include_shared: bool = True,
) -> list[dict]:
    """列出 Prompt：自己的 + （可选）他人共享的"""
    db = await get_db()
    try:
        params: list = [user_id]
        where = ["(p.user_id = ?"]
        if include_shared:
            where.append(" OR p.is_shared = 1")
        where_clause = "".join(where) + ")"
        if task_type:
            where_clause += " AND p.task_type = ?"
            params.append(task_type)

        cursor = await db.execute(
            f"""SELECT p.*, u.username AS owner_name
                FROM prompt_library p JOIN users u ON p.user_id = u.id
                WHERE {where_clause}
                ORDER BY p.is_shared DESC, p.use_count DESC, p.created_at DESC""",
            params,
        )
        rows = await cursor.fetchall()
        result = []
        for r in rows:
            d = _row_to_dict(r)
            d["owner_name"] = r["owner_name"]
            d["is_owner"] = r["user_id"] == user_id
            result.append(d)
        return result
    finally:
        await db.close()


async def get_prompt(prompt_id: str) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM prompt_library WHERE id = ?",
            (prompt_id,),
        )
        row = await cursor.fetchone()
        return _row_to_dict(row) if row else None
    finally:
        await db.close()


async def update_prompt(prompt_id: str, user_id: int, updates: dict) -> dict | None:
    """更新 Prompt（只能改自己的）"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT user_id FROM prompt_library WHERE id = ?",
            (prompt_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        if row["user_id"] != user_id:
            return None  # 无权改

        set_parts = []
        params = []
        for key in ("title", "description", "full_prompt", "model_used", "aspect_ratio"):
            if key in updates and updates[key] is not None:
                set_parts.append(f"{key} = ?")
                params.append(updates[key])
        if "is_shared" in updates:
            set_parts.append("is_shared = ?")
            params.append(1 if updates["is_shared"] else 0)
        if "tags" in updates:
            set_parts.append("tags = ?")
            params.append(json.dumps(updates["tags"] or [], ensure_ascii=False))
        if "elements" in updates:
            # elements: dict → JSON；None 或空 dict → NULL（续18）
            el = updates["elements"]
            set_parts.append("elements = ?")
            params.append(json.dumps(el, ensure_ascii=False) if el else None)

        if not set_parts:
            cursor = await db.execute("SELECT * FROM prompt_library WHERE id = ?", (prompt_id,))
            return _row_to_dict(await cursor.fetchone())

        params.append(prompt_id)
        await db.execute(
            f"UPDATE prompt_library SET {', '.join(set_parts)} WHERE id = ?",
            params,
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM prompt_library WHERE id = ?", (prompt_id,))
        return _row_to_dict(await cursor.fetchone())
    finally:
        await db.close()


async def delete_prompt(prompt_id: str, user_id: int) -> bool:
    """删除（只能删自己的；admin 可删任意，外层判断 role）"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT user_id FROM prompt_library WHERE id = ?",
            (prompt_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return False
        if row["user_id"] != user_id:
            return False
        await db.execute("DELETE FROM prompt_library WHERE id = ?", (prompt_id,))
        await db.commit()
        return True
    finally:
        await db.close()


async def delete_prompt_admin(prompt_id: str) -> bool:
    """admin 强删任意"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "DELETE FROM prompt_library WHERE id = ?",
            (prompt_id,),
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def increment_use_count(prompt_id: str) -> None:
    """标记被复用（use_count += 1）"""
    db = await get_db()
    try:
        await db.execute(
            "UPDATE prompt_library SET use_count = use_count + 1 WHERE id = ?",
            (prompt_id,),
        )
        await db.commit()
    finally:
        await db.close()
