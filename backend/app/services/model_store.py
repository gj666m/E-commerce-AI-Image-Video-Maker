# 模特库存储服务 - 文件管理 + index.json 索引
import json
import logging
import time
from pathlib import Path

from PIL import Image
import io

from app.config import settings

logger = logging.getLogger(__name__)

# 模特库目录
MODELS_DIR = Path(settings.model_store_dir)
THUMB_SIZE = 256  # 缩略图长边像素


def _ensure_dir():
    """确保模特库目录存在"""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)


def _load_index() -> list[dict]:
    """加载模特索引"""
    index_path = MODELS_DIR / "index.json"
    if index_path.exists():
        return json.loads(index_path.read_text(encoding="utf-8"))
    return []


def _save_index(index: list[dict]):
    """保存模特索引"""
    index_path = MODELS_DIR / "index.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def _generate_id() -> str:
    """生成模特 ID"""
    return f"model_{int(time.time() * 1000)}"


def _create_thumbnail(image_bytes: bytes) -> bytes:
    """创建缩略图"""
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    # 等比缩放到缩略图尺寸
    w, h = img.size
    ratio = THUMB_SIZE / max(w, h)
    new_w, new_h = int(w * ratio), int(h * ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()


def save_model(name: str, params: dict, image_bytes: bytes) -> dict:
    """保存模特到库

    Args:
        name: 模特名称
        params: 生成参数
        image_bytes: 模特图二进制

    Returns:
        保存的模特信息
    """
    _ensure_dir()
    model_id = _generate_id()

    # 保存原图
    img_path = MODELS_DIR / f"{model_id}.jpeg"
    img_path.write_bytes(image_bytes)

    # 保存缩略图
    thumb_bytes = _create_thumbnail(image_bytes)
    thumb_path = MODELS_DIR / f"{model_id}_thumb.jpeg"
    thumb_path.write_bytes(thumb_bytes)

    # 更新索引
    record = {
        "id": model_id,
        "name": name,
        "params": params,
        "file": f"{model_id}.jpeg",
        "thumbnail": f"{model_id}_thumb.jpeg",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    index = _load_index()
    index.append(record)
    _save_index(index)

    logger.info(f"模特已保存: {model_id} - {name}")
    return record


def list_models() -> list[dict]:
    """获取模特库列表"""
    _ensure_dir()
    return _load_index()


def delete_model(model_id: str) -> bool:
    """删除模特

    Args:
        model_id: 模特 ID

    Returns:
        是否删除成功
    """
    index = _load_index()
    new_index = [m for m in index if m["id"] != model_id]

    if len(new_index) == len(index):
        return False  # 没找到

    # 删除文件
    for m in index:
        if m["id"] == model_id:
            for key in ("file", "thumbnail"):
                fpath = MODELS_DIR / m[key]
                if fpath.exists():
                    fpath.unlink()
            break

    _save_index(new_index)
    logger.info(f"模特已删除: {model_id}")
    return True
