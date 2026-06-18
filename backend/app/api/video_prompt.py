# 视频提示词反推接口
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.deps import get_current_user
from app.providers.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["video-prompt"])

# API易 Gemini 视频理解硬限制：整个请求体 ≤ 20MB
# 留 5MB buffer 给 base64 膨胀（×1.33）+ system prompt + 其他字段
# 实际：15MB 视频 → base64 后 ~20MB，临界值
MAX_VIDEO_SIZE = 15 * 1024 * 1024  # 15MB

# 全局单例
_gemini = GeminiProvider()


@router.post("/video-to-prompt")
async def video_to_prompt(
    current_user=Depends(get_current_user),
    video: UploadFile = File(..., description="视频文件（mp4/mov/webm，≤15MB）"),
    style: str = Form("sora_structured", description="输出风格：sora_structured（目前仅支持此选项）"),
    extra_prompt: str | None = Form(None, description="用户额外要求（可选）"),
):
    """视频 → 结构化分镜 prompt（提示词反推）

    流程：上传视频 → 校验大小/MIME → base64 内联传 Gemini → 返回 Sora 结构化分镜 prompt

    利用 API易中转 Gemini 3.5 Flash 的视频理解能力（1 FPS 采样 + 音频理解）。
    """
    # 1. 校验 MIME
    mime_type = video.content_type or ""
    if not mime_type.startswith("video/"):
        raise HTTPException(400, f"仅支持视频文件，收到 {mime_type or '未知类型'}")

    # 2. 校验大小
    raw = await video.read()
    size_mb = len(raw) / 1024 / 1024
    if len(raw) > MAX_VIDEO_SIZE:
        raise HTTPException(
            400,
            f"视频大小 {size_mb:.1f}MB 超过 15MB 限制，请压缩或截短后重试",
        )

    # 3. 兜底 mime_type（部分浏览器上传 mov 时可能 content_type 缺失）
    if not mime_type:
        # 按扩展名兜底
        ext = (video.filename or "").lower().rsplit(".", 1)[-1] if video.filename else ""
        mime_map = {"mp4": "video/mp4", "mov": "video/quicktime", "webm": "video/webm", "mkv": "video/x-matroska"}
        mime_type = mime_map.get(ext, "video/mp4")

    logger.info(
        f"视频提示词反推请求: user={current_user['username']}, "
        f"file={video.filename}, size={size_mb:.2f}MB, mime={mime_type}"
    )

    # 4. 调 Gemini
    try:
        prompt = await _gemini.reverse_video_prompt(
            video_bytes=raw,
            mime_type=mime_type,
            style=style,
            extra_prompt=extra_prompt or "",
        )
    except RuntimeError as e:
        logger.error(f"视频提示词反推失败: {e}")
        raise HTTPException(500, str(e))

    return {
        "success": True,
        "prompt": prompt,
        "model_used": "gemini-3.5-flash",
        "video_size": len(raw),
        "video_mime": mime_type,
    }
