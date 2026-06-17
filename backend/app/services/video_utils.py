# 临时视频文件管理 - 存储、URL 生成、路径反推
from pathlib import Path

from app.config import settings


def get_temp_dir() -> Path:
    """获取临时视频目录，不存在则创建"""
    temp_dir = Path(settings.video_temp_dir).resolve()
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def save_video(user_id: int, task_id: str, data: bytes, ext: str = "mp4") -> str:
    """保存视频到用户子目录

    Args:
        user_id: 用户 ID（用于按用户隔离文件）
        task_id: 任务 ID
        data: 视频二进制
        ext: 文件扩展名

    Returns:
        相对路径（含 user_id 前缀），如 "3/abc123.mp4"
    """
    user_dir = get_temp_dir() / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    rel_path = f"{user_id}/{task_id}.{ext}"
    filepath = get_temp_dir() / rel_path
    filepath.write_bytes(data)
    return rel_path


def make_video_url(rel_path: str) -> str:
    """生成视频访问 URL

    Args:
        rel_path: 相对路径（含 user_id 前缀，或旧任务的纯 filename）

    Returns:
        访问 URL，如 /video-files/3/abc123.mp4
    """
    return f"/video-files/{rel_path}"


def get_video_abs_path(video_url: str) -> Path | None:
    """从 video_url 反推磁盘绝对路径，用于删除/清理

    Args:
        video_url: DB 中存储的 URL，如 /video-files/3/abc123.mp4

    Returns:
        校验通过的绝对路径；不通过（越权/空）返回 None
    """
    if not video_url:
        return None
    prefix = "/video-files/"
    if not video_url.startswith(prefix):
        return None
    rel_path = video_url[len(prefix):]
    temp_dir = get_temp_dir()
    abs_path = (temp_dir / rel_path).resolve()
    # 安全校验：必须在 temp_dir 下，防止 ../ 越权
    if not abs_path.is_relative_to(temp_dir):
        return None
    return abs_path
