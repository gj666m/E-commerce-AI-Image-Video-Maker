# 模型路由 - 根据任务类型选择 Provider
from app.config import settings
from app.providers.base import BaseProvider
from app.providers.mock_provider import MockProvider
from app.providers.openai_provider import OpenAIProvider
from app.providers.fal_provider import FalProvider
from app.providers.volcengine_provider import VolcengineProvider
from app.providers.nanobanana_provider import NanoBananaProvider
from app.providers.gptimage_provider import GPTImageProvider


def get_available_providers() -> dict[str, BaseProvider]:
    """获取所有可用的 Provider 实例"""
    providers: dict[str, BaseProvider] = {
        "mock": MockProvider(),
    }
    if settings.has_openai:
        providers["openai"] = OpenAIProvider()
    if settings.has_fal:
        providers["fal"] = FalProvider()
    if settings.has_volcengine:
        providers["volcengine"] = VolcengineProvider()
    if settings.has_nanobanana:
        providers["nanobanana"] = NanoBananaProvider()
    if settings.has_gptimage:
        providers["gptimage"] = GPTImageProvider()
    return providers


def get_provider(
    task_type: str,
    model_name: str | None = None,
) -> BaseProvider:
    """根据任务类型和用户指定模型获取 Provider

    Args:
        task_type: 任务类型（material_scene / background）
        model_name: 用户指定的模型名，None 则自动路由

    Returns:
        Provider 实例
    """
    providers = get_available_providers()

    # 用户指定了模型
    if model_name and model_name in providers:
        return providers[model_name]

    # 自动路由：优先真实 Provider
    # volcengine > gptimage > nanobanana > OpenAI > fal > mock
    if settings.has_volcengine:
        return providers["volcengine"]
    if settings.has_gptimage:
        return providers["gptimage"]
    if settings.has_nanobanana:
        return providers["nanobanana"]
    if settings.has_openai:
        return providers["openai"]
    if settings.has_fal:
        return providers["fal"]

    return providers["mock"]


# 模型元信息注册表
_MODEL_META = {
    "mock": {
        "display_name": "Mock（测试模式）",
        "description": "无 API Key 时使用，返回占位图",
        "capabilities": ["text_to_image"],
        "api_key_hint": "无需 Key",
    },
    "openai": {
        "display_name": "GPT-Image-2（OpenAI）",
        "description": "OpenAI 生图模型，高质量，支持文生图和图生图",
        "capabilities": ["text_to_image", "image_to_image"],
        "api_key_hint": "OPENAI_API_KEY",
    },
    "fal": {
        "display_name": "FLUX（fal.ai）",
        "description": "FLUX 模型，队列模式，支持多种风格",
        "capabilities": ["text_to_image", "image_to_image"],
        "api_key_hint": "FAL_API_KEY",
    },
    "volcengine": {
        "display_name": "Seedream（火山方舟）",
        "description": "豆包 Seedream 图片生成模型，支持文生图和参考图生图",
        "capabilities": ["text_to_image", "image_to_image"],
        "api_key_hint": "VOLCENGINE_API_KEY",
    },
    "nanobanana": {
        "display_name": "Nano Banana 2（Gemini）",
        "description": "Google Gemini 图片生成模型，高质量文生图和图生图，通过 API易中转站调用",
        "capabilities": ["text_to_image", "image_to_image"],
        "api_key_hint": "NANOBANANA_API_KEY",
    },
    "gptimage": {
        "display_name": "GPT-Image-2（OpenAI）",
        "description": "OpenAI GPT 图片生成模型，$0.03/张，文字还原度高，中文提示词友好，支持多图融合",
        "capabilities": ["text_to_image", "image_to_image"],
        "api_key_hint": "GPTIMAGE_API_KEY",
    },
}


def get_models_list() -> list[dict]:
    """返回可用模型列表（供前端展示）"""
    providers = get_available_providers()
    models = []
    for name, provider in providers.items():
        meta = _MODEL_META.get(name, {})
        models.append({
            "name": name,
            "display_name": meta.get("display_name", name),
            "available": provider.is_available,
            "description": meta.get("description", ""),
            "capabilities": meta.get("capabilities", []),
            "api_key_hint": meta.get("api_key_hint", ""),
        })
    return models
