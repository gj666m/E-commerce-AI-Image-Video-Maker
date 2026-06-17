# 图片生成历史存储服务 - SQLite + 文件管理
import io
import json
import logging
import time
from pathlib import Path

from PIL import Image

from app.config import settings
from app.database import get_db

logger = logging.getLogger(__name__)

# 历史图根目录
HISTORY_DIR = Path(settings.generation_history_dir).resolve()
THUMB_SIZE = 400  # 历史缩略图较大，便于前端网格预览


def _user_dir(user_id: int) -> Path:
    """获取用户的历史图目录"""
    d = HISTORY_DIR / str(user_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _generate_id() -> str:
    return f"gen_{int(time.time() * 1000)}"


def _create_thumbnail(image_bytes: bytes) -> bytes:
    """生成缩略图（JPEG，长边 400px）"""
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    w, h = img.size
    ratio = THUMB_SIZE / max(w, h)
    new_w, new_h = max(1, int(w * ratio)), max(1, int(h * ratio))
    img = img.resize((new_w, new_h), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()


async def save_history(
    user_id: int,
    task_type: str,
    prompt: str,
    params: dict,
    model_used: str,
    image_bytes: bytes,
    cost: float = 0.0,
    currency: str = "¥",
) -> dict | None:
    """保存一张生成图到历史

    Args:
        image_bytes: 已后处理的最终图片二进制（将原样落盘 + 生成缩略图）
    返回历史记录 dict，失败返回 None（不影响主流程）
    """
    try:
        history_id = _generate_id()
        user_d = _user_dir(user_id)

        # 原图统一存为 jpeg（减小体积）
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        orig_buf = io.BytesIO()
        img.save(orig_buf, format="JPEG", quality=92)
        orig_bytes = orig_buf.getvalue()

        img_path = user_d / f"{history_id}.jpeg"
        img_path.write_bytes(orig_bytes)

        # 缩略图
        thumb_bytes = _create_thumbnail(image_bytes)
        thumb_path = user_d / f"{history_id}_thumb.jpeg"
        thumb_path.write_bytes(thumb_bytes)

        db = await get_db()
        try:
            await db.execute(
                """INSERT INTO generation_history
                (id, user_id, task_type, prompt, params, model_used, file, thumbnail, cost, currency)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    history_id, user_id, task_type, prompt,
                    json.dumps(params, ensure_ascii=False),
                    model_used,
                    f"{history_id}.jpeg",
                    f"{history_id}_thumb.jpeg",
                    cost, currency,
                ),
            )
            await db.commit()
        finally:
            await db.close()

        return {
            "id": history_id,
            "task_type": task_type,
            "prompt": prompt,
            "params": params,
            "model_used": model_used,
            "file": f"{user_id}/{history_id}.jpeg",
            "thumbnail": f"{user_id}/{history_id}_thumb.jpeg",
            "cost": cost,
            "currency": currency,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
    except Exception as e:
        logger.warning(f"保存历史失败（不影响主流程）: {e}")
        return None


async def list_history(
    user_id: int,
    task_type: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[dict]:
    """获取用户的历史列表（按时间倒序，自动隐藏用户自己软删的）"""
    db = await get_db()
    try:
        if task_type:
            cursor = await db.execute(
                """SELECT id, task_type, prompt, params, model_used, file, thumbnail, cost, currency,
                          file_expired, user_deleted, user_deleted_at, created_at
                FROM generation_history
                WHERE user_id = ? AND task_type = ? AND user_deleted = 0
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?""",
                (user_id, task_type, limit, offset),
            )
        else:
            cursor = await db.execute(
                """SELECT id, task_type, prompt, params, model_used, file, thumbnail, cost, currency,
                          file_expired, user_deleted, user_deleted_at, created_at
                FROM generation_history
                WHERE user_id = ? AND user_deleted = 0
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?""",
                (user_id, limit, offset),
            )
        rows = await cursor.fetchall()
        return [_row_to_dict(r, user_id) for r in rows]
    finally:
        await db.close()


async def list_all_history(
    task_type: str | None = None,
    include_deleted: bool = False,
    limit: int = 200,
    offset: int = 0,
) -> list[dict]:
    """管理员获取所有用户的历史

    include_deleted=False（默认）：只看未被用户软删的
    include_deleted=True：包含用户软删的记录（admin 审计用）
    """
    db = await get_db()
    try:
        # 构造 WHERE：默认排除 user_deleted=1
        where_parts = []
        params: list = []
        if task_type:
            where_parts.append("h.task_type = ?")
            params.append(task_type)
        if not include_deleted:
            where_parts.append("h.user_deleted = 0")
        where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

        sql = f"""SELECT h.id, h.task_type, h.prompt, h.params, h.model_used, h.file, h.thumbnail,
                  h.cost, h.currency, h.file_expired, h.user_deleted, h.user_deleted_at,
                  h.created_at, h.user_id, u.username
            FROM generation_history h JOIN users u ON h.user_id = u.id
            {where_clause}
            ORDER BY h.created_at DESC
            LIMIT ? OFFSET ?"""
        params.extend([limit, offset])
        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()
        return [_row_to_dict(r, r["user_id"], include_user=True) for r in rows]
    finally:
        await db.close()


def _row_to_dict(r, user_id: int, include_user: bool = False) -> dict:
    d = {
        "id": r["id"],
        "task_type": r["task_type"],
        "prompt": r["prompt"],
        "params": json.loads(r["params"]),
        "model_used": r["model_used"],
        "file": f"{user_id}/{r['file']}",
        "thumbnail": f"{user_id}/{r['thumbnail']}",
        "cost": r["cost"],
        "currency": r["currency"],
        "file_expired": bool(r["file_expired"]),
        "user_deleted": bool(r["user_deleted"]),
        "user_deleted_at": r["user_deleted_at"],
        "created_at": r["created_at"],
    }
    if include_user:
        d["user_id"] = r["user_id"]
        d["username"] = r["username"]
    return d


async def delete_history(user_id: int, history_id: str) -> bool:
    """用户软删单条历史（只能软删自己的）

    行为：删盘文件 + 标记 user_deleted=1（元数据保留，admin 仍可见）
    """
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT file, thumbnail FROM generation_history WHERE id = ? AND user_id = ?",
            (history_id, user_id),
        )
        row = await cursor.fetchone()
        if not row:
            return False

        # 删磁盘文件（节省空间，DB 元数据保留）
        user_d = _user_dir(user_id)
        for key in ("file", "thumbnail"):
            fname = Path(row[key]).name
            fpath = (user_d / fname).resolve()
            if not fpath.is_relative_to(user_d):
                continue
            try:
                if fpath.exists():
                    fpath.unlink()
            except OSError as e:
                logger.warning(f"删除历史文件失败 {fpath}: {e}")

        # 软删：标记 + 记录时间，不 DELETE
        await db.execute(
            """UPDATE generation_history
               SET user_deleted = 1, user_deleted_at = datetime('now', 'localtime')
               WHERE id = ?""",
            (history_id,),
        )
        await db.commit()
        logger.info(f"用户软删历史: {history_id} (user={user_id})")
        return True
    finally:
        await db.close()


async def delete_history_any(history_id: str) -> bool:
    """管理员硬删任意一条历史（真删，不可恢复）"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT file, thumbnail, user_id FROM generation_history WHERE id = ?",
            (history_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return False

        user_d = HISTORY_DIR / str(row["user_id"])
        for key in ("file", "thumbnail"):
            fname = Path(row[key]).name
            fpath = (user_d / fname).resolve()
            if not fpath.is_relative_to(user_d):
                continue
            try:
                if fpath.exists():
                    fpath.unlink()
            except OSError as e:
                logger.warning(f"删除历史文件失败 {fpath}: {e}")

        await db.execute("DELETE FROM generation_history WHERE id = ?", (history_id,))
        await db.commit()
        logger.info(f"管理员硬删历史: {history_id}")
        return True
    finally:
        await db.close()


async def clear_user_history(user_id: int) -> int:
    """用户清空自己的全部历史（软删：文件删，元数据保留，admin 仍可见）

    返回处理的条数
    """
    db = await get_db()
    try:
        # 只统计尚未软删的条数（避免重复清空时返回虚高数字）
        cursor = await db.execute(
            "SELECT COUNT(*) FROM generation_history WHERE user_id = ? AND user_deleted = 0",
            (user_id,),
        )
        row = await cursor.fetchone()
        count = row[0] if row else 0

        # 软删所有未软删的
        await db.execute(
            """UPDATE generation_history
               SET user_deleted = 1, user_deleted_at = datetime('now', 'localtime')
               WHERE user_id = ? AND user_deleted = 0""",
            (user_id,),
        )
        await db.commit()
    finally:
        await db.close()

    # 清空磁盘文件（用户已经看不到了，文件留着也是浪费空间）
    user_d = _user_dir(user_id)
    if user_d.exists():
        import shutil
        shutil.rmtree(user_d, ignore_errors=True)
        user_d.mkdir(parents=True, exist_ok=True)

    logger.info(f"用户 {user_id} 清空历史（软删），共 {count} 条")
    return count


async def cleanup_expired_history() -> int:
    """分层清理历史记录：
    - 文件过期（generation_history_expire_days，默认 3 天）：删磁盘文件 + 标记 file_expired=1，元数据保留
    - 记录过期（generation_history_record_expire_days，默认 90 天）：DELETE 整行
    返回处理的记录数（删文件 + 删行总和）
    """
    file_days = settings.generation_history_expire_days
    record_days = settings.generation_history_record_expire_days
    db = await get_db()
    try:
        # 阶段 1：文件过期 → 删盘 + 标记 file_expired=1（只处理尚未标记的）
        cursor = await db.execute(
            """SELECT id, user_id, file, thumbnail FROM generation_history
            WHERE file_expired = 0
              AND created_at < datetime('now', 'localtime', ?)""",
            (f"-{file_days} days",),
        )
        file_rows = await cursor.fetchall()

        for r in file_rows:
            user_d = HISTORY_DIR / str(r["user_id"])
            for key in ("file", "thumbnail"):
                fname = Path(r[key]).name
                fpath = (user_d / fname).resolve()
                if not fpath.is_relative_to(user_d):
                    continue
                try:
                    if fpath.exists():
                        fpath.unlink()
                except OSError:
                    pass

        if file_rows:
            file_ids = [r["id"] for r in file_rows]
            placeholders = ",".join("?" * len(file_ids))
            await db.execute(
                f"UPDATE generation_history SET file_expired = 1 WHERE id IN ({placeholders})",
                file_ids,
            )

        # 阶段 2：记录过期 → DELETE 整行（不再删文件，阶段 1 已删）
        cursor = await db.execute(
            """SELECT id FROM generation_history
            WHERE created_at < datetime('now', 'localtime', ?)""",
            (f"-{record_days} days",),
        )
        record_rows = await cursor.fetchall()
        if record_rows:
            record_ids = [r["id"] for r in record_rows]
            placeholders = ",".join("?" * len(record_ids))
            await db.execute(
                f"DELETE FROM generation_history WHERE id IN ({placeholders})",
                record_ids,
            )

        await db.commit()
        return len(file_rows) + len(record_rows)
    finally:
        await db.close()


def delete_user_history_files(user_id: int):
    """删除用户的所有历史文件（删除用户时调用）"""
    user_d = HISTORY_DIR / str(user_id)
    if user_d.exists():
        import shutil
        shutil.rmtree(user_d, ignore_errors=True)
        logger.info(f"已清理用户 {user_id} 的历史文件")
