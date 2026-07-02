# 视频首帧抽取（素材资产库静态缩略图）
# 用 ffmpeg -ss 0 -frames:v 1 直接抽第一帧，不受场景过滤影响。
# 沉淀视频素材时调用，生成 jpg 落盘永久保留。
import asyncio
import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_JPEG_QUALITY = 3  # ffmpeg -qscale:v，2=高，3=中高（素材缩略图够用）


def _check_ffmpeg() -> str:
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise RuntimeError("服务器未安装 ffmpeg")
    return ffmpeg_path


def _extract_first_frame_sync(video_path: Path, output_jpg: Path) -> bool:
    """同步抽首帧到 output_jpg，成功返 True。

    用 -ss 0 -frames:v 1：跳到第 0 秒、只输出一帧。
    加 -an 忽略音频流，避免某些视频音频解码错误导致整体失败。
    """
    ffmpeg_path = _check_ffmpeg()
    output_jpg.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg_path,
        "-ss", "0",
        "-i", str(video_path),
        "-frames:v", "1",
        "-an",
        "-qscale:v", str(_DEFAULT_JPEG_QUALITY),
        "-y",
        str(output_jpg),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=15)
        if result.returncode != 0:
            err_tail = result.stderr.decode("utf-8", errors="ignore")[-300:]
            logger.warning(f"ffmpeg 抽首帧失败 {video_path}: {err_tail}")
            return False
        return output_jpg.is_file() and output_jpg.stat().st_size > 0
    except subprocess.TimeoutExpired:
        logger.warning(f"ffmpeg 抽首帧超时 {video_path}")
        return False
    except Exception as e:
        logger.warning(f"ffmpeg 抽首帧异常 {video_path}: {e}")
        return False


async def extract_first_frame(video_path: Path, output_jpg: Path) -> bool:
    """异步抽首帧。成功返 True，失败返 False（不抛异常，调用方静默降级）。"""
    try:
        return await asyncio.to_thread(_extract_first_frame_sync, video_path, output_jpg)
    except Exception as e:
        logger.warning(f"抽首帧异常 {video_path}: {e}")
        return False
