# 视频生成 Provider 抽象基类
# 与图片 Provider 不同，视频生成是异步模式：提交→轮询→取结果
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class VideoTask:
    """视频生成任务状态"""
    task_id: str
    status: str = "pending"       # pending / processing / completed / failed
    progress: int = 0             # 0-100
    video_url: str | None = None  # 完成后的视频访问 URL
    cost: float = 0.0
    error: str | None = None
    prompt_used: str = ""
    model_used: str = ""
    meta: dict = field(default_factory=dict)


class VideoProvider(ABC):
    """视频生成 Provider 抽象基类

    视频生成是异步流程：
    1. submit() 提交任务，返回外部任务 ID
    2. poll() 查询任务状态和进度
    3. get_result() 获取生成的视频二进制
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider 名称"""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Provider 是否可用（API Key 已配置）"""
        pass

    @abstractmethod
    async def submit(
        self,
        prompt: str,
        image: bytes | None = None,
        extra_images: list[bytes] | None = None,
        params: dict | None = None,
    ) -> str:
        """提交视频生成任务

        Args:
            prompt: 视频生成 Prompt
            image: 主参考图片（商品图/素材图）
            extra_images: 附加参考图（最多5张，加上主图共最多6张）
            params: 额外参数（时长、分辨率等）

        Returns:
            外部任务 ID，用于后续 poll/get_result
        """
        pass

    @abstractmethod
    async def poll(self, external_task_id: str) -> VideoTask:
        """查询任务状态

        Args:
            external_task_id: submit() 返回的任务 ID

        Returns:
            当前任务状态
        """
        pass

    @abstractmethod
    async def get_result(self, external_task_id: str) -> bytes:
        """获取生成的视频二进制

        Args:
            external_task_id: submit() 返回的任务 ID

        Returns:
            视频文件的二进制内容

        Raises:
            RuntimeError: 任务未完成或失败时
        """
        pass
