# OpenAI Provider - GPT-Image-2 生图
import base64
import httpx

from app.config import settings
from app.providers.base import BaseProvider, GenerateResult, http_error_message

# GPT-Image-2 定价（美元/张，按尺寸）
COST_TABLE = {
    "1024x1024": 0.019,
    "1024x1536": 0.028,
    "1536x1024": 0.028,
}


class OpenAIProvider(BaseProvider):
    """OpenAI GPT-Image-2 Provider"""

    API_BASE = "https://api.openai.com/v1"

    @property
    def name(self) -> str:
        return "openai"

    @property
    def is_available(self) -> bool:
        return settings.has_openai

    async def generate(
        self,
        prompt: str,
        image: bytes | None = None,
        images: list[bytes] | None = None,
        params: dict | None = None,
    ) -> GenerateResult:
        params = params or {}
        size = params.get("size", "1024x1024")

        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }

        if image:
            # 图生图：编辑模式
            payload = await self._build_edit_payload(prompt, image, size)
            url = f"{self.API_BASE}/images/edits"
        else:
            # 纯文生图
            payload = self._build_generate_payload(prompt, size)
            url = f"{self.API_BASE}/images/generations"

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                if image:
                    # edits 接口用 multipart
                    form_data = await self._build_edit_form(prompt, image, size)
                    headers.pop("Content-Type", None)
                    resp = await client.post(url, headers=headers, files=form_data)
                else:
                    resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()

            images = self._extract_images(data)
            cost = self._calc_cost(size, len(images))

            return GenerateResult(
                success=True,
                images=images,
                cost=cost,
                currency="$",
                raw_response=data,
            )
        except httpx.HTTPStatusError as e:
            return GenerateResult(
                success=False,
                error=http_error_message(e.response.status_code, e.response.text[:500], "OpenAI"),
                raw_response={"status_code": e.response.status_code},
            )
        except Exception as e:
            return GenerateResult(
                success=False,
                error=f"OpenAI 调用失败: {str(e)}",
            )

    def _build_generate_payload(self, prompt: str, size: str) -> dict:
        """文生图请求体"""
        return {
            "model": "gpt-image-2",
            "prompt": prompt,
            "n": 1,
            "size": size,
        }

    async def _build_edit_form(self, prompt: str, image: bytes, size: str) -> list:
        """图生图 multipart 表单"""
        return [
            ("image", ("product.png", image, "image/png")),
            ("prompt", (None, prompt)),
            ("model", (None, "gpt-image-2")),
            ("n", (None, "1")),
            ("size", (None, size)),
        ]

    async def _build_edit_payload(self, prompt: str, image: bytes, size: str) -> dict:
        """图生图 JSON body（备用）"""
        b64 = base64.b64encode(image).decode()
        return {
            "model": "gpt-image-2",
            "prompt": prompt,
            "image": f"data:image/png;base64,{b64}",
            "n": 1,
            "size": size,
        }

    def _extract_images(self, data: dict) -> list[bytes]:
        """从 API 响应中提取图片二进制"""
        images = []
        for item in data.get("data", []):
            b64 = item.get("b64_json")
            if b64:
                images.append(base64.b64decode(b64))
        return images

    def _calc_cost(self, size: str, count: int) -> float:
        """计算调用成本"""
        unit_cost = COST_TABLE.get(size, 0.019)
        return round(unit_cost * count, 4)
