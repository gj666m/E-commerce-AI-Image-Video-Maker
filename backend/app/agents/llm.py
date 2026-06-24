# Claude 客户端 - langchain-anthropic ChatAnthropic 指向 API易中转
import logging

from langchain_anthropic import ChatAnthropic

from app.config import settings

logger = logging.getLogger(__name__)

_llm: ChatAnthropic | None = None


def get_llm() -> ChatAnthropic:
    """ChatAnthropic 单例（指向 API易 Anthropic 原生端点）

    用 langchain-anthropic 而非原生 SDK：LangGraph 的 astream_events 原生追踪 token 流，
    bind_tools 开箱即用。API易是纯官转，完整支持 Anthropic 流式协议 + prompt caching。
    """
    global _llm
    if _llm is None:
        _llm = ChatAnthropic(
            model=settings.claude_apiyi_model,
            api_key=settings.claude_apiyi_api_key,
            base_url=settings.claude_apiyi_base_url,
            max_tokens=4096,
            temperature=0.7,
            timeout=settings.agent_request_timeout,
            max_retries=2,
        )
        logger.info(f"ChatAnthropic 初始化: model={settings.claude_apiyi_model}, base_url={settings.claude_apiyi_base_url}")
    return _llm


def reset_llm() -> None:
    """重置单例（配置变更时用，运行时一般不调）"""
    global _llm
    _llm = None
