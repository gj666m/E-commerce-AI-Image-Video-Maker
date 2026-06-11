# 火山方舟 Seedream Provider - 文生图 + 图生图 + 多图生图
import base64
import logging

import httpx

from app.config import settings
from app.providers.base import BaseProvider, GenerateResult, http_error_message
from app.services.http_client import get_http_client

logger = logging.getLogger(__name__)

# Seedream 4.5 定价（元/张，火山方舟国内版）
COST_PER_IMAGE = 0.25


class VolcengineProvider(BaseProvider):
    """火山方舟 Seedream 图片生成 Provider

    API 兼容 OpenAI 格式：
    POST https://ark.cn-beijing.volces.com/api/v3/images/generations

    支持：
    - 文生图：仅 prompt
    - 单图生图：image（单张参考图）
    - 多图生图：images（最多 14 张参考图，prompt 中用"图1""图2"引用）
    """

    API_BASE = "https://ark.cn-beijing.volces.com/api/v3"

    @property
    def name(self) -> str:
        return "volcengine"

    @property
    def is_available(self) -> bool:
        return bool(settings.volcengine_api_key)

    # Seedream 4.5 尺寸/质量映射
    SIZE_MAP = {
        # 质量级别
        "4k": "4k",
        "2k": "2k",
        "1k": "1k",
        # 比例格式（全部用 4k 质量级别）
        "1:1": "4k",
        "3:4": "4k",
        "4:3": "4k",
        "4:5": "4k",
        "5:4": "4k",
        "9:16": "4k",
        "16:9": "4k",
        # 旧格式兼容
        "1024x1024": "4k",
        "1536x1024": "4k",
        "1024x1536": "4k",
    }

    async def generate(
        self,
        prompt: str,
        image: bytes | None = None,
        images: list[bytes] | None = None,
        params: dict | None = None,
    ) -> GenerateResult:
        params = params or {}
        size = self.SIZE_MAP.get(params.get("size", "2K"), "2K")

        headers = {
            "Authorization": f"Bearer {settings.volcengine_api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": settings.volcengine_model_id,
            "prompt": prompt,
            "size": size,
            "response_format": "url",
            "sequential_image_generation": "disabled",
            "stream": False,
            "watermark": False,
        }

        # 多图生图：images 参数传数组（最多 14 张）
        if images and len(images) > 0:
            b64_images = []
            for img_bytes in images:
                b64 = base64.b64encode(img_bytes).decode()
                b64_images.append(f"data:image/png;base64,{b64}")
            # 单张也用数组格式（Seedream API 兼容）
            payload["image"] = b64_images if len(b64_images) > 1 else b64_images[0]
        elif image:
            # 单张图生图（向后兼容）
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
                raw_response=data,
            )
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text[:500]
            logger.error(f"Volcengine API 错误: {e.response.status_code} - {error_detail}")
            return GenerateResult(
                success=False,
                error=http_error_message(e.response.status_code, error_detail, "火山方舟"),
                raw_response={"status_code": e.response.status_code},
            )
        except Exception as e:
            logger.error(f"Volcengine 调用失败: {e}")
            return GenerateResult(
                success=False,
                error=f"火山方舟调用失败: {str(e)}",
            )

    async def _extract_images(self, data: dict) -> list[bytes]:
        """从 API 响应中提取图片二进制（支持 url 和 b64_json 两种格式）"""
        images = []
        for item in data.get("data", []):
            # 优先用 b64_json
            b64 = item.get("b64_json")
            if b64:
                images.append(base64.b64decode(b64))
                continue
            # 从 URL 下载
            img_url = item.get("url")
            if img_url:
                client = get_http_client()
                resp = await client.get(img_url, timeout=60)
                if resp.status_code == 200:
                    images.append(resp.content)
        return images
