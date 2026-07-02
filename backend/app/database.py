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
    display_name TEXT,                          -- 真实使用人名（便于运营跟进）
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
    balance_before INTEGER,  -- 提交任务前的 API易 quota 快照（用于真实扣费计算）
    cost REAL,                -- 真实扣费（首次完成时计算并持久化）
    currency TEXT,            -- 费用币种（$ 或 ¥）
    file_expired BOOLEAN NOT NULL DEFAULT 0,      -- 文件已过期（磁盘已删，元数据保留）
    user_deleted BOOLEAN NOT NULL DEFAULT 0,      -- 用户软删标记（admin 仍可见）
    user_deleted_at TEXT,                          -- 用户软删时间
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    completed_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS generation_history (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    task_type TEXT NOT NULL,
    prompt TEXT NOT NULL DEFAULT '',
    params TEXT NOT NULL DEFAULT '{}',
    model_used TEXT NOT NULL DEFAULT '',
    file TEXT NOT NULL,
    thumbnail TEXT NOT NULL,
    cost REAL NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT '¥',
    file_expired BOOLEAN NOT NULL DEFAULT 0,
    user_deleted BOOLEAN NOT NULL DEFAULT 0,      -- 用户软删标记（admin 仍可见）
    user_deleted_at TEXT,                          -- 用户软删时间
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS prompt_library (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    task_type TEXT NOT NULL,                       -- quick/outfit/model_gen/seed_grass/product_main/aplus/video/video_shots
    title TEXT NOT NULL,
    description TEXT,                              -- 用户原始描述（可空）
    full_prompt TEXT NOT NULL,                     -- 完整 prompt（含比例/风格等元数据，实际发给模型的）
    model_used TEXT,                               -- 模型名
    aspect_ratio TEXT,                             -- 比例
    sample_image TEXT,                             -- 效果图缩略图相对路径（如 user_id/xxx_thumb.jpeg）
    sample_kind TEXT DEFAULT 'image',              -- 'image' 或 'video'
    tags TEXT NOT NULL DEFAULT '[]',               -- JSON 数组
    elements TEXT,                                 -- 工坊结构化要素 JSON（图片类 8 要素，续18）
    is_shared BOOLEAN NOT NULL DEFAULT 0,          -- 是否共享给全员
    use_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS asset_library (
    id TEXT PRIMARY KEY,                     -- al_xxxxxxxx
    user_id INTEGER NOT NULL,
    source_type TEXT NOT NULL,               -- 'image' / 'video'（关联 generation_history / video_tasks）
    source_id TEXT NOT NULL,                 -- 关联源表 id
    title TEXT NOT NULL,
    description TEXT,
    tags TEXT NOT NULL DEFAULT '[]',         -- JSON 数组，自定义标签
    thumbnail_path TEXT,                     -- 视频类沉淀时抽的首帧 jpg 相对路径（{user_id}/{asset_id}.jpg）
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS asset_applications (
    id TEXT PRIMARY KEY,                     -- aa_xxxxxxxx
    asset_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,                -- 冗余便于权限过滤
    shop_name TEXT NOT NULL,                 -- 自由填（亚马逊 / TikTok 店铺名）
    applied_url TEXT,                        -- listing / 视频链接
    applied_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (asset_id) REFERENCES asset_library(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS asset_tracking_records (
    id TEXT PRIMARY KEY,                     -- tr_xxxxxxxx
    application_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    views INTEGER,                           -- 预设通用：播放量
    clicks INTEGER,                          -- 点击
    conversions INTEGER,                     -- 转化数
    gmv REAL,                                -- 销售额
    extra_metrics TEXT NOT NULL DEFAULT '[]', -- JSON 数组，自定义指标 [{name,value}]
    notes TEXT,
    recorded_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),  -- 数据归属时间
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),   -- 录入时间
    FOREIGN KEY (application_id) REFERENCES asset_applications(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_model_library_user ON model_library(user_id);
CREATE INDEX IF NOT EXISTS idx_video_tasks_user ON video_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_generation_history_user ON generation_history(user_id);
CREATE INDEX IF NOT EXISTS idx_generation_history_created ON generation_history(created_at);
CREATE INDEX IF NOT EXISTS idx_prompt_library_user ON prompt_library(user_id);
CREATE INDEX IF NOT EXISTS idx_prompt_library_task_type ON prompt_library(task_type);
CREATE INDEX IF NOT EXISTS idx_asset_library_user ON asset_library(user_id);
CREATE INDEX IF NOT EXISTS idx_asset_library_source ON asset_library(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_asset_app_asset ON asset_applications(asset_id);
CREATE INDEX IF NOT EXISTS idx_asset_app_user ON asset_applications(user_id);
CREATE INDEX IF NOT EXISTS idx_asset_app_shop ON asset_applications(shop_name);
CREATE INDEX IF NOT EXISTS idx_tracking_app ON asset_tracking_records(application_id);
CREATE INDEX IF NOT EXISTS idx_tracking_recorded ON asset_tracking_records(recorded_at);
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

        # 兼容迁移：generation_history 旧表无 file_expired 列时补上
        cursor = await db.execute("PRAGMA table_info(generation_history)")
        columns = {row[1] for row in await cursor.fetchall()}
        if "file_expired" not in columns:
            await db.execute(
                "ALTER TABLE generation_history ADD COLUMN file_expired BOOLEAN NOT NULL DEFAULT 0"
            )
            await db.commit()
            logger.info("已为 generation_history 添加 file_expired 列")
        if "user_deleted" not in columns:
            await db.execute(
                "ALTER TABLE generation_history ADD COLUMN user_deleted BOOLEAN NOT NULL DEFAULT 0"
            )
            await db.commit()
            logger.info("已为 generation_history 添加 user_deleted 列")
        if "user_deleted_at" not in columns:
            await db.execute(
                "ALTER TABLE generation_history ADD COLUMN user_deleted_at TEXT"
            )
            await db.commit()
            logger.info("已为 generation_history 添加 user_deleted_at 列")

        # 兼容迁移：video_tasks 旧表无 balance_before 列时补上
        cursor = await db.execute("PRAGMA table_info(video_tasks)")
        columns = {row[1] for row in await cursor.fetchall()}
        if "balance_before" not in columns:
            await db.execute(
                "ALTER TABLE video_tasks ADD COLUMN balance_before INTEGER"
            )
            await db.commit()
            logger.info("已为 video_tasks 添加 balance_before 列")
        if "cost" not in columns:
            await db.execute("ALTER TABLE video_tasks ADD COLUMN cost REAL")
            await db.commit()
            logger.info("已为 video_tasks 添加 cost 列")
        if "currency" not in columns:
            await db.execute("ALTER TABLE video_tasks ADD COLUMN currency TEXT")
            await db.commit()
            logger.info("已为 video_tasks 添加 currency 列")
        if "file_expired" not in columns:
            await db.execute(
                "ALTER TABLE video_tasks ADD COLUMN file_expired BOOLEAN NOT NULL DEFAULT 0"
            )
            await db.commit()
            logger.info("已为 video_tasks 添加 file_expired 列")
        if "user_deleted" not in columns:
            await db.execute(
                "ALTER TABLE video_tasks ADD COLUMN user_deleted BOOLEAN NOT NULL DEFAULT 0"
            )
            await db.commit()
            logger.info("已为 video_tasks 添加 user_deleted 列")
        if "user_deleted_at" not in columns:
            await db.execute("ALTER TABLE video_tasks ADD COLUMN user_deleted_at TEXT")
            await db.commit()
            logger.info("已为 video_tasks 添加 user_deleted_at 列")

        # 兼容迁移：prompt_library 旧表无 elements 列时补上（续18 工坊双向恢复要素）
        cursor = await db.execute("PRAGMA table_info(prompt_library)")
        columns = {row[1] for row in await cursor.fetchall()}
        if "elements" not in columns:
            await db.execute("ALTER TABLE prompt_library ADD COLUMN elements TEXT")
            await db.commit()
            logger.info("已为 prompt_library 添加 elements 列")

        # 兼容迁移：users 旧表无 display_name 列时补上
        cursor = await db.execute("PRAGMA table_info(users)")
        columns = {row[1] for row in await cursor.fetchall()}
        if "display_name" not in columns:
            await db.execute("ALTER TABLE users ADD COLUMN display_name TEXT")
            await db.commit()
            logger.info("已为 users 添加 display_name 列")

        # 兼容迁移：asset_library 旧表无 thumbnail_path 列时补上（视频素材静态首帧）
        cursor = await db.execute("PRAGMA table_info(asset_library)")
        columns = {row[1] for row in await cursor.fetchall()}
        if "thumbnail_path" not in columns:
            await db.execute("ALTER TABLE asset_library ADD COLUMN thumbnail_path TEXT")
            await db.commit()
            logger.info("已为 asset_library 添加 thumbnail_path 列")

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
