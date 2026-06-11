# Seedream 5.0 Lite Provider - 继承 VolcengineProvider，使用独立 API Key
from app.config import settings
from app.providers.volcengine_provider import VolcengineProvider


class Seedream5Provider(VolcengineProvider):
    """火山方舟 Seedream 5.0 Lite 图片生成 Provider

    API 格式与 Seedream 4.5 完全相同，仅 API Key 和 Model ID 不同。
    支持 3K 分辨率。
    """

    @property
    def name(self) -> str:
        return "seedream5"

    @property
    def is_available(self) -> bool:
        return bool(settings.seedream5_api_key)

    async def generate(self, prompt, image=None, images=None, params=None):
        """覆盖父类方法，使用独立的 API Key 和 Model ID"""
        import base64
        import logging
        import httpx
        from app.services.http_client import get_http_client
        from app.providers.base import GenerateResult, http_error_message

        logger = logging.getLogger(__name__)
        params = params or {}
        size = self.SIZE_MAP.get(params.get("size", "2K"), "2K")

        headers = {
            "Authorization": f"Bearer {settings.seedream5_api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": settings.seedream5_model_id,
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
            # Seedream 5.0 定价：¥0.22/张（火山方舟国内版）
            cost = round(0.22 * len(images_result), 4)

            return GenerateResult(
                success=True,
                images=images_result,
                cost=cost,
                currency="¥",
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
