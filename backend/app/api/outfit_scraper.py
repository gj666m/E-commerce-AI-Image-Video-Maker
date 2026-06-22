# 穿搭素材抓取接口
"""单条 TikTok/短视频链接 → 下载 → ffmpeg 抽帧 → 返回关键帧 base64

设计：单条接口，前端串行循环调用（同 tiktok_script 模式）
- 简单、实时、可中断、不触发反爬批量检测
- 失败不抛 HTTP，返回 success=False 让前端继续后续链接
- 关键帧用于运营选穿搭参考图（生视频用）
"""
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.deps import get_current_user
from app.services.tiktok_downloader import download_tiktok
from app.services.video_frame_extractor import extract_key_frames_b64

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/outfit-scrape", tags=["outfit-scrape"])


@router.post("/extract")
async def extract_outfit(
    current_user=Depends(get_current_user),
    url: str = Form(..., description="TikTok / Instagram / YouTube / 抖音 视频链接"),
    max_frames: int = Form(8, description="最多返回的帧数（默认 8）"),
):
    """单条链接 → 关键帧列表

    流程：
    1. yt-dlp 下载视频（≤30MB，含平台白名单校验）
    2. ffmpeg 抽取场景变化关键帧（每 1 秒最多 1 帧，上限 8 张）
    3. 返回 {success, url, frames: [data_url], error?}

    失败时 success=False + error 字段（不抛 HTTP 错误，让前端可以继续处理其他链接）
    """
    url = url.strip()
    if not url:
        raise HTTPException(400, "链接不能为空")

    logger.info(f"穿搭素材抓取 user={current_user['username']}, url={url[:80]}")

    # === 1. 下载视频 ===
    try:
        raw, mime = await download_tiktok(url, max_size_mb=30)
    except RuntimeError as e:
        logger.warning(f"视频下载失败 url={url[:80]}: {e}")
        return {
            "success": False,
            "url": url,
            "error": str(e),
            "frames": [],
        }

    size_mb = len(raw) / 1024 / 1024

    # === 2. ffmpeg 抽帧 ===
    try:
        frames_b64 = await extract_key_frames_b64(raw, max_frames=max_frames)
    except RuntimeError as e:
        logger.error(f"抽帧失败 url={url[:80]}: {e}")
        return {
            "success": False,
            "url": url,
            "error": f"抽帧失败: {e}",
            "frames": [],
        }

    if not frames_b64:
        # 兜底：场景过滤太严导致 0 帧，重新用简单抽帧（fps=0.5）
        try:
            frames_b64 = await extract_key_frames_b64(
                raw, max_frames=max_frames, scene_threshold=0.0, fps=0.5
            )
        except RuntimeError:
            pass

    logger.info(
        f"穿搭素材抓取完成 user={current_user['username']}, "
        f"size={size_mb:.2f}MB, frames={len(frames_b64)}"
    )

    return {
        "success": True,
        "url": url,
        "frames": frames_b64,
        "error": None,
        "video_size": len(raw),
    }


@router.post("/extract-upload")
async def extract_outfit_upload(
    current_user=Depends(get_current_user),
    video: UploadFile = File(..., description="视频文件（mp4/mov 等，≤30MB）"),
    max_frames: int = Form(8, description="最多返回的帧数（默认 8）"),
):
    """上传视频文件 → 关键帧列表

    跳过 yt-dlp 下载步骤，直接 ffmpeg 抽帧。适合：
    - 用户本地已有视频素材（抖音/小红书下载的）
    - TikTok 链接被风控时手动下载后上传
    """
    logger.info(
        f"穿搭素材上传抓取 user={current_user['username']}, "
        f"filename={video.filename}, content_type={video.content_type}"
    )

    # === 1. 校验 + 读文件 ===
    # 不强制 content_type 校验：部分浏览器/格式会上传 application/octet-stream
    # 让 ffmpeg 自己判断内容合法性（失败会抛 RuntimeError）
    raw = await video.read()
    if not raw:
        raise HTTPException(400, "视频内容为空")
    if len(raw) > 30 * 1024 * 1024:
        raise HTTPException(400, "视频过大（>30MB），请压缩后再传")

    size_mb = len(raw) / 1024 / 1024
    source_label = video.filename or "uploaded_video"

    # === 2. ffmpeg 抽帧 ===
    try:
        frames_b64 = await extract_key_frames_b64(raw, max_frames=max_frames)
    except RuntimeError as e:
        logger.error(f"上传视频抽帧失败 file={source_label}: {e}")
        return {
            "success": False,
            "url": source_label,
            "error": f"抽帧失败: {e}",
            "frames": [],
        }

    # 0 帧兜底：场景过滤太严，重试简单抽帧
    if not frames_b64:
        try:
            frames_b64 = await extract_key_frames_b64(
                raw, max_frames=max_frames, scene_threshold=0.0, fps=0.5
            )
        except RuntimeError:
            pass

    logger.info(
        f"穿搭素材上传抓取完成 user={current_user['username']}, "
        f"size={size_mb:.2f}MB, frames={len(frames_b64)}"
    )

    return {
        "success": True,
        "url": source_label,
        "frames": frames_b64,
        "error": None,
        "video_size": len(raw),
    }
