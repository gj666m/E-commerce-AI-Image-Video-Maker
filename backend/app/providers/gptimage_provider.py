# GPT-Image-2-All Provider - API易中转站 OpenAI Images API 格式
import base64
import logging

import httpx

from app.config import settings
from app.providers.base import BaseProvider, GenerateResult, http_error_message

logger = logging.getLogger(__name__)

# 统一按次计费 $0.03/张
COST_PER_CALL = 0.03

# 比例 → prompt 前缀对照表（经过验证的稳定写法）
ASPECT_RATIO_PROMPTS = {
    "1:1": "1:1 方形构图",
    "3:4": "3:4",
    "4:3": "4:3",
    "4:5": "3:4",    # 4:5 无直接对照，用最接近的 3:4
    "5:4": "4:3",    # 5:4 无直接对照，用最接近的 4:3
    "9:16": "竖屏 9:16",
    "16:9": "横版 16:9",
    "3:2": "3:2 尺寸",
    "2:3": "2:3 尺寸",
    "2:5": "2:5 竖屏",
    "5:2": "5:2 横屏",
    "61:25": "横版 16:9",  # A+ Banner 用最宽的横版
}


class GPTImageProvider(BaseProvider):
    """GPT-Image-2-All 图片生成 Provider（API易中转站）"""

    @property
    def name(self) -> str:
        return "gptimage"

    @property
    def is_available(self) -> bool:
        return bool(settings.gptimage_api_key)

    async def generate(
        self,
        prompt: str,
        image: bytes | None = None,
        images: list[bytes] | None = None,
        params: dict | None = None,
    ) -> GenerateResult:
        params = params or {}
        aspect_ratio = params.get("aspect_ratio", "")

        # 比例前缀拼到 prompt 开头
        size_prefix = ASPECT_RATIO_PROMPTS.get(aspect_ratio, "")
        if size_prefix:
            final_prompt = f"{size_prefix}，{prompt}"
        else:
            final_prompt = prompt

        # 收集参考图
        ref_images = []
        if image:
            ref_images.append(image)
        if images:
            ref_images.extend(images)

        headers = {
            "Authorization": f"Bearer {settings.gptimage_api_key}",
        }

        try:
            async with httpx.AsyncClient(timeout=300) as client:
                if ref_images:
                    # 图生图：/v1/images/edits（multipart）
                    form_fields = self._build_edit_form(final_prompt, ref_images)
                    url = f"{settings.gptimage_base_url}/v1/images/edits"
                    resp = await client.post(url, headers=headers, files=form_fields)
                else:
                    # 文生图：/v1/images/generations
                    payload = self._build_generate_payload(final_prompt)
                    url = f"{settings.gptimage_base_url}/v1/images/generations"
                    headers["Content-Type"] = "application/json"
                    resp = await client.post(url, headers=headers, json=payload)

                resp.raise_for_status()
                data = resp.json()

            result_images = self._extract_images(data)

            if not result_images:
                # 200 但可能是文字软拒绝
                text_content = str(data.get("data", data))
                return GenerateResult(
                    success=False,
                    error=f"GPT-Image 未生成图片（可能被内容策略拒绝）: {text_content[:300]}",
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
            logger.warning(f"GPT-Image API 错误: {e.response.status_code} - {error_text}")
            return GenerateResult(
                success=False,
                error=http_error_message(e.response.status_code, error_text, "GPT-Image"),
                raw_response={"status_code": e.response.status_code},
            )
        except httpx.TimeoutException:
            return GenerateResult(
                success=False,
                error="GPT-Image 超时（300s），请稍后重试",
            )
        except Exception as e:
            logger.error(f"GPT-Image 调用失败: {e}")
            return GenerateResult(
                success=False,
                error=f"GPT-Image 调用失败: {str(e)}",
            )

    def _build_generate_payload(self, prompt: str) -> dict:
        """文生图请求体（显式 n=1，按次计费 $0.03/张）"""
        return {
            "model": settings.gptimage_model,
            "prompt": prompt,
            "response_format": "b64_json",
            "n": 1,
        }

    def _build_edit_form(self, prompt: str, ref_images: list[bytes]) -> list:
        """图生图 multipart 表单"""
        fields = [
            ("prompt", (None, prompt)),
            ("model", (None, settings.gptimage_model)),
            ("response_format", (None, "b64_json")),
        ]
        for i, img in enumerate(ref_images):
            fields.append(("image", (f"image_{i}.png", img, "image/png")))
        return fields

    def _extract_images(self, data: dict) -> list[bytes]:
        """从 API 响应提取图片二进制

        gpt-image-2-all 的 b64_json 已含 data:image/png;base64, 前缀，
        需要先剥离再 decode。

        设计为 n=1 按次计费，中转站偶发返回多张图（上游聚合 bug），
        只取第一张，避免 cost 被错误平摊（generate.py 里 per_cost = cost/len(images)）。
        """
        items = data.get("data", [])
        if not items:
            return []
        # 只取第一张，丢弃中转站偶发返回的冗余图
        item = items[0]
        b64 = item.get("b64_json")
        if b64:
            if b64.startswith("data:"):
                b64 = b64.split(",", 1)[1]
            return [base64.b64decode(b64)]
        # 备用：url 格式（不应走到这里，因为请求了 b64_json）
        url = item.get("url")
        if url:
            logger.info(f"GPT-Image 返回了 URL 而非 b64_json: {url[:80]}...")
            try:
                resp = httpx.get(url, timeout=60)
                resp.raise_for_status()
                return [resp.content]
            except Exception as e:
                logger.error(f"下载 GPT-Image URL 失败: {e}")
        return []
