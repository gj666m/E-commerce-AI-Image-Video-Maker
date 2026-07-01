# 图片处理工具 - 压缩、格式转换、base64、风格转换
import base64
import io
import logging

from PIL import Image

from app.config import settings

logger = logging.getLogger(__name__)

# 风格转换用固定 prompt：真人图 → 水彩插画风格
_STYLIZE_PROMPT = (
    "将这张人物照片转换为水彩插画风格的人物设计稿，"
    "保持人物的面部特征、发型、体型和姿态不变，"
    "使用柔和的水彩笔触和淡雅色彩，背景简洁纯色"
)


async def stylize_for_video(image_bytes: bytes) -> bytes:
    """将模特图转为水彩插画风格，绕过 Seedance 人脸检测

    调用 Seedream img2img，固定 prompt + 2k 尺寸，
    返回风格化后的图片 bytes。
    """
    from app.providers.volcengine_provider import VolcengineProvider

    provider = VolcengineProvider()
    result = await provider.generate(
        prompt=_STYLIZE_PROMPT,
        image=image_bytes,
        params={"size": "2k"},
    )

    if not result.success or not result.images:
        raise RuntimeError(f"风格转换失败: {result.error or '无图片返回'}")

    # 取第一张（通常只生成一张）
    stylized = result.images[0]
    logger.info(f"风格转换完成，输出大小: {len(stylized)} bytes")
    return stylized


def compress_image(
    image_bytes: bytes,
    max_long_edge: int | None = None,
    format: str = "PNG",
    min_short_edge: int | None = None,
) -> bytes:
    """压缩图片，长边不超过 max_long_edge，短边不小于 min_short_edge（保持比例）

    Args:
        image_bytes: 原始图片二进制
        max_long_edge: 长边最大像素，默认读配置
        format: 输出格式 PNG/JPEG
        min_short_edge: 短边最小像素，不足时等比放大（视频场景 Seedance 要求 ≥300px）

    Returns:
        压缩后的图片二进制
    """
    max_long_edge = max_long_edge or settings.image_max_long_edge
    img = Image.open(io.BytesIO(image_bytes))

    # 处理 RGBA 转 RGB（JPEG 不支持透明通道）
    if format == "JPEG" and img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # 等比缩放/放大：大图优先缩小长边，小图优先放大短边（两者互斥，避免循环）
    w, h = img.size
    long_edge = max(w, h)
    short_edge = min(w, h)

    if long_edge > max_long_edge:
        # 大图：等比缩小长边
        ratio = max_long_edge / long_edge
        new_w = int(w * ratio)
        new_h = int(h * ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)
    elif min_short_edge and short_edge < min_short_edge:
        # 小图但短边不足：等比放大短边（不放大长边，避免无谓放大小图）
        ratio = min_short_edge / short_edge
        new_w = int(w * ratio)
        new_h = int(h * ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format=format, quality=85 if format == "JPEG" else None)
    return buf.getvalue()


def image_to_base64(image_bytes: bytes) -> str:
    """图片二进制转 base64 字符串"""
    return base64.b64encode(image_bytes).decode("utf-8")


def base64_to_image(b64_str: str) -> bytes:
    """base64 字符串转图片二进制"""
    return base64.b64decode(b64_str)


def get_image_info(image_bytes: bytes) -> dict:
    """获取图片基本信息"""
    img = Image.open(io.BytesIO(image_bytes))
    return {
        "width": img.width,
        "height": img.height,
        "format": img.format,
        "mode": img.mode,
    }
