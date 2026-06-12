# Seedance 2.0 视频生成 Provider - 火山方舟异步任务模式
import base64
import logging

import httpx

from app.config import settings
from app.providers.video_base import VideoProvider, VideoTask
from app.providers.base import RATE_LIMIT_MSG
from app.services.http_client import get_http_client

logger = logging.getLogger(__name__)

# Seedance 2.0 定价：¥28/百万 token（按 usage.completion_tokens 计算）
COST_PER_MILLION_TOKENS = 28.0


class SeedanceVideoProvider(VideoProvider):
    """字节跳动 Seedance 2.0 视频生成 Provider

    API 使用火山方舟异步任务模式：
    1. POST /api/v3/contents/generations/tasks → 提交任务
    2. GET /api/v3/contents/generations/tasks/{id} → 轮询状态
    3. 完成后从 content 中提取视频 URL → 下载保存

    支持：
    - 文生视频：仅 prompt
    - 图生视频：prompt + 参考图（base64 data URL）
    - 音频生成：generate_audio=true 时根据 prompt 中的音频描述生成
    """

    API_BASE = "https://ark.cn-beijing.volces.com/api/v3"
    MODEL = "doubao-seedance-2-0-260128"

    @property
    def name(self) -> str:
        return "seedance"

    @property
    def is_available(self) -> bool:
        return bool(settings.volcengine_seedance_endpoint)

    async def submit(
        self,
        prompt: str,
        image: bytes | None = None,
        extra_images: list[bytes] | None = None,
        params: dict | None = None,
    ) -> str:
        """提交视频生成任务（支持多参考图）"""
        params = params or {}
        duration = params.get("duration", 5)
        ratio = params.get("ratio", "16:9")
        generate_audio = params.get("generate_audio", False)
        resolution = params.get("resolution")  # 480p / 720p / 1080p

        headers = {
            "Authorization": f"Bearer {settings.volcengine_seedance_endpoint}",
            "Content-Type": "application/json",
        }

        # 构造 content 数组
        content: list[dict] = []

        # 参考图
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

        # 文本描述
        content.append({
            "type": "text",
            "text": prompt,
        })

        payload = {
            "model": self.MODEL,
            "content": content,
            "ratio": ratio,
            "duration": duration,
            "generate_audio": generate_audio,
            "watermark": False,
            "content_safety": {
                "face_detection_level": "low",
                "allow_virtual_face": True,
            },
        }

        # 分辨率（不传则 API 默认）
        if resolution:
            payload["resolution"] = resolution

        url = f"{self.API_BASE}/contents/generations/tasks"

        try:
            client = get_http_client()
            resp = await client.post(url, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()

            task_id = data.get("id")
            if not task_id:
                raise RuntimeError(f"Seedance 提交失败，无返回 task_id: {data}")

            logger.info(f"Seedance 任务已提交: {task_id}")
            return task_id

        except httpx.HTTPStatusError as e:
            error_detail = e.response.text[:500]
            logger.error(f"Seedance 提交 API 错误: {e.response.status_code} - {error_detail}")
            if e.response.status_code == 429:
                raise RuntimeError(RATE_LIMIT_MSG)
            raise RuntimeError(f"Seedance 提交失败: {e.response.status_code} - {error_detail}")
        except Exception as e:
            logger.error(f"Seedance 提交异常: {e}")
            raise

    async def poll(self, external_task_id: str) -> VideoTask:
        """查询任务状态"""
        headers = {
            "Authorization": f"Bearer {settings.volcengine_seedance_endpoint}",
        }
        url = f"{self.API_BASE}/contents/generations/tasks/{external_task_id}"

        try:
            client = get_http_client()
            resp = await client.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Seedance 轮询 API 错误: {e.response.status_code}")
            return VideoTask(
                task_id=external_task_id,
                status="failed",
                error=f"轮询失败: {e.response.status_code}",
            )

        status = data.get("status", "").lower()

        # 状态映射：Seedance 状态 → 内部状态
        status_map = {
            "pending": "pending",
            "processing": "processing",
            "running": "processing",
            "succeeded": "completed",
            "completed": "completed",
            "failed": "failed",
        }
        mapped_status = status_map.get(status, "pending")

        # 进度估算
        progress = 0
        if mapped_status == "processing":
            progress = data.get("progress", 50)
        elif mapped_status == "completed":
            progress = 100

        # 错误信息
        error = None
        if mapped_status == "failed":
            error_msg = data.get("error", {})
            if isinstance(error_msg, dict):
                error = error_msg.get("message", "视频生成失败")
            else:
                error = str(error_msg) or "视频生成失败"

        # 按实际 token 用量计费（¥28/百万 token）
        cost = 0.0
        if mapped_status == "completed":
            usage = data.get("usage", {})
            completion_tokens = usage.get("completion_tokens", 0)
            if completion_tokens > 0:
                cost = round(completion_tokens * COST_PER_MILLION_TOKENS / 1_000_000, 4)
            else:
                # 兜底：无 usage 信息时不计费
                logger.warning(f"Seedance 任务 {external_task_id} 完成但无 usage 信息")

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

    async def get_result(self, external_task_id: str) -> bytes:
        """下载生成的视频二进制"""
        task = await self.poll(external_task_id)

        if task.status != "completed":
            raise RuntimeError(f"任务未完成: {task.status}, 错误: {task.error}")

        # 从原始响应中提取视频 URL
        raw = task.meta.get("raw_response", {})
        content = raw.get("content", {})
        video_url = None

        if isinstance(content, dict):
            # Seedance 2.0 返回 {"video_url": "https://..."}
            video_url = content.get("video_url")
        elif isinstance(content, list):
            # 兼容数组格式
            for item in content:
                if isinstance(item, dict) and item.get("type") == "video_url":
                    video_url = item.get("video_url", {}).get("url")
                    break

        if not video_url:
            raise RuntimeError("任务完成但无视频 URL")

        logger.info(f"Seedance 视频下载中: {video_url[:100]}...")

        client = get_http_client()
        resp = await client.get(video_url, timeout=120)
        resp.raise_for_status()
        return resp.content
