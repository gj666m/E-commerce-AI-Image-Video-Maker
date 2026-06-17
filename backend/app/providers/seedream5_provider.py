# Seedream 5.0 Provider - 通过 API易 中转站调用（2026-06-17 由火山方舟官方切中转）
import base64
import logging

import httpx

from app.config import settings
from app.providers.base import GenerateResult, http_error_message
from app.services.http_client import get_http_client

logger = logging.getLogger(__name__)

# Seedream 5.0 定价（USD/张，API易中转站）
COST_PER_IMAGE = 0.035


class Seedream5Provider:
    """Seedream 5.0 图片生成 Provider（API易中转）

    与 Seedream 4.5 使用同一端点 `/v1/images/generations`，仅 API Key、Model ID、
    分辨率档位不同。5.0 支持 2K / 3K（不支持 4K）。
    """

    API_BASE = "https://api.apiyi.com/v1"

    # 5.0 支持 2K / 3K；其他档位降级到 2K
    SIZE_MAP = {
        "2K": "2K",
        "3K": "3K",
        "2k": "2K",
        "3k": "3K",
        # 比例格式统一走 2K（宽高比由 prompt 推断）
        "1:1": "2K",
        "3:4": "2K",
        "4:3": "2K",
        "4:5": "2K",
        "5:4": "2K",
        "9:16": "2K",
        "16:9": "2K",
        "4K": "2K",  # 5.0 不支持 4K，降级
        "4k": "2K",
        "1k": "2K",
        "1K": "2K",
    }

    @property
    def name(self) -> str:
        return "seedream5"

    @property
    def is_available(self) -> bool:
        return bool(settings.seedream5_apiyi_api_key)

    async def generate(self, prompt, image=None, images=None, params=None):
        params = params or {}
        size = self.SIZE_MAP.get(params.get("size", "2K"), "2K")

        headers = {
            "Authorization": f"Bearer {settings.seedream5_apiyi_api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": settings.seedream5_apiyi_model,
            "prompt": prompt,
            "size": size,
            "response_format": "url",
            "sequential_image_generation": "disabled",
            "stream": False,
            "watermark": False,
        }

        # 多图生图
        if images and len(images) > 0:
            b64_images = []
            for img_bytes in images:
                b64 = base64.b64encode(img_bytes).decode()
                b64_images.append(f"data:image/png;base64,{b64}")
            payload["image"] = b64_images if len(b64_images) > 1 else b64_images[0]
        elif image:
            b64_image = base64.b64encode(image).decode()
            payload["image"] = f"data:image/png;base64,{b64_image}"

        url = f"{self.API_BASE}/images/generations"

        try:
            client = get_http_client()
            resp = await client.post(url, headers=headers, json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()

            images_result = await self._extract_images(data)
            cost = round(COST_PER_IMAGE * len(images_result), 4)

            return GenerateResult(
                success=True,
                images=images_result,
                cost=cost,
                currency="$",
                raw_response=data,
            )
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text[:500]
            logger.error(f"Seedream 5.0 API 错误: {e.response.status_code} - {error_detail}")
            return GenerateResult(
                success=False,
                error=http_error_message(e.response.status_code, error_detail, "Seedream 5.0"),
                raw_response={"status_code": e.response.status_code},
            )
        except Exception as e:
            logger.error(f"Seedream 5.0 调用失败: {e}")
            return GenerateResult(
                success=False,
                error=f"Seedream 5.0 调用失败: {str(e)}",
            )

    async def _extract_images(self, data: dict) -> list[bytes]:
        """从 API 响应中提取图片二进制（支持 url 和 b64_json 两种格式）"""
        images = []
        for item in data.get("data", []):
            b64 = item.get("b64_json")
            if b64:
                images.append(base64.b64decode(b64))
                continue
            img_url = item.get("url")
            if img_url:
                client = get_http_client()
                resp = await client.get(img_url, timeout=60)
                if resp.status_code == 200:
                    images.append(resp.content)
        return images
