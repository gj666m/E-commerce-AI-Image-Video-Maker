# SQLite 数据库初始化与连接管理
import aiosqlite
import logging
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "app.db"

# 建表 SQL
_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS model_library (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    params TEXT NOT NULL DEFAULT '{}',
    file TEXT NOT NULL,
    thumbnail TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS video_tasks (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    external_id TEXT,
    provider_name TEXT NOT NULL,
    prompt TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    resolution TEXT,
    video_url TEXT,
    error TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    completed_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_model_library_user ON model_library(user_id);
CREATE INDEX IF NOT EXISTS idx_video_tasks_user ON video_tasks(user_id);
"""


async def get_db() -> aiosqlite.Connection:
    """获取数据库连接（WAL 模式 + 外键约束）"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db():
    """初始化数据库（建表 + 默认管理员）"""
    db = await get_db()
    try:
        await db.executescript(_CREATE_TABLES)
        await db.commit()

        # 检查是否已有管理员
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        row = await cursor.fetchone()
        if row[0] == 0:
            from app.auth import hash_password
            await db.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'admin')",
                ("admin", hash_password("admin123")),
            )
            await db.commit()
            logger.info("默认管理员已创建: admin / admin123")
    finally:
        await db.close()
