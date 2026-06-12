# Seedance 2.0 视频生成 Provider - API易中转站
# 与 SeedanceVideoProvider 相同的 API 格式，但走 API易中转（不排队，不限并发）
import logging

from app.config import settings
from app.providers.seedance_provider import SeedanceVideoProvider

logger = logging.getLogger(__name__)


class SeedanceApiyiVideoProvider(SeedanceVideoProvider):
    """字节跳动 Seedance 2.0 视频生成 Provider（API易中转站）

    API 格式与火山方舟直连完全一致，区别：
    - Base URL: api.apiyi.com/seedance/api/v3（多了 /seedance 前缀）
    - Auth: 使用 API易 令牌（非火山方舟 endpoint ID）
    - 优势：不限并发，不排队
    """

    API_BASE = "https://api.apiyi.com/seedance/api/v3"

    @property
    def name(self) -> str:
        return "seedance_apiyi"

    @property
    def is_available(self) -> bool:
        return bool(settings.seedance_apiyi_api_key)

    def _get_auth_token(self) -> str:
        """返回 API易 令牌"""
        return settings.seedance_apiyi_api_key

    async def submit(self, prompt, image=None, extra_images=None, params=None):
        """提交任务（覆盖 auth header）"""
        params = params or {}
        duration = params.get("duration", 5)
        ratio = params.get("ratio", "16:9")
        generate_audio = params.get("generate_audio", False)

        import base64
        import httpx

        from app.providers.base import RATE_LIMIT_MSG
        from app.services.http_client import get_http_client

        headers = {
            "Authorization": f"Bearer {self._get_auth_token()}",
            "Content-Type": "application/json",
            # 避免 gzip 解码错误（API易 网关已知问题）
            "Accept-Encoding": "identity",
        }

        # 构造 content 数组
        content = []

        if image:
            b64 = base64.b64encode(image).decode()
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                "role": "reference_image",
            })
        if extra_images:
            for img_bytes in extra_images:
                b64 = base64.b64encode(img_bytes).decode()
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    "role": "reference_image",
                })

        content.append({"type": "text", "text": prompt})

        payload = {
            "model": self.MODEL,
            "content": content,
            "ratio": ratio,
            "duration": duration,
            "generate_audio": generate_audio,
            "watermark": False,
        }

        url = f"{self.API_BASE}/contents/generations/tasks"

        try:
            client = get_http_client()
            resp = await client.post(url, headers=headers, json=payload, timeout=300)
            resp.raise_for_status()
            data = resp.json()

            task_id = data.get("id")
            if not task_id:
                raise RuntimeError(f"Seedance(API易) 提交失败，无返回 task_id: {data}")

            logger.info(f"Seedance(API易) 任务已提交: {task_id}")
            return task_id

        except httpx.HTTPStatusError as e:
            error_detail = e.response.text[:500]
            logger.error(f"Seedance(API易) 提交 API 错误: {e.response.status_code} - {error_detail}")
            if e.response.status_code == 429:
                raise RuntimeError(RATE_LIMIT_MSG)
            raise RuntimeError(f"Seedance(API易) 提交失败: {e.response.status_code} - {error_detail}")
        except Exception as e:
            logger.error(f"Seedance(API易) 提交异常: {e}")
            raise

    async def poll(self, external_task_id):
        """查询任务状态（覆盖 auth header）"""
        import httpx

        from app.services.http_client import get_http_client

        headers = {
            "Authorization": f"Bearer {self._get_auth_token()}",
            "Accept-Encoding": "identity",
        }
        url = f"{self.API_BASE}/contents/generations/tasks/{external_task_id}"

        try:
            client = get_http_client()
            resp = await client.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Seedance(API易) 轮询 API 错误: {e.response.status_code}")
            from app.providers.video_base import VideoTask
            return VideoTask(
                task_id=external_task_id,
                status="failed",
                error=f"轮询失败: {e.response.status_code}",
            )

        status = data.get("status", "").lower()

        # 状态映射
        status_map = {
            "pending": "pending",
            "processing": "processing",
            "running": "processing",
            "succeeded": "completed",
            "completed": "completed",
            "failed": "failed",
        }
        mapped_status = status_map.get(status, "pending")

        progress = 0
        if mapped_status == "processing":
            progress = data.get("progress", 50)
        elif mapped_status == "completed":
            progress = 100

        error = None
        if mapped_status == "failed":
            error_msg = data.get("error", {})
            if isinstance(error_msg, dict):
                error = error_msg.get("message", "视频生成失败")
            else:
                error = str(error_msg) or "视频生成失败"

        # 按 token 计费
        from app.providers.video_base import VideoTask

        cost = 0.0
        if mapped_status == "completed":
            usage = data.get("usage", {})
            completion_tokens = usage.get("completion_tokens", 0)
            if completion_tokens > 0:
                cost = round(completion_tokens * 28.0 / 1_000_000, 4)
            else:
                logger.warning(f"Seedance(API易) 任务 {external_task_id} 完成但无 usage 信息")

        return VideoTask(
            task_id=external_task_id,
            status=mapped_status,
            progress=progress,
            video_url=None,
            cost=cost,
            error=error,
            model_used=self.MODEL,
            meta={"raw_response": data},
        )
