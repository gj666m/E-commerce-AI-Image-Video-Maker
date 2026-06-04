# Provider 抽象基类
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class GenerateResult:
    """模型生成结果"""
    success: bool
    images: list[bytes] = field(default_factory=list)
    cost: float = 0.0
    raw_response: dict = field(default_factory=dict)
    error: str | None = None


class BaseProvider(ABC):
    """AI 模型 Provider 抽象基类"""

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
    async def generate(
        self,
        prompt: str,
        image: bytes | None = None,
        images: list[bytes] | None = None,
        params: dict | None = None,
    ) -> GenerateResult:
        """调用模型生成

        Args:
            prompt: 生图 Prompt
            image: 参考图片（单张，图生图时传入）
            images: 多张参考图片（多图生图时传入，如模特图+商品图）
            params: 额外参数（尺寸、数量等）
        """
        pass
