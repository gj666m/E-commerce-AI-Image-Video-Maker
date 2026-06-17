# 视频任务存储 - SQLite 持久化
import logging
import time

from app.database import get_db

logger = logging.getLogger(__name__)

TASK_EXPIRE_SECONDS = 3600  # 已完成任务保留 1 小时


async def create_task(
    task_id: str,
    user_id: int,
    external_id: str,
    provider_name: str,
    prompt: str,
    resolution: str | None = None,
    balance_before: int | None = None,
):
    """创建视频任务记录

    balance_before: 提交任务前的 API易 quota 快照，用于完成后算真实扣费
    """
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO video_tasks (id, user_id, external_id, provider_name, prompt, status, resolution, balance_before) "
            "VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)",
            (task_id, user_id, external_id, provider_name, prompt, resolution, balance_before),
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


def compute_real_cost(balance_before: int | None, balance_after: int | None) -> float | None:
    """根据前后 quota 快照算真实 USD 花费

    返回 None 表示无法计算（降级用 token 估算）
    """
    if balance_before is None or balance_after is None:
        return None
    diff = balance_before - balance_after
    if diff <= 0:
        # 差值为 0 或负（并发干扰），不可信，降级
        return None
    return round(diff / 500000, 4)  # 500000 quota = $1


async def update_task_status(
    task_id: str,
    status: str,
    video_url: str | None = None,
    error: str | None = None,
    cost: float | None = None,
    currency: str | None = None,
):
    """更新任务状态

    cost/currency 仅在首次完成时传入，用于持久化真实扣费
    """
    db = await get_db()
    try:
        if status in ("completed", "failed"):
            # 用 COALESCE 保证 cost/currency 列只在传入时更新，不覆盖已有值
            await db.execute(
                """UPDATE video_tasks
                   SET status = ?, video_url = ?, error = ?,
                       cost = COALESCE(?, cost),
                       currency = COALESCE(?, currency),
                       completed_at = datetime('now', 'localtime')
                   WHERE id = ?""",
                (status, video_url, error, cost, currency, task_id),
            )
        else:
            await db.execute(
                "UPDATE video_tasks SET status = ? WHERE id = ?",
                (status, task_id),
            )
        await db.commit()
    finally:
        await db.close()


async def get_user_active_tasks(user_id: int) -> list[dict]:
    """获取用户未完成的视频任务（pending / processing），用于切页面后恢复轮询"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM video_tasks WHERE user_id = ? AND status IN ('pending', 'processing') ORDER BY created_at DESC",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
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
