# Provider 抽象基类
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

# 429 限流/额度不足的统一提示
RATE_LIMIT_MSG = "模型额度不足或已限流，请联系管理员续费或切换其他模型重试"


def http_error_message(status_code: int, detail: str, provider_name: str) -> str:
    """根据 HTTP 状态码返回用户友好的错误消息"""
    if status_code == 429:
        return RATE_LIMIT_MSG
    if status_code == 403:
        return f"内容审核未通过，请修改描述或参考图后重试"
    return f"{provider_name} API 错误: {status_code} - {detail}"


@dataclass
class GenerateResult:
    """模型生成结果"""
    success: bool
    images: list[bytes] = field(default_factory=list)
    cost: float = 0.0
    currency: str = "¥"  # 费用币种：¥ 人民币 / $ 美元
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
