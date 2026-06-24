# AsyncSqliteSaver 单例 - LangGraph checkpoint 持久化（Phase 3）
# 独立 agent_checkpoints.db，与 app.db 隔离避免 WAL 锁竞争
import logging
from pathlib import Path

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.config import settings

logger = logging.getLogger(__name__)

_saver: AsyncSqliteSaver | None = None
_conn: aiosqlite.Connection | None = None


async def init_checkpointer() -> None:
    """应用启动时初始化 checkpoint saver（lifespan 调用一次）

    - 建库目录
    - 打开 aiosqlite 连接（开启 WAL 提升并发写）
    - saver.setup() 建表
    """
    global _saver, _conn
    if _saver is not None:
        return
    db_path = Path(settings.agent_checkpoint_db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    _conn = await aiosqlite.connect(str(db_path))
    # WAL 模式，降低多请求写checkpoint 时的锁竞争
    await _conn.execute("PRAGMA journal_mode=WAL")
    await _conn.commit()
    _saver = AsyncSqliteSaver(_conn)
    await _saver.setup()
    logger.info(f"Agent Checkpoint 初始化完成：db={db_path}")


async def close_checkpointer() -> None:
    """应用关闭时释放连接"""
    global _saver, _conn
    if _conn is not None:
        await _conn.close()
    _saver = None
    _conn = None


def get_checkpointer() -> AsyncSqliteSaver | None:
    """获取 checkpoint saver 单例（未初始化返回 None，graph 降级编译为无持久化）"""
    return _saver
