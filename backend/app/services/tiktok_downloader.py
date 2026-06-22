# TikTok / 短视频链接下载工具
"""用 yt-dlp 下载 TikTok 等短视频平台视频，返回 bytes + MIME。

设计要点：
- yt-dlp 是纯 Python，无二进制依赖，自带 TikTok 解析逻辑
- 服务器 IP 可能被 TikTok 风控，失败时抛 RuntimeError，调用方降级到「请手动上传文件」
- 异步包装（yt-dlp 本身是同步，用 asyncio.to_thread 包一层）
- 限制最大体积，避免下载到长视频撑爆内存
"""
import asyncio
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# 允许的平台域名白名单（防止用户用 file:// 或内网 URL 滥用）
_ALLOWED_HOSTS = (
    "tiktok.com",
    "www.tiktok.com",
    "vm.tiktok.com",
    "douyin.com",
    "www.douyin.com",
    "instagram.com",
    "www.instagram.com",
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
)


def _looks_allowed(url: str) -> bool:
    lowered = url.lower().strip()
    if not lowered.startswith(("http://", "https://")):
        return False
    # 粗略匹配域名
    try:
        host = lowered.split("//", 1)[1].split("/", 1)[0].split(":", 1)[0]
    except IndexError:
        return False
    return any(host == h or host.endswith("." + h) for h in _ALLOWED_HOSTS)


def _download_sync(url: str, tmp_dir: str, max_size_mb: int) -> tuple[str, str]:
    """同步下载逻辑（在 to_thread 里跑），返回 (saved_path, ext)"""
    import yt_dlp

    max_bytes = max_size_mb * 1024 * 1024

    # yt-dlp 选项：限大小、取 mp4 优先、不下载字幕/封面
    ydl_opts = {
        # 优先 mp4，回退到 best
        "format": "best[ext=mp4]/best",
        "outtmpl": os.path.join(tmp_dir, "%(id)s.%(ext)s"),
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "skip_download": False,
        "max_filesize": max_bytes,
        # 不下字幕、不写 json、不下缩略图
        "writesubtitles": False,
        "writeautomaticsub": False,
        "writeinfojson": False,
        "writethumbnail": False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # 拿实际下载的文件路径
        if "requested_downloads" in info and info["requested_downloads"]:
            filepath = info["requested_downloads"][0].get("filepath")
            ext = info["requested_downloads"][0].get("ext", "mp4")
        else:
            # 兜底：用 prepare_filename 推断
            filepath = ydl.prepare_filename(info)
            ext = info.get("ext", "mp4")

        if not filepath or not os.path.exists(filepath):
            raise RuntimeError("yt-dlp 未产出文件，可能被平台风控")

        actual_size = os.path.getsize(filepath)
        if actual_size > max_bytes:
            os.remove(filepath)
            raise RuntimeError(
                f"视频过大（{actual_size / 1024 / 1024:.1f}MB > {max_size_mb}MB），请手动下载后上传"
            )

        return filepath, ext or "mp4"


def _mime_from_ext(ext: str) -> str:
    """扩展名 → MIME 兜底"""
    return {
        "mp4": "video/mp4",
        "mov": "video/quicktime",
        "webm": "video/webm",
        "mkv": "video/x-matroska",
        "m4v": "video/x-m4v",
    }.get(ext.lower().lstrip("."), "video/mp4")


async def download_tiktok(url: str, max_size_mb: int = 30) -> tuple[bytes, str]:
    """下载 TikTok / 短视频平台的视频

    Args:
        url: TikTok / Instagram / YouTube 短视频链接
        max_size_mb: 最大允许体积（MB），超出抛错

    Returns:
        (video_bytes, mime_type)

    Raises:
        RuntimeError: 下载失败 / 超时 / 超大 / 平台风控
    """
    if not _looks_allowed(url):
        raise RuntimeError(
            "仅支持 TikTok / Instagram / YouTube / 抖音 等主流短视频平台的链接"
        )

    # 用临时目录隔离，下载完读 bytes 再删
    with tempfile.TemporaryDirectory(prefix="tiktok_dl_") as tmp_dir:
        try:
            # yt-dlp 同步接口，包到线程
            filepath, ext = await asyncio.wait_for(
                asyncio.to_thread(_download_sync, url, tmp_dir, max_size_mb),
                timeout=60,  # 60s 下载超时
            )
        except asyncio.TimeoutError:
            raise RuntimeError("视频下载超时（>60s），请手动下载后上传文件")
        except Exception as e:
            # yt-dlp 抛的各种 DownloadError / ExtractError 都裹一层
            msg = str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__
            logger.warning(f"yt-dlp 下载失败: {type(e).__name__}: {msg}")
            raise RuntimeError(
                f"视频链接解析失败（{msg}），可能被平台风控，请手动下载后上传文件"
            )

        # 读 bytes
        try:
            data = Path(filepath).read_bytes()
        finally:
            try:
                os.remove(filepath)
            except OSError:
                pass

        mime = _mime_from_ext(ext)
        logger.info(f"TikTok 下载成功: {url} → {len(data)} bytes, mime={mime}")
        return data, mime
