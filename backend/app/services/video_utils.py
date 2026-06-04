# 临时视频文件管理 - 存储、URL 生成、过期清理
import time
import uuid
from pathlib import Path

from app.config import settings


def get_temp_dir() -> Path:
    """获取临时视频目录，不存在则创建"""
    temp_dir = Path(settings.video_temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def save_video(task_id: str, data: bytes, ext: str = "mp4") -> str:
    """保存视频到临时目录

    Args:
        task_id: 任务 ID
        data: 视频二进制
        ext: 文件扩展名

    Returns:
        文件名（不含路径）
    """
    temp_dir = get_temp_dir()
    filename = f"{task_id}.{ext}"
    filepath = temp_dir / filename
    filepath.write_bytes(data)
    return filename


def get_video_path(filename: str) -> Path | None:
    """获取视频文件路径

    Args:
        filename: 文件名

    Returns:
        文件完整路径，不存在返回 None
    """
    filepath = get_temp_dir() / filename
    if filepath.exists():
        return filepath
    return None


def make_video_url(filename: str) -> str:
    """生成视频访问 URL

    Args:
        filename: 文件名

    Returns:
        访问 URL，如 /video-files/abc123.mp4
    """
    return f"/video-files/{filename}"


def cleanup_expired() -> int:
    """清理过期的临时视频文件

    Returns:
        清理的文件数
    """
    temp_dir = get_temp_dir()
    if not temp_dir.exists():
        return 0

    now = time.time()
    expire_seconds = settings.video_expire_seconds
    count = 0

    for f in temp_dir.iterdir():
        if f.is_file():
            if now - f.stat().st_mtime > expire_seconds:
                f.unlink()
                count += 1

    return count
