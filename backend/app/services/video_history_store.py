# 视频历史存储服务 - SQLite + 文件管理（参考 history_store.py）
import logging
import shutil
from pathlib import Path

from app.config import settings
from app.database import get_db
from app.services.video_utils import get_temp_dir, get_video_abs_path

logger = logging.getLogger(__name__)

# 视频文件保留天数（到期删盘 + 标记 file_expired）
FILE_EXPIRE_DAYS = settings.video_expire_seconds // 86400  # 3
# 视频元数据保留天数（到期 DELETE 整行）
RECORD_EXPIRE_DAYS = settings.video_history_record_expire_days  # 90


async def list_video_history(
    user_id: int,
    limit: int = 200,
    offset: int = 0,
) -> list[dict]:
    """获取用户的视频历史（仅 completed，按时间倒序，自动隐藏用户软删的）"""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT id, prompt, provider_name, resolution, video_url,
                      cost, currency, file_expired, user_deleted, user_deleted_at, created_at
            FROM video_tasks
            WHERE user_id = ? AND status = 'completed' AND user_deleted = 0
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?""",
            (user_id, limit, offset),
        )
        rows = await cursor.fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        await db.close()


async def list_all_video_history(
    include_deleted: bool = False,
    limit: int = 200,
    offset: int = 0,
) -> list[dict]:
    """管理员获取所有用户的视频历史

    include_deleted=False（默认）：只看未被用户软删的
    include_deleted=True：包含用户软删的记录（admin 审计用）
    """
    db = await get_db()
    try:
        where_parts = ["t.status = 'completed'"]
        params: list = []
        if not include_deleted:
            where_parts.append("t.user_deleted = 0")
        where_clause = "WHERE " + " AND ".join(where_parts)

        sql = f"""SELECT t.id, t.prompt, t.provider_name, t.resolution, t.video_url,
                  t.cost, t.currency, t.file_expired, t.user_deleted, t.user_deleted_at,
                  t.created_at, t.user_id, u.username
            FROM video_tasks t JOIN users u ON t.user_id = u.id
            {where_clause}
            ORDER BY t.created_at DESC
            LIMIT ? OFFSET ?"""
        params.extend([limit, offset])
        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()
        return [_row_to_dict(r, include_user=True) for r in rows]
    finally:
        await db.close()


def _row_to_dict(r, include_user: bool = False) -> dict:
    d = {
        "id": r["id"],
        "prompt": r["prompt"],
        "provider_name": r["provider_name"],
        "resolution": r["resolution"],
        "video_url": r["video_url"],
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


async def delete_video_history_any(task_id: str) -> bool:
    """管理员硬删任意一条视频历史（真删，不可恢复）"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT video_url FROM video_tasks WHERE id = ?",
            (task_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return False

        _safe_unlink(row["video_url"])

        await db.execute("DELETE FROM video_tasks WHERE id = ?", (task_id,))
        await db.commit()
        logger.info(f"管理员硬删视频历史: {task_id}")
        return True
    finally:
        await db.close()


async def clear_all_video_history_admin(username: str | None = None) -> int:
    """管理员硬删全部视频历史（真删：删盘文件 + DELETE 整行，不可恢复）

    Args:
        username: 指定用户名则只清该用户，None 则清所有用户
    返回删除条数
    """
    db = await get_db()
    try:
        if username:
            cursor = await db.execute("SELECT id FROM users WHERE username = ?", (username,))
            u = await cursor.fetchone()
            if not u:
                return 0
            uid = u["id"]
            # 先查出要删的视频文件
            cursor = await db.execute(
                "SELECT video_url FROM video_tasks WHERE user_id = ? AND status = 'completed'",
                (uid,),
            )
            rows = await cursor.fetchall()
            for r in rows:
                _safe_unlink(r["video_url"])
            cursor = await db.execute(
                "SELECT COUNT(*) FROM video_tasks WHERE user_id = ? AND status = 'completed'",
                (uid,),
            )
            count = (await cursor.fetchone())[0] or 0
            await db.execute(
                "DELETE FROM video_tasks WHERE user_id = ? AND status = 'completed'",
                (uid,),
            )
            await db.commit()
            user_dir = get_temp_dir() / str(uid)
            if user_dir.exists():
                shutil.rmtree(user_dir, ignore_errors=True)
                user_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"管理员硬删用户 {username}(id={uid}) 全部视频历史，共 {count} 条")
        else:
            cursor = await db.execute(
                "SELECT video_url FROM video_tasks WHERE status = 'completed'"
            )
            rows = await cursor.fetchall()
            for r in rows:
                _safe_unlink(r["video_url"])
            cursor = await db.execute(
                "SELECT COUNT(*) FROM video_tasks WHERE status = 'completed'"
            )
            count = (await cursor.fetchone())[0] or 0
            await db.execute("DELETE FROM video_tasks WHERE status = 'completed'")
            await db.commit()
            # 清空整个 temp_dir 下所有用户子目录
            temp = get_temp_dir()
            if temp.exists():
                for child in temp.iterdir():
                    if child.is_dir():
                        shutil.rmtree(child, ignore_errors=True)
            logger.info(f"管理员硬删所有用户视频历史，共 {count} 条")
        return count
    finally:
        await db.close()


async def cleanup_expired_video_history() -> int:
    """分层清理视频历史记录（仅 completed 任务）：
    - 文件过期（FILE_EXPIRE_DAYS，默认 3 天）：删磁盘文件 + 标记 file_expired=1
    - 记录过期（RECORD_EXPIRE_DAYS，默认 90 天）：DELETE 整行
    返回处理的记录数
    """
    db = await get_db()
    try:
        # 阶段 1：文件过期 → 删盘 + 标记 file_expired=1（只处理尚未标记的）
        cursor = await db.execute(
            """SELECT id, video_url FROM video_tasks
            WHERE status = 'completed' AND file_expired = 0
              AND created_at < datetime('now', 'localtime', ?)""",
            (f"-{FILE_EXPIRE_DAYS} days",),
        )
        file_rows = await cursor.fetchall()

        for r in file_rows:
            _safe_unlink(r["video_url"])

        if file_rows:
            file_ids = [r["id"] for r in file_rows]
            placeholders = ",".join("?" * len(file_ids))
            await db.execute(
                f"UPDATE video_tasks SET file_expired = 1 WHERE id IN ({placeholders})",
                file_ids,
            )

        # 阶段 2：记录过期 → DELETE 整行（文件阶段 1 已删，无需再删）
        cursor = await db.execute(
            """SELECT id FROM video_tasks
            WHERE status = 'completed' AND created_at < datetime('now', 'localtime', ?)""",
            (f"-{RECORD_EXPIRE_DAYS} days",),
        )
        record_rows = await cursor.fetchall()
        if record_rows:
            record_ids = [r["id"] for r in record_rows]
            placeholders = ",".join("?" * len(record_ids))
            await db.execute(
                f"DELETE FROM video_tasks WHERE id IN ({placeholders})",
                record_ids,
            )

        await db.commit()
        return len(file_rows) + len(record_rows)
    finally:
        await db.close()


def _safe_unlink(video_url: str | None) -> None:
    """安全删除磁盘视频文件（从 video_url 反推路径，is_relative_to 校验防越权）"""
    if not video_url:
        return
    abs_path = get_video_abs_path(video_url)
    if abs_path is None:
        return
    try:
        if abs_path.exists():
            abs_path.unlink()
    except OSError as e:
        logger.warning(f"删除视频文件失败 {abs_path}: {e}")


def delete_user_video_files(user_id: int):
    """删除用户的所有视频文件（删除用户账号时调用）"""
    user_dir = get_temp_dir() / str(user_id)
    if user_dir.exists():
        shutil.rmtree(user_dir, ignore_errors=True)
        logger.info(f"已清理用户 {user_id} 的视频文件")
