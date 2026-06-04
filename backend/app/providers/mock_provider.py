# Mock Provider - 无 API Key 时返回占位图
import io
import math
import textwrap

from PIL import Image, ImageDraw, ImageFont

from app.providers.base import BaseProvider, GenerateResult


class MockProvider(BaseProvider):
    """Mock 生图 Provider，返回带文字的占位图"""

    @property
    def name(self) -> str:
        return "mock"

    @property
    def is_available(self) -> bool:
        return True  # Mock 始终可用

    async def generate(
        self,
        prompt: str,
        image: bytes | None = None,
        images: list[bytes] | None = None,
        params: dict | None = None,
    ) -> GenerateResult:
        params = params or {}
        size_str = params.get("size", "1024x1024")
        width, height = self._parse_size(size_str)

        # 生成占位图
        img = self._create_placeholder(width, height, prompt)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()

        return GenerateResult(
            success=True,
            images=[img_bytes],
            cost=0.0,
            raw_response={"mock": True, "size": size_str},
        )

    def _parse_size(self, size_str: str) -> tuple[int, int]:
        """解析尺寸字符串，如 '1024x1024'"""
        try:
            w, h = size_str.lower().split("x")
            return int(w), int(h)
        except (ValueError, AttributeError):
            return 1024, 1024

    def _create_placeholder(self, width: int, height: int, prompt: str) -> Image.Image:
        """生成带文字说明的占位图"""
        img = Image.new("RGB", (width, height), color=(240, 240, 245))
        draw = ImageDraw.Draw(img)

        # 边框虚线效果
        margin = 40
        draw.rectangle(
            [margin, margin, width - margin, height - margin],
            outline=(200, 200, 210),
            width=2,
        )

        # 标题
        title = "[MOCK] AI Generated Image"
        self._draw_centered_text(draw, title, width, height * 0.35, size=32, fill=(100, 100, 120))

        # 尺寸信息
        size_text = f"{width} x {height}"
        self._draw_centered_text(draw, size_text, width, height * 0.5, size=24, fill=(150, 150, 170))

        # Prompt 摘要（截断显示）
        display_prompt = prompt[:200] + ("..." if len(prompt) > 200 else "")
        wrapped = textwrap.fill(display_prompt, width=50)
        self._draw_centered_text(draw, wrapped, width, height * 0.65, size=16, fill=(130, 130, 150))

        return img

    def _draw_centered_text(
        self, draw: ImageDraw.Draw, text: str, canvas_w: int, y: float,
        size: int = 20, fill: tuple = (0, 0, 0),
    ):
        """居中绘制文字（使用默认字体，按 size 缩放）"""
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
        except (OSError, IOError):
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        x = (canvas_w - text_w) / 2
        draw.text((x, y), text, font=font, fill=fill, align="center")
