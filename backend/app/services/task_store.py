# 视频任务存储 - SQLite 持久化
import logging
import time

from app.database import get_db

logger = logging.getLogger(__name__)

TASK_EXPIRE_SECONDS = 3600  # 已完成任务保留 1 小时


async def create_task(task_id: str, user_id: int, external_id: str, provider_name: str, prompt: str, resolution: str | None = None):
    """创建视频任务记录"""
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO video_tasks (id, user_id, external_id, provider_name, prompt, status, resolution) VALUES (?, ?, ?, ?, ?, 'pending', ?)",
            (task_id, user_id, external_id, provider_name, prompt, resolution),
        )
        await db.commit()
    finally:
        await db.close()


async def get_task(task_id: str) -> dict | None:
    """获取任务信息"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM video_tasks WHERE id = ?", (task_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def update_task_status(task_id: str, status: str, video_url: str | None = None, error: str | None = None):
    """更新任务状态"""
    db = await get_db()
    try:
        if status in ("completed", "failed"):
            await db.execute(
                "UPDATE video_tasks SET status = ?, video_url = ?, error = ?, completed_at = datetime('now', 'localtime') WHERE id = ?",
                (status, video_url, error, task_id),
            )
        else:
            await db.execute(
                "UPDATE video_tasks SET status = ? WHERE id = ?",
                (status, task_id),
            )
        await db.commit()
    finally:
        await db.close()


async def cleanup_expired_tasks():
    """清理过期任务"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "DELETE FROM video_tasks WHERE status IN ('completed', 'failed') AND completed_at < datetime('now', '-1 hour', 'localtime')"
        )
        count = cursor.rowcount
        if count > 0:
            logger.info(f"清理过期视频任务: {count} 个")
        return count
    finally:
        await db.close()
