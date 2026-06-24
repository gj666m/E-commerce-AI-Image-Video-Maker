# Agent 工具 - 包装现有 Provider/prompt_engine/history_store
# Phase 1 只实现：generate_quick_image + list_available_models
# 后续 Phase 4 补全 outfit/model/seed_grass/product_main/aplus + analyze_product
import logging
import time
from typing import Optional

from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from app.agents.image_store import image_store
from app.services.model_router import get_provider, get_available_providers, get_models_list
from app.services.prompt_engine import build_quick_prompt
from app.services.postprocess import apply_realistic_filter
from app.services.image_utils import image_to_base64
from app.services.history_store import save_history

logger = logging.getLogger(__name__)


def _aspect_to_size(aspect_ratio: str) -> str:
    """宽高比 → Seedream size 档位（复用 generate.py 同款映射）"""
    size_map = {
        "1:1": "2k",
        "3:4": "2k",
        "4:3": "2k",
        "4:5": "2k",
        "9:16": "2k",
        "16:9": "2k",
        "61:25": "4k",
    }
    return size_map.get(aspect_ratio, "4k")


VALID_ASPECT_RATIOS = ["1:1", "3:4", "4:3", "4:5", "9:16", "16:9", "61:25"]


@tool
async def generate_quick_image(
    description: str,
    aspect_ratio: str = "1:1",
    model_name: Optional[str] = None,
    reference_image_ids: Optional[list[str]] = None,
    config: RunnableConfig = None,
) -> str:
    """快速生成一张电商图片。用户描述原样透传为生图 prompt，不走任何模板。

    Args:
        description: 用户对要生成图片的画面描述（中文或英文均可，尽量具体）。
        aspect_ratio: 宽高比。可选值：1:1 / 3:4 / 4:3 / 4:5 / 9:16 / 16:9 / 61:25。默认 1:1。
        model_name: 指定生图模型，可选：seedream5 / volcengine / gptimage / gptimage_vip / nanobanana。
                    不确定时留空（null），走自动路由。用户指定时优先用用户指定的。
        reference_image_ids: 参考图的 image_id 列表（最多 6 张），从用户上传图中选取。无参考图则留空。
    Returns:
        生成结果摘要（成功/失败 + image_id + 使用的模型），图片本身通过 SSE 单独推送。
    """
    # 从 config 拿 user_id / thread_id
    configurable = (config or {}).get("configurable", {})
    user_id = configurable.get("user_id", 0)
    thread_id = configurable.get("thread_id", "default")

    # 参数校验
    if aspect_ratio not in VALID_ASPECT_RATIOS:
        aspect_ratio = "1:1"
    if reference_image_ids is None:
        reference_image_ids = []
    if len(reference_image_ids) > 6:
        reference_image_ids = reference_image_ids[:6]

    # 拼 prompt
    prompt = build_quick_prompt(description=description, aspect_ratio=aspect_ratio)

    # 模型路由（用户指定优先，校验白名单）
    providers = get_available_providers()
    chosen = model_name if (model_name and model_name in providers and model_name != "mock") else None
    provider = get_provider("quick", chosen)
    logger.info(f"[agent] generate_quick_image: model={provider.name}, ratio={aspect_ratio}, refs={len(reference_image_ids)}")

    # 取参考图
    ref_images: list[bytes] = []
    if reference_image_ids:
        ref_images = await image_store.get_many(reference_image_ids)

    # 尺寸
    size = _aspect_to_size(aspect_ratio)

    try:
        gen_kwargs = {}
        if ref_images:
            gen_kwargs["images"] = ref_images
        t_gen = time.perf_counter()
        result = await provider.generate(prompt, params={"size": size, "aspect_ratio": aspect_ratio}, **gen_kwargs)
        logger.info(f"[agent] generate_quick_image 完成 model={provider.name} ratio={aspect_ratio} refs={len(ref_images)} cost={time.perf_counter() - t_gen:.2f}s")
    except Exception as e:
        logger.error(f"[agent] 生图异常: {e}", exc_info=True)
        return f"❌ 生图失败：{e}"

    if not result.success or not result.images:
        return f"❌ 生图失败：{result.error or '未知错误'}"

    # 取第一张（Agent 一次生一张）
    img = result.images[0]
    processed = apply_realistic_filter(img, intensity="light")

    # 存 ImageStore（生成图前缀 gen_）
    image_id = await image_store.put(
        processed,
        thread_id=thread_id,
        mime="image/jpeg",
        filename=f"agent_gen.jpeg",
        prefix="gen",
    )

    # 存历史（失败不影响主流程）
    per_cost = result.cost / max(1, len(result.images))
    try:
        await save_history(
            user_id=user_id,
            task_type="quick",
            prompt=prompt,
            params={
                "description": description,
                "aspect_ratio": aspect_ratio,
                "model_name": provider.name,
                "source": "agent",
            },
            model_used=provider.name,
            image_bytes=processed,
            cost=per_cost,
            currency=result.currency,
        )
    except Exception as e:
        logger.warning(f"[agent] 存历史失败（不影响主流程）: {e}")

    # 把生成图元信息塞进 config metadata，runner 从 state 提取后单独走 SSE 推送 data_url
    # 这里给 ToolMessage 返回文字摘要（避免把 base64 塞进 Claude 上下文）
    data_url = f"data:image/jpeg;base64,{image_to_base64(processed)}"
    gen_meta = {
        "image_id": image_id,
        "data_url": data_url,
        "prompt_used": prompt,
        "model_used": provider.name,
        "cost": per_cost,
        "currency": result.currency,
        "aspect_ratio": aspect_ratio,
    }
    # 通过 config configurable 回传生成图元信息（runner 侧聚合）
    meta_bag = configurable.setdefault("_generated_images", [])
    meta_bag.append(gen_meta)

    return f"✅ 成功生成 1 张图片（model={provider.name}, {aspect_ratio}, 费用 {per_cost:.4f} {result.currency}/张）。image_id={image_id}。"


@tool
async def list_available_models(config: RunnableConfig = None) -> str:
    """查询当前实际可用的生图模型列表。选模型前可调用此工具确认哪些模型已配置 API Key。

    Returns:
        可用模型清单文本（含 model_name、显示名、单价、特性）。
    """
    models = get_models_list()
    lines = []
    for m in models:
        if m["name"] == "mock":
            continue
        if not m.get("available"):
            continue
        lines.append(f"- {m['name']}：{m['display_name']}（{m.get('description', '')}）")
    if not lines:
        return "当前没有可用的生图模型（均为 mock 模式）。"
    return "当前可用的生图模型：\n" + "\n".join(lines)


# Phase 1 工具清单
ALL_TOOLS = [generate_quick_image, list_available_models]
