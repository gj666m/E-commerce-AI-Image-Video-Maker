# Mock 视频生成 Provider - 无 API Key 时模拟异步视频生成流程
import asyncio
import io
import math
import textwrap
import uuid
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

from app.providers.video_base import VideoProvider, VideoTask


class MockVideoProvider(VideoProvider):
    """Mock 视频生成 Provider

    模拟异步流程：
    - submit() 创建任务，初始化进度
    - poll() 每次调用推进进度（0→30→60→100）
    - get_result() 生成占位 GIF 视频帧
    """

    # 内存任务表 {external_task_id: VideoTask}
    _tasks: dict[str, VideoTask] = {}

    # 进度阶梯（每次 poll 推进一步）
    _PROGRESS_STEPS = [0, 30, 60, 100]

    @property
    def name(self) -> str:
        return "mock_video"

    @property
    def is_available(self) -> bool:
        return True  # Mock 始终可用

    async def submit(
        self,
        prompt: str,
        image: bytes | None = None,
        extra_images: list[bytes] | None = None,
        params: dict | None = None,
    ) -> str:
        task_id = uuid.uuid4().hex[:12]
        params = params or {}

        task = VideoTask(
            task_id=task_id,
            status="processing",
            progress=0,
            prompt_used=prompt,
            model_used=self.name,
            meta={
                "poll_count": 0,
                "duration": params.get("duration", 5),
                "has_image": image is not None,
            },
        )
        self._tasks[task_id] = task
        return task_id

    async def poll(self, external_task_id: str) -> VideoTask:
        task = self._tasks.get(external_task_id)
        if not task:
            return VideoTask(
                task_id=external_task_id,
                status="failed",
                error="任务不存在",
            )

        # 推进进度
        poll_count = task.meta.get("poll_count", 0) + 1
        task.meta["poll_count"] = poll_count

        step_index = min(poll_count, len(self._PROGRESS_STEPS) - 1)
        task.progress = self._PROGRESS_STEPS[step_index]

        if task.progress >= 100:
            task.status = "completed"
        else:
            task.status = "processing"

        return task

    async def get_result(self, external_task_id: str) -> bytes:
        task = self._tasks.get(external_task_id)
        if not task or task.status != "completed":
            raise RuntimeError("任务未完成或不存在")

        # 生成占位 GIF（模拟视频）
        return self._generate_mock_gif(task)

    def _generate_mock_gif(self, task: VideoTask) -> bytes:
        """生成占位 GIF 作为模拟视频"""
        duration = task.meta.get("duration", 5)
        frames = []
        num_frames = min(duration * 2, 12)  # 每秒 2 帧，最多 12 帧

        for i in range(num_frames):
            frame = self._create_frame(i, num_frames, task.prompt_used, duration)
            frames.append(frame)

        buf = io.BytesIO()
        frames[0].save(
            buf,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=500,  # 每帧 500ms
            loop=0,
        )
        return buf.getvalue()

    def _create_frame(
        self, frame_index: int, total_frames: int, prompt: str, duration: int,
    ) -> Image.Image:
        """生成单帧图片"""
        width, height = 640, 360
        img = Image.new("RGB", (width, height), color=(30, 30, 50))
        draw = ImageDraw.Draw(img)

        # 进度动画背景色变化
        progress = int((frame_index / max(total_frames - 1, 1)) * 100)
        bar_width = int(width * 0.6 * (progress / 100))
        draw.rectangle(
            [width * 0.2, height * 0.65, width * 0.2 + bar_width, height * 0.72],
            fill=(80, 180, 120),
        )
        # 进度条背景
        draw.rectangle(
            [width * 0.2, height * 0.65, width * 0.8, height * 0.72],
            outline=(100, 100, 120),
            width=1,
        )

        # 标题
        self._draw_text(draw, "[MOCK] AI Generated Video", width, height * 0.2, size=22, fill=(200, 200, 220))
        self._draw_text(draw, f"Duration: {duration}s | Frame: {frame_index+1}/{total_frames}", width, height * 0.35, size=14, fill=(150, 150, 170))

        # Prompt 摘要
        display = prompt[:120] + ("..." if len(prompt) > 120 else "")
        wrapped = textwrap.fill(display, width=45)
        self._draw_text(draw, wrapped, width, height * 0.48, size=12, fill=(130, 130, 160))

        # 进度文字
        self._draw_text(draw, f"Progress: {progress}%", width, height * 0.8, size=16, fill=(100, 200, 140))

        return img

    def _draw_text(
        self, draw: ImageDraw.Draw, text: str, canvas_w: int, y: float,
        size: int = 16, fill: tuple = (200, 200, 200),
    ):
        """居中绘制文字"""
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
        except (OSError, IOError):
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        x = (canvas_w - text_w) / 2
        draw.text((x, y), text, font=font, fill=fill, align="center")
