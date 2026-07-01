# Seedance 2.0 Mini 视频生成 Provider - 火山官网直连
# 与 SeedanceVideoProvider 完全相同的 API 格式，区别：
# - Model: doubao-seedance-2-0-mini-260615（半价版本）
# - Auth: API Key 直接作 Bearer（非 endpoint ID）
# - 不走 API易中转，不参与 API易 余额计费 → cost 字段置 0（历史页 v-if 不渲染）
from app.config import settings
from app.providers.seedance_provider import SeedanceVideoProvider


class SeedanceMiniVideoProvider(SeedanceVideoProvider):
    """字节跳动 Seedance 2.0 Mini 视频生成 Provider（火山官网直连）

    API 格式与 SeedanceVideoProvider 完全一致，区别仅在 Model 与 Auth：
    - Model：doubao-seedance-2-0-mini-260615（半价）
    - Auth：API Key 直接作 Bearer（不走中转，不需要 endpoint ID）
    - 计费：COST_PER_MILLION_TOKENS=0 → cost 字段不记录
      （官网扣款走火山账户另算，不参与 API易 余额体系）
    """

    MODEL = "doubao-seedance-2-0-mini-260615"
    COST_PER_MILLION_TOKENS = 0.0  # 不计费：不参与 API易 余额，cost 字段始终 0

    @property
    def name(self) -> str:
        return "seedance_mini"

    @property
    def is_available(self) -> bool:
        return bool(settings.seedance_mini_api_key)

    def _get_auth_token(self) -> str:
        """返回官网 API Key（直接作 Bearer）"""
        return settings.seedance_mini_api_key
