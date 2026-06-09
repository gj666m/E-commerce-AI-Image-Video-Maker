# Nano Banana 2 Provider - Google Gemini 图片生成（通过 API易中转站）
import base64
import logging

import httpx

from app.config import settings
from app.providers.base import BaseProvider, GenerateResult

logger = logging.getLogger(__name__)

# Nano Banana 2 定价（$0.055/次调用）
COST_PER_CALL = 0.055


class NanoBananaProvider(BaseProvider):
    """Nano Banana 2 图片生成 Provider

    使用 Gemini API 格式（通过 API易中转站）：
    POST {base_url}/v1beta/models/{model}:generateContent

    支持：
    - 文生图：仅 prompt
    - 图生图：单张参考图
    """

    @property
    def name(self) -> str:
        return "nanobanana"

    @property
    def is_available(self) -> bool:
        return bool(settings.nanobanana_api_key)

    # 比例映射：项目比例 → Nano Banana 2 支持的比例
    ASPECT_RATIO_MAP = {
        "1:1": "1:1",
        "3:4": "3:4",
        "4:3": "4:3",
        "4:5": "4:5",
        "5:4": "5:4",
        "9:16": "9:16",
        "16:9": "16:9",
    }

    # 分辨率映射
    IMAGE_SIZE_MAP = {
        "512px": "512px",
        "1k": "1K",
        "2k": "2K",
        "4k": "4K",
    }

    async def generate(
        self,
        prompt: str,
        image: bytes | None = None,
        images: list[bytes] | None = None,
        params: dict | None = None,
    ) -> GenerateResult:
        params = params or {}

        # 解析比例和分辨率
        size_param = params.get("size", "2k")
        aspect_ratio = self.ASPECT_RATIO_MAP.get(size_param, "1:1")
        image_size = self.IMAGE_SIZE_MAP.get(size_param, "2K")

        # 如果是比例格式（如 "1:1"），使用默认分辨率 2K
        if ":" in size_param:
            image_size = "2K"

        headers = {
            "Authorization": f"Bearer {settings.nanobanana_api_key}",
            "Content-Type": "application/json",
        }

        # 构建 parts
        parts = []

        # 图生图：添加参考图
        ref_image = image or (images[0] if images else None)
        if ref_image:
            b64_ref = base64.b64encode(ref_image).decode()
            parts.append({
                "inlineData": {
                    "mimeType": "image/png",
                    "data": b64_ref,
                }
            })

        parts.append({"text": prompt})

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "responseModalities": ["IMAGE"],
                "imageConfig": {
                    "aspectRatio": aspect_ratio,
                    "imageSize": image_size,
                }
            }
        }

        model = settings.nanobanana_model
        url = f"{settings.nanobanana_base_url}/v1beta/models/{model}:generateContent"

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()

            images_result = self._extract_images(data)
            cost = round(COST_PER_CALL, 4)

            return GenerateResult(
                success=True,
                images=images_result,
                cost=cost,
                raw_response=data,
            )
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text[:500]
            logger.error(f"Nano Banana API 错误: {e.response.status_code} - {error_detail}")
            return GenerateResult(
                success=False,
                error=f"Nano Banana API 错误: {e.response.status_code} - {error_detail}",
                raw_response={"status_code": e.response.status_code},
            )
        except Exception as e:
            logger.error(f"Nano Banana 调用失败: {e}")
            return GenerateResult(
                success=False,
                error=f"Nano Banana 调用失败: {str(e)}",
            )

    def _extract_images(self, data: dict) -> list[bytes]:
        """从 Gemini API 响应中提取图片二进制"""
        images = []
        try:
            candidates = data.get("candidates", [])
            for candidate in candidates:
                parts = candidate.get("content", {}).get("parts", [])
                for part in parts:
                    inline_data = part.get("inlineData", {})
                    b64 = inline_data.get("data")
                    if b64:
                        images.append(base64.b64decode(b64))
        except (KeyError, IndexError) as e:
            logger.error(f"解析 Nano Banana 响应失败: {e}")
        return images
