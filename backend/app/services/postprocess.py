# 图片后处理服务 — 轻微颗粒+色调调整，提升真实感（纯 Pillow，无额外依赖）
import io
import logging
import random

from PIL import Image, ImageEnhance, ImageFilter

logger = logging.getLogger(__name__)


def apply_realistic_filter(image_bytes: bytes, intensity: str = "light") -> bytes:
    """对生成图片应用轻微后处理，降低 AI 感

    处理链：
    1. 轻微胶片颗粒（模拟手机拍摄噪点）
    2. 轻微暖色温偏移（模拟自然光）
    3. 对比度微调（避免过于完美）
    4. 轻微模糊+锐化（模拟手机镜头质感）

    Args:
        image_bytes: 原图二进制
        intensity: 强度 light(默认) / medium / strong

    Returns:
        处理后的图片二进制
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        original_mode = img.mode

        if img.mode != "RGB":
            img = img.convert("RGB")

        # 强度参数
        presets = {
            "light": {"grain": 8, "warmth": 3, "contrast": 0.97, "blur_radius": 0.3},
            "medium": {"grain": 15, "warmth": 5, "contrast": 0.95, "blur_radius": 0.5},
            "strong": {"grain": 25, "warmth": 8, "contrast": 0.93, "blur_radius": 0.7},
        }
        p = presets.get(intensity, presets["light"])

        # 1. 轻微胶片颗粒
        img = _add_grain(img, amount=p["grain"])

        # 2. 轻微暖色温
        img = _apply_warm_tone(img, strength=p["warmth"])

        # 3. 对比度微调
        if p["contrast"] != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(p["contrast"])

        # 4. 轻微模糊 + 锐化（模拟手机镜头）
        if p["blur_radius"] > 0:
            img = img.filter(ImageFilter.GaussianBlur(radius=p["blur_radius"]))
            img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=50))

        # 编码
        buf = io.BytesIO()
        save_format = "JPEG" if original_mode in ("RGB", "L") else "PNG"
        img.save(buf, format=save_format, quality=95)
        return buf.getvalue()

    except Exception as e:
        logger.warning(f"后处理失败，返回原图: {e}")
        return image_bytes


def _add_grain(img: Image.Image, amount: int = 8) -> Image.Image:
    """用纯 Pillow 添加颗粒噪点

    原理：生成一张随机噪点图（灰度），以低透明度叠加到原图上
    """
    noise = Image.effect_noise(img.size, random.randint(0, 999))
    noise = noise.convert("RGB")
    # 降低噪点强度
    enhancer = ImageEnhance.Brightness(noise)
    noise = enhancer.enhance(0.5)
    # 以低透明度混合
    return Image.blend(img, noise, alpha=amount / 255.0)


def _apply_warm_tone(img: Image.Image, strength: int = 3) -> Image.Image:
    """轻微暖色温偏移

    原理：通过 point() 分别微调 R（增）和 B（减）通道
    """
    r, g, b = img.split()

    # R 通道微增
    r = r.point(lambda x: min(255, x + strength))
    # B 通道微减
    b = b.point(lambda x: max(0, x - strength))

    return Image.merge("RGB", (r, g, b))
