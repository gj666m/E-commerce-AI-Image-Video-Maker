# GPT-Image-2-VIP Provider - API易中转站，支持 size + 4K
import logging

from app.config import settings
from app.providers.base import BaseProvider, GenerateResult, http_error_message
from app.providers.gptimage_provider import GPTImageProvider

logger = logging.getLogger(__name__)

# 统一按次计费 $0.03/张
COST_PER_CALL = 0.03

# 比例 → 4K Detail 档 size 对照表（文档验证的 30 档之一）
ASPECT_RATIO_TO_SIZE = {
    "1:1": "2880x2880",
    "3:4": "2480x3312",
    "4:3": "3312x2480",
    "4:5": "2560x3216",
    "5:4": "3216x2560",
    "9:16": "2160x3840",
    "16:9": "3840x2160",
    "2:3": "2336x3520",
    "3:2": "3520x2336",
    "21:9": "3840x1632",
    # A+ Banner 用最宽横版
    "61:25": "3840x1632",
}


class GPTImageVipProvider(GPTImageProvider):
    """GPT-Image-2-VIP 图片生成 Provider（API易中转站，支持 size + 4K）"""

    @property
    def name(self) -> str:
        return "gptimage_vip"

    @property
    def is_available(self) -> bool:
        return bool(settings.gptimage_vip_api_key)

    def _get_api_key(self) -> str:
        return settings.gptimage_vip_api_key

    def _get_base_url(self) -> str:
        return settings.gptimage_vip_base_url

    def _get_model(self) -> str:
        return settings.gptimage_vip_model

    def _build_generate_payload(self, prompt: str, params: dict | None = None) -> dict:
        """文生图请求体（含 size 参数，显式 n=1 按次计费）"""
        payload = {
            "model": self._get_model(),
            "prompt": prompt,
            "response_format": "b64_json",
            "n": 1,
        }
        # VIP 支持 size 参数，默认 4K Detail 档
        aspect_ratio = (params or {}).get("aspect_ratio", "")
        size = ASPECT_RATIO_TO_SIZE.get(aspect_ratio)
        if size:
            payload["size"] = size
        return payload

    def _build_edit_form(self, prompt: str, ref_images: list[bytes], params: dict | None = None) -> list:
        """图生图 multipart 表单（含 size 参数）"""
        fields = [
            ("prompt", (None, prompt)),
            ("model", (None, self._get_model())),
            ("response_format", (None, "b64_json")),
        ]
        # VIP 支持 size
        aspect_ratio = (params or {}).get("aspect_ratio", "")
        size = ASPECT_RATIO_TO_SIZE.get(aspect_ratio)
        if size:
            fields.append(("size", (None, size)))
        for i, img in enumerate(ref_images):
            fields.append(("image", (f"image_{i}.png", img, "image/png")))
        return fields

    async def generate(
        self,
        prompt: str,
        image: bytes | None = None,
        images: list[bytes] | None = None,
        params: dict | None = None,
    ) -> GenerateResult:
        """生成图片（VIP 版本，不拼比例前缀，用 size 参数控制）"""
        import httpx

        ref_images = []
        if image:
            ref_images.append(image)
        if images:
            ref_images.extend(images)

        headers = {
            "Authorization": f"Bearer {self._get_api_key()}",
        }

        try:
            async with httpx.AsyncClient(timeout=300) as client:
                if ref_images:
                    form_fields = self._build_edit_form(prompt, ref_images, params)
                    url = f"{self._get_base_url()}/v1/images/edits"
                    resp = await client.post(url, headers=headers, files=form_fields)
                else:
                    payload = self._build_generate_payload(prompt, params)
                    url = f"{self._get_base_url()}/v1/images/generations"
                    headers["Content-Type"] = "application/json"
                    resp = await client.post(url, headers=headers, json=payload)

                resp.raise_for_status()
                data = resp.json()

            result_images = self._extract_images(data)

            if not result_images:
                text_content = str(data.get("data", data))
                return GenerateResult(
                    success=False,
                    error=f"GPT-Image-VIP 未生成图片（可能被内容策略拒绝）: {text_content[:300]}",
                    raw_response=data,
                )

            return GenerateResult(
                success=True,
                images=result_images,
                cost=COST_PER_CALL,
                currency="$",
                raw_response=data,
            )

        except httpx.HTTPStatusError as e:
            error_text = e.response.text[:500]
            logger.warning(f"GPT-Image-VIP API 错误: {e.response.status_code} - {error_text}")
            return GenerateResult(
                success=False,
                error=http_error_message(e.response.status_code, error_text, "GPT-Image-VIP"),
                raw_response={"status_code": e.response.status_code},
            )
        except httpx.TimeoutException:
            return GenerateResult(
                success=False,
                error="GPT-Image-VIP 超时（300s），4K 出图较慢，请稍后重试",
            )
        except Exception as e:
            logger.error(f"GPT-Image-VIP 调用失败: {e}")
            return GenerateResult(
                success=False,
                error=f"GPT-Image-VIP 调用失败: {str(e)}",
            )
