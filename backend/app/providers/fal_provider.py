# fal.ai Provider - FLUX 生图（队列模式：提交 → 轮询 → 取结果）
import base64
import asyncio

import httpx

from app.config import settings
from app.providers.base import BaseProvider, GenerateResult, http_error_message

# FLUX 模型定价（美元/张，估算）
COST_TABLE = {
    "1024x1024": 0.025,
    "1024x1536": 0.035,
    "1536x1024": 0.035,
}

# fal.ai 队列轮询配置
POLL_INTERVAL = 2  # 秒
POLL_MAX_WAIT = 120  # 最多等 120 秒


class FalProvider(BaseProvider):
    """fal.ai Provider（FLUX 模型，队列模式）"""

    API_BASE = "https://queue.fal.run"

    # fal.ai 上的模型 ID
    MODELS = {
        "flux-dev": "fal-ai/flux/dev",
        "flux-schnell": "fal-ai/flux/schnell",
        "flux-pro": "fal-ai/flux-pro",
    }

    DEFAULT_MODEL = "flux-schnell"

    @property
    def name(self) -> str:
        return "fal"

    @property
    def is_available(self) -> bool:
        return settings.has_fal

    async def generate(
        self,
        prompt: str,
        image: bytes | None = None,
        images: list[bytes] | None = None,
        params: dict | None = None,
    ) -> GenerateResult:
        params = params or {}
        size = params.get("size", "1024x1024")
        model_id = params.get("model_id", self.DEFAULT_MODEL)
        fal_model = self.MODELS.get(model_id, self.MODELS[self.DEFAULT_MODEL])

        headers = {
            "Authorization": f"Key {settings.fal_api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "prompt": prompt,
            "image_size": self._parse_size(size),
            "num_images": 1,
        }

        # 图生图：加入参考图
        if image:
            b64 = base64.b64encode(image).decode()
            payload["image_url"] = f"data:image/png;base64,{b64}"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # 1. 提交任务到队列
                submit_url = f"{self.API_BASE}/{fal_model}"
                submit_resp = await client.post(submit_url, headers=headers, json=payload)
                submit_resp.raise_for_status()
                request_id = submit_resp.json()["request_id"]

                # 2. 轮询结果
                status_url = f"{self.API_BASE}/{fal_model}/requests/{request_id}/status"
                result_url = f"{self.API_BASE}/{fal_model}/requests/{request_id}"

                elapsed = 0
                while elapsed < POLL_MAX_WAIT:
                    await asyncio.sleep(POLL_INTERVAL)
                    elapsed += POLL_INTERVAL

                    status_resp = await client.get(status_url, headers=headers)
                    status_resp.raise_for_status()
                    status_data = status_resp.json()

                    if status_data["status"] == "COMPLETED":
                        # 3. 获取结果
                        result_resp = await client.get(result_url, headers=headers)
                        result_resp.raise_for_status()
                        return self._parse_result(result_resp.json(), size)

                    elif status_data["status"] in ("FAILED", "CANCELLED"):
                        return GenerateResult(
                            success=False,
                            error=f"fal.ai 任务失败: {status_data.get('error', 'unknown')}",
                            raw_response=status_data,
                        )

                return GenerateResult(
                    success=False,
                    error=f"fal.ai 超时（{POLL_MAX_WAIT}秒）",
                )

        except httpx.HTTPStatusError as e:
            return GenerateResult(
                success=False,
                error=http_error_message(e.response.status_code, str(e.response.text[:200]), "fal.ai"),
                raw_response={"status_code": e.response.status_code},
            )
        except Exception as e:
            return GenerateResult(
                success=False,
                error=f"fal.ai 调用失败: {str(e)}",
            )

    def _parse_size(self, size_str: str) -> str:
        """'1024x1024' → 'square_hd' 等 fal.ai 格式"""
        size_map = {
            "1024x1024": "square_hd",
            "1024x1536": "portrait_16_12",
            "1536x1024": "landscape_16_12",
        }
        return size_map.get(size_str, "square_hd")

    def _parse_result(self, data: dict, size: str) -> GenerateResult:
        """解析 fal.ai 返回结果"""
        images = []
        for img_data in data.get("images", []):
            url = img_data.get("url")
            if url:
                # fal.ai 返回图片 URL，下载为二进制
                import sync_httpx
                # 用 httpx 同步下载（在 async 中用 run_in_executor）
                # 这里简化处理，返回 URL 让调用方下载
                images.append(url.encode())  # 临时用 URL 字节代替
            else:
                b64 = img_data.get("b64_json")
                if b64:
                    images.append(base64.b64decode(b64))

        cost = COST_TABLE.get(size, 0.025)

        return GenerateResult(
            success=True,
            images=images,
            cost=cost,
            currency="$",
            raw_response=data,
        )
