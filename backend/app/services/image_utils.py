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
) -> bytes:
    """压缩图片，长边不超过 max_long_edge，保持比例

    Args:
        image_bytes: 原始图片二进制
        max_long_edge: 长边最大像素，默认读配置
        format: 输出格式 PNG/JPEG

    Returns:
        压缩后的图片二进制
    """
    max_long_edge = max_long_edge or settings.image_max_long_edge
    img = Image.open(io.BytesIO(image_bytes))

    # 处理 RGBA 转 RGB（JPEG 不支持透明通道）
    if format == "JPEG" and img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # 等比缩放
    w, h = img.size
    long_edge = max(w, h)
    if long_edge > max_long_edge:
        ratio = max_long_edge / long_edge
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


def bypass_face_detection(image_bytes: bytes) -> bytes:
    """人脸切割错位绕过人脸检测

    将图片纵向切成 3 条，每条水平错位若干像素再拼回。
    肉眼几乎无感，但破坏人脸检测算法的空间特征提取。
    参考：ZeroLu/seedance2.0-how-to 社区方案
    """
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")

    w, h = img.size
    num_strips = 5  # 纵切条数
    offsets = [0, 30, -25, 20, -30]  # 每条水平错位像素（正=右移，负=左移）

    strip_w = w // num_strips
    result = Image.new("RGB", (w, h))

    for i in range(num_strips):
        x_start = i * strip_w
        x_end = x_start + strip_w if i < num_strips - 1 else w
        strip = img.crop((x_start, 0, x_end, h))

        # 应用水平错位：在新画布上偏移粘贴
        paste_x = x_start + offsets[i]
        # 边界裁剪
        src_x = max(0, -offsets[i]) if paste_x < 0 else 0
        dst_x = max(0, paste_x)
        actual_w = min(strip_w, w - dst_x)

        if actual_w > 0:
            cropped = strip.crop((src_x, 0, src_x + actual_w, h))
            result.paste(cropped, (dst_x, 0))

    buf = io.BytesIO()
    result.save(buf, format="JPEG", quality=95)
    return buf.getvalue()
