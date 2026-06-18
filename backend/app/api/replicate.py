# 爆品复刻接口
"""爆品复刻：上传爆款视频 + 商品信息 → AI 抽取骨架 + 裂变 3 份新视频 prompt

3 步 AI 链路：
1. GeminiProvider.extract_viral_structure → 叙事骨架 dict
2. ProductAnalysisProvider.analyze → 商品理解（可选，失败不阻断）
3. GeminiProvider.generate_replicate_variations → 3 份 prompt 变体

用户选中后，调现有 /api/video/generate 生成视频。
"""
import json
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from typing import Optional

from app.deps import get_current_user
from app.providers.deepseek_provider import ProductAnalysisProvider
from app.providers.gemini_provider import GeminiProvider
from app.services.image_utils import compress_image
from app.services.tiktok_downloader import download_tiktok

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/replicate", tags=["replicate"])

# API易 Gemini 视频理解硬限制：≤15MB 视频（与 video_prompt.py 对齐）
MAX_VIDEO_SIZE = 15 * 1024 * 1024

# 全局单例
_gemini = GeminiProvider()
_provider = ProductAnalysisProvider()


def _guess_video_mime(filename: str | None, content_type: str | None) -> str:
    """根据 content_type + 文件扩展名兜底 mime"""
    if content_type and content_type.startswith("video/"):
        return content_type
    ext = (filename or "").lower().rsplit(".", 1)[-1] if filename else ""
    return {
        "mp4": "video/mp4",
        "mov": "video/quicktime",
        "webm": "video/webm",
        "mkv": "video/x-matroska",
        "m4v": "video/x-m4v",
    }.get(ext, "video/mp4")


@router.post("/analyze")
async def replicate_analyze(
    current_user=Depends(get_current_user),
    # 原视频：二选一
    video: Optional[UploadFile] = File(None, description="上传视频文件（mp4/mov/webm，≤15MB）"),
    video_url: Optional[str] = Form(None, description="TikTok / Instagram / YouTube 短视频链接"),
    # 商品
    product_images: list[UploadFile] = File(default=[], description="商品图 1-3 张（可选但推荐）"),
    product_info: Optional[str] = Form(None, description="商品信息（名称/卖点/受众/市场，自由文本）"),
    extra_prompt: Optional[str] = Form(None, description="用户额外要求（可选）"),
):
    """爆品复刻主接口：3 步 AI 链路

    返回：
        {success, structure, variations, product_analysis, video_source}
    """
    # === 1. 获取视频 bytes（上传 OR 链接下载）===
    if video and video.filename:
        raw = await video.read()
        mime = _guess_video_mime(video.filename, video.content_type)
        video_source = "upload"
    elif video_url:
        try:
            raw, mime = await download_tiktok(video_url, max_size_mb=15)
        except RuntimeError as e:
            logger.warning(f"视频链接下载失败 user={current_user['username']}: {e}")
            raise HTTPException(400, str(e))
        video_source = "link"
    else:
        raise HTTPException(400, "请上传视频文件或提供视频链接")

    size_mb = len(raw) / 1024 / 1024
    if len(raw) > MAX_VIDEO_SIZE:
        raise HTTPException(
            400,
            f"视频大小 {size_mb:.1f}MB 超过 15MB 限制，请压缩或截短后重试",
        )

    # === 2. 提取骨架 ===
    logger.info(
        f"爆品复刻请求 user={current_user['username']}, "
        f"source={video_source}, size={size_mb:.2f}MB"
    )
    try:
        structure = await _gemini.extract_viral_structure(raw, mime)
    except (RuntimeError, ValueError) as e:
        logger.error(f"骨架提取失败: {e}")
        raise HTTPException(500, f"视频骨架提取失败: {e}")

    # === 3. 商品分析（可选，失败不阻断）===
    product_analysis = None
    if product_images:
        try:
            first_raw = await product_images[0].read()
            compressed = compress_image(first_raw, max_long_edge=1280, format="JPEG")
            try:
                product_analysis = await _provider.analyze(compressed)
            except Exception as e:
                logger.warning(f"商品分析失败（不阻断）: {e}")
        except Exception as e:
            logger.warning(f"商品图压缩失败（不阻断）: {e}")

    # === 4. 拼接商品信息（用户输入 + AI 分析）===
    full_product_info = product_info or ""
    if product_analysis:
        # 去掉 _meta
        analysis_view = {k: v for k, v in product_analysis.items() if k != "_meta"}
        full_product_info += (
            f"\n\n[AI 商品分析]\n"
            f"{json.dumps(analysis_view, ensure_ascii=False, indent=2)}"
        )
    if not full_product_info.strip():
        full_product_info = "（用户未提供商品信息，请按常见服装/美妆商品推断）"

    # === 5. 裂变 ===
    try:
        variations = await _gemini.generate_replicate_variations(
            structure=structure,
            product_info=full_product_info,
            extra_prompt=extra_prompt or "",
            count=3,
        )
    except (RuntimeError, ValueError) as e:
        logger.error(f"裂变失败: {e}")
        raise HTTPException(500, f"裂变变体生成失败: {e}")

    logger.info(
        f"爆品复刻完成 user={current_user['username']}, "
        f"variations={len(variations)}"
    )

    return {
        "success": True,
        "structure": structure,
        "variations": variations,
        "product_analysis": product_analysis,
        "video_source": video_source,
        "video_size": len(raw),
        "video_mime": mime,
    }
