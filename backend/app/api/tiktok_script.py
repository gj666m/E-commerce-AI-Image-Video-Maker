# TikTok 脚本字幕提取接口
"""单条链接 → 下载视频 → Gemini 视频理解 → SRT 字幕

设计：单条接口，前端串行循环调用。
- 简单：不需要 SSE / WebSocket
- 实时：每条结果即时返回，前端可实时追加卡片
- 可取消：前端 AbortController 随时中断剩余链接
- 稳定：串行不触发 TikTok 反爬批量检测
"""
import logging

from fastapi import APIRouter, Depends, Form, HTTPException

from app.deps import get_current_user
from app.providers.gemini_provider import GeminiProvider
from app.services.tiktok_downloader import download_tiktok

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tiktok-script", tags=["tiktok-script"])

# 全局单例
_gemini = GeminiProvider()


@router.post("/extract")
async def extract_script(
    current_user=Depends(get_current_user),
    url: str = Form(..., description="TikTok / Instagram / YouTube / 抖音 视频链接"),
):
    """单条链接 → SRT 字幕

    流程：
    1. yt-dlp 下载视频（≤15MB，含平台白名单校验）
    2. Gemini 视频理解转写为 SRT 字幕
    3. 返回 {success, url, script, error?}

    失败时 success=False + error 字段（不抛 HTTP 错误，让前端可以继续处理其他链接）
    """
    url = url.strip()
    if not url:
        raise HTTPException(400, "链接不能为空")

    logger.info(f"TikTok 脚本提取 user={current_user['username']}, url={url[:80]}")

    # === 1. 下载视频 ===
    try:
        raw, mime = await download_tiktok(url, max_size_mb=15)
    except RuntimeError as e:
        logger.warning(f"视频下载失败 url={url[:80]}: {e}")
        return {
            "success": False,
            "url": url,
            "error": str(e),
            "script": None,
        }

    size_mb = len(raw) / 1024 / 1024

    # === 2. Gemini 转写 ===
    try:
        script = await _gemini.extract_video_script(raw, mime)
    except (RuntimeError, ValueError) as e:
        logger.error(f"字幕转写失败 url={url[:80]}: {e}")
        return {
            "success": False,
            "url": url,
            "error": f"字幕转写失败: {e}",
            "script": None,
        }

    logger.info(
        f"TikTok 脚本提取完成 user={current_user['username']}, "
        f"size={size_mb:.2f}MB, script_len={len(script)}"
    )

    return {
        "success": True,
        "url": url,
        "script": script,
        "error": None,
        "video_size": len(raw),
    }
