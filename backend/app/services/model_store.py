# 模特库存储服务 - SQLite + 文件管理
import json
import logging
import time
from pathlib import Path

from PIL import Image
import io

from app.config import settings
from app.database import get_db

logger = logging.getLogger(__name__)

# 模特库根目录
MODELS_DIR = Path(settings.model_store_dir).resolve()
THUMB_SIZE = 256


def _user_dir(user_id: int) -> Path:
    """获取用户的模特库目录"""
    d = MODELS_DIR / str(user_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_path(user_id: int, filename: str) -> Path:
    """安全拼接路径，防止路径遍历攻击"""
    safe_name = Path(filename).name
    user_d = _user_dir(user_id)
    full_path = (user_d / safe_name).resolve()
    if not full_path.is_relative_to(user_d):
        raise ValueError(f"非法路径: {filename}")
    return full_path


def _create_thumbnail(image_bytes: bytes) -> bytes:
    """创建缩略图"""
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    w, h = img.size
    ratio = THUMB_SIZE / max(w, h)
    new_w, new_h = int(w * ratio), int(h * ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()


def _generate_id() -> str:
    return f"model_{int(time.time() * 1000)}"


async def save_model(user_id: int, name: str, params: dict, image_bytes: bytes) -> dict:
    """保存模特到库"""
    model_id = _generate_id()
    user_d = _user_dir(user_id)

    # 保存原图
    img_path = user_d / f"{model_id}.jpeg"
    img_path.write_bytes(image_bytes)

    # 保存缩略图
    thumb_bytes = _create_thumbnail(image_bytes)
    thumb_path = user_d / f"{model_id}_thumb.jpeg"
    thumb_path.write_bytes(thumb_bytes)

    # 写入数据库
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO model_library (id, user_id, name, params, file, thumbnail) VALUES (?, ?, ?, ?, ?, ?)",
            (model_id, user_id, name, json.dumps(params, ensure_ascii=False), f"{model_id}.jpeg", f"{model_id}_thumb.jpeg"),
        )
        await db.commit()
    finally:
        await db.close()

    logger.info(f"模特已保存: {model_id} - {name} (user={user_id})")
    return {
        "id": model_id,
        "name": name,
        "params": params,
        "file": f"{model_id}.jpeg",
        "thumbnail": f"{model_id}_thumb.jpeg",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


async def list_models(user_id: int) -> list[dict]:
    """获取用户的模特库列表"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, name, params, file, thumbnail, created_at FROM model_library WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "params": json.loads(r["params"]),
                "file": f"{user_id}/{r['file']}",
                "thumbnail": f"{user_id}/{r['thumbnail']}",
                "created_at": r["created_at"],
            }
            for r in rows
        ]
    finally:
        await db.close()


async def list_all_models() -> list[dict]:
    """管理员获取所有用户的模特库"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT m.id, m.name, m.params, m.file, m.thumbnail, m.created_at, m.user_id, u.username FROM model_library m JOIN users u ON m.user_id = u.id ORDER BY m.created_at DESC"
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "params": json.loads(r["params"]),
                "file": f"{r['user_id']}/{r['file']}",
                "thumbnail": f"{r['user_id']}/{r['thumbnail']}",
                "created_at": r["created_at"],
                "user_id": r["user_id"],
                "username": r["username"],
            }
            for r in rows
        ]
    finally:
        await db.close()


async def delete_model(user_id: int, model_id: str) -> bool:
    """删除模特"""
    db = await get_db()
    try:
        # 查找模特记录
        cursor = await db.execute(
            "SELECT file, thumbnail FROM model_library WHERE id = ? AND user_id = ?",
            (model_id, user_id),
        )
        row = await cursor.fetchone()
        if not row:
            return False

        # 删除文件
        for key in ("file", "thumbnail"):
            try:
                fpath = _safe_path(user_id, row[key])
                if fpath.exists():
                    fpath.unlink()
            except ValueError:
                logger.warning(f"跳过非法路径: {row[key]}")

        # 删除数据库记录
        await db.execute("DELETE FROM model_library WHERE id = ?", (model_id,))
        await db.commit()
        logger.info(f"模特已删除: {model_id} (user={user_id})")
        return True
    finally:
        await db.close()


def delete_user_models(user_id: int):
    """删除用户的所有模特文件（删除用户时调用）"""
    user_d = _user_dir(user_id)
    if user_d.exists():
        import shutil
        shutil.rmtree(user_d, ignore_errors=True)
        logger.info(f"已清理用户 {user_id} 的模特库文件")
