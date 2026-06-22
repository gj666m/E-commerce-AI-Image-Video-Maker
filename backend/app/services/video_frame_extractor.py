# 视频抽帧服务
"""用 ffmpeg 从视频 bytes 抽取关键帧，返回 JPEG bytes 列表。

设计要点：
- 依赖系统 ffmpeg 二进制（Mac: brew install ffmpeg；Ubuntu: apt install ffmpeg）
- 用 select=gt(scene,0.3) 过滤场景变化明显的帧，避免连续相似帧
- 异步包装 subprocess（同步调用包到 asyncio.to_thread）
- 限制总帧数（默认 8 张）+ 每帧大小，防内存爆炸
- 失败统一抛 RuntimeError，调用方决定降级策略
"""
import asyncio
import base64
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# 默认配置
_DEFAULT_MAX_FRAMES = 8
_DEFAULT_SCENE_THRESHOLD = 0.3  # 场景变化阈值（0-1，越小越敏感）
_DEFAULT_FPS = 1.0  # 每秒抽 1 帧
_DEFAULT_JPEG_QUALITY = 2  # ffmpeg -qscale:v，2 = 高质量


def _check_ffmpeg() -> str:
    """检查 ffmpeg 是否可用，返回可执行路径"""
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise RuntimeError(
            "服务器未安装 ffmpeg。Ubuntu: sudo apt install ffmpeg；Mac: brew install ffmpeg"
        )
    return ffmpeg_path


def _extract_sync(
    video_path: str,
    output_dir: str,
    fps: float,
    scene_threshold: float,
    max_frames: int,
) -> list[str]:
    """同步抽帧逻辑（在 to_thread 里跑），返回输出文件路径列表"""
    ffmpeg_path = _check_ffmpeg()

    # 输出模板：frame_001.jpg
    output_pattern = os.path.join(output_dir, "frame_%03d.jpg")

    # ffmpeg 命令：
    # -vf "select=gt(scene\\,T),fps=F" -vsync vfr → 按场景变化过滤 + 限帧率
    # -qscale:v Q → JPEG 质量（2=高，10=低）
    # -frames:v N → 最多输出 N 帧
    filter_arg = f"select='gt(scene\\,{scene_threshold})',fps={fps}"

    cmd = [
        ffmpeg_path,
        "-i", video_path,
        "-vf", filter_arg,
        "-frames:v", str(max_frames),
        "-qscale:v", str(_DEFAULT_JPEG_QUALITY),
        "-y",  # 覆盖输出
        output_pattern,
    ]

    try:
        # stderr 重定向捕获（ffmpeg 日志在 stderr）
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=30,  # 30s 超时
        )
        if result.returncode != 0:
            err_tail = result.stderr.decode("utf-8", errors="ignore")[-500:]
            raise RuntimeError(f"ffmpeg 抽帧失败：{err_tail}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("ffmpeg 抽帧超时（>30s），视频可能过大或损坏")

    # 收集输出文件（按文件名排序）
    frames = sorted(Path(output_dir).glob("frame_*.jpg"))
    return [str(p) for p in frames]


async def extract_key_frames(
    video_bytes: bytes,
    max_frames: int = _DEFAULT_MAX_FRAMES,
    scene_threshold: float = _DEFAULT_SCENE_THRESHOLD,
    fps: float = _DEFAULT_FPS,
) -> list[bytes]:
    """从视频 bytes 抽取关键帧

    Args:
        video_bytes: 视频二进制
        max_frames: 最多返回的帧数
        scene_threshold: 场景变化阈值（0-1，越小越敏感，默认 0.3）
        fps: 抽帧率（每秒多少帧，默认 1.0）

    Returns:
        JPEG bytes 列表（已按时序排序）

    Raises:
        RuntimeError: ffmpeg 不可用 / 抽帧失败 / 超时
    """
    if not video_bytes:
        raise RuntimeError("视频内容为空")

    # 用临时目录隔离：存原视频 + 抽帧输出
    with tempfile.TemporaryDirectory(prefix="frame_extract_") as tmp_dir:
        # 先把 video bytes 写到临时文件（ffmpeg 需要可 seek 的输入）
        video_path = os.path.join(tmp_dir, "input.mp4")
        Path(video_path).write_bytes(video_bytes)

        output_dir = os.path.join(tmp_dir, "frames")
        os.makedirs(output_dir, exist_ok=True)

        try:
            frame_paths = await asyncio.to_thread(
                _extract_sync,
                video_path,
                output_dir,
                fps,
                scene_threshold,
                max_frames,
            )
        except Exception as e:
            msg = str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__
            logger.warning(f"抽帧失败: {type(e).__name__}: {msg}")
            raise RuntimeError(f"视频抽帧失败：{msg}")

        # 读所有帧 bytes
        frames: list[bytes] = []
        for fp in frame_paths:
            try:
                frames.append(Path(fp).read_bytes())
            except OSError:
                continue

        logger.info(f"抽帧完成: {len(frames)} 张关键帧")
        return frames


async def extract_key_frames_b64(
    video_bytes: bytes,
    max_frames: int = _DEFAULT_MAX_FRAMES,
    scene_threshold: float = _DEFAULT_SCENE_THRESHOLD,
    fps: float = _DEFAULT_FPS,
) -> list[str]:
    """从视频抽取关键帧，返回 base64 编码的 data URL 列表（前端可直接用）

    Returns:
        ["data:image/jpeg;base64,...", ...]
    """
    frames = await extract_key_frames(
        video_bytes, max_frames=max_frames,
        scene_threshold=scene_threshold, fps=fps,
    )
    return [
        f"data:image/jpeg;base64,{base64.b64encode(f).decode('ascii')}"
        for f in frames
    ]
