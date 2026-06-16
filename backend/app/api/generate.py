# 核心生成接口
import asyncio
import base64
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.deps import get_current_user
from app.services.image_utils import compress_image, image_to_base64, get_image_info
from app.services.model_router import get_provider
from app.services.postprocess import apply_realistic_filter
from app.services.prompt_engine import build_prompt, build_seed_grass_prompt, build_product_main_prompt, build_aplus_prompt, build_quick_prompt

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["generate"])


@router.post("/generate")
async def generate(
    current_user=Depends(get_current_user),
    task_type: str = Form(..., description="任务类型: outfit / product_video 等"),
    image: UploadFile | None = File(None, description="商品图（场景图时需要）"),
    images: list[UploadFile] = File(default=[], description="多张参考图（composite 模式：图1=模特，图2=商品，图3=场景...）"),
    description: str = Form(..., description="场景描述或商品描述"),
    style: str | None = Form(None, description="风格偏好"),
    model_name: str | None = Form(None, description="指定模型，None 则自动路由"),
    aspect_ratio: str = Form("1:1", description="宽高比: 1:1 / 16:9 / 9:16"),
    custom_prompt: str | None = Form(None, description="用户自定义 Prompt 补充"),
    enable_analysis: bool = Form(False, description="是否启用智能分析（P7 功能，暂未实现）"),
    count: int = Form(1, description="生成数量（1-4 张）"),
    product_info: str | None = Form(None, description="商品信息文本（用户输入或AI分析，可选）"),
    # 种草图专用参数
    persona: str | None = Form(None, description="博主人设描述（种草图专用）"),
    scene: str | None = Form(None, description="场景描述（种草图专用，优先于 description）"),
    # A+ 图专用参数
    selling_point: str | None = Form(None, description="核心卖点（A+ 图专用）"),
    headline: str | None = Form(None, description="标题文字（A+ 图专用）"),
    body_text: str | None = Form(None, description="正文文字（A+ 图专用）"),
    layout: str | None = Form(None, description="布局类型（A+ 图专用）"),
):
    """核心生成接口

    流程：接收参数 → 图片压缩 → Prompt 拼装 → 模型路由 → 调用生图 → 返回结果

    多图模式（composite）：上传多张参考图，prompt 中用"图1""图2""图3"引用
    多张生成（count）：并行调用 Provider，生成多张供挑选
    种草图模式（seed_grass）：persona + scene 参数拼入专用模板
    """
    # 参数校验
    valid_task_types = {"quick", "outfit", "product_video", "seed_grass", "product_main", "aplus", "model_gen", "model_ref"}
    if task_type not in valid_task_types:
        raise HTTPException(400, f"无效的任务类型: {task_type}，支持: {', '.join(sorted(valid_task_types))}")

    count = max(1, min(count, 4))

    valid_ratios = {"1:1", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "61:25"}
    if aspect_ratio not in valid_ratios:
        raise HTTPException(400, f"无效的比例: {aspect_ratio}，支持: {', '.join(sorted(valid_ratios))}")

    if not description or not description.strip():
        raise HTTPException(400, "描述不能为空")

    # 1. 图片处理
    image_bytes: bytes | None = None
    multi_image_bytes: list[bytes] = []
    image_info: dict | None = None

    if image:
        raw = await image.read()
        if len(raw) > 20 * 1024 * 1024:
            raise HTTPException(400, "图片大小不能超过 20MB")
        image_bytes = compress_image(raw)
        image_info = get_image_info(image_bytes)
        logger.info(f"图片已压缩: {image_info}")

    # 多图处理：并行压缩，避免阻塞事件循环
    raw_images = []
    for img_file in images:
        raw = await img_file.read()
        if len(raw) > 20 * 1024 * 1024:
            raise HTTPException(400, f"图片 {img_file.filename} 大小不能超过 20MB")
        raw_images.append(raw)

    if raw_images:
        multi_image_bytes = await asyncio.gather(
            *[asyncio.to_thread(compress_image, raw) for raw in raw_images]
        )
        multi_image_bytes = list(multi_image_bytes)
        for img_file, compressed in zip(images, multi_image_bytes):
            logger.info(f"多图上传: {img_file.filename}, 压缩后 {len(compressed)} bytes")

    if multi_image_bytes and not image_info:
        image_info = get_image_info(multi_image_bytes[0])

    # 2. Prompt 拼装
    if task_type == "quick":
        # 快速生图：不走任何模板，用户描述原样透传 + 比例前缀
        prompt = build_quick_prompt(description=description, aspect_ratio=aspect_ratio)
    elif task_type == "seed_grass":
        prompt = build_seed_grass_prompt(
            description=description,
            persona=persona,
            scene=scene,
            style=style,
            aspect_ratio=aspect_ratio,
            user_custom=custom_prompt,
            product_info_text=product_info,
        )
    elif task_type == "product_main":
        prompt = build_product_main_prompt(
            description=description,
            user_custom=custom_prompt,
            product_info_text=product_info,
        )
    elif task_type == "aplus":
        prompt = build_aplus_prompt(
            selling_point=selling_point or "",
            headline=headline or "",
            body_text=body_text or "",
            layout=layout or "left_image_right_text",
            scene=description,
            style=style,
            aspect_ratio=aspect_ratio,
            user_custom=custom_prompt,
            product_info_text=product_info,
        )
    else:
        prompt = build_prompt(
            task_type=task_type,
            description=description,
            style=style,
            aspect_ratio=aspect_ratio,
            user_custom=custom_prompt,
            product_info_text=product_info,
        )
    logger.info(f"Prompt 拼装完成，长度: {len(prompt)}")

    # 3. 模型路由
    provider = get_provider(task_type, model_name)
    logger.info(f"使用模型: {provider.name}，数量: {count}")

    # 4. 尺寸参数
    size = _aspect_to_size(aspect_ratio)

    # 5. 并行调用生图（单张失败不影响其他）
    gen_kwargs = {"images": multi_image_bytes} if multi_image_bytes else {"image": image_bytes}
    tasks = [provider.generate(prompt, **gen_kwargs, params={"size": size, "aspect_ratio": aspect_ratio}) for _ in range(count)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 6. 收集结果（自动后处理，单张失败不影响其他）
    all_images_b64: list[str] = []
    total_cost = 0.0
    currency = "¥"
    first_error = None
    # 单张成本（用于历史记录）
    per_cost = 0.0
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            logger.error(f"第 {i+1} 张生成异常: {r}")
            if not first_error:
                first_error = str(r)
            continue
        if r.success and r.images:
            per_cost = r.cost / max(1, len(r.images))
            for img in r.images:
                # 自动后处理：轻微颗粒+色调调整，提升真实感
                processed = apply_realistic_filter(img, intensity="light")
                all_images_b64.append(image_to_base64(processed))
                # 落盘到历史（失败不影响主流程）
                from app.services.history_store import save_history
                history_params = {
                    "description": description,
                    "style": style,
                    "aspect_ratio": aspect_ratio,
                    "model_name": model_name,
                    "count": count,
                }
                await save_history(
                    user_id=current_user["id"],
                    task_type=task_type,
                    prompt=prompt,
                    params=history_params,
                    model_used=provider.name,
                    image_bytes=processed,
                    cost=per_cost,
                    currency=r.currency,
                )
            total_cost += r.cost
            currency = r.currency  # 同一批次用同一 provider，取最后一个即可
        else:
            logger.warning(f"第 {i+1} 张生成失败: {r.error}")
            if not first_error:
                first_error = r.error or "未知错误"

    if not all_images_b64:
        raise HTTPException(500, first_error or "全部生成失败，请稍后重试")

    return {
        "success": True,
        "images": all_images_b64,
        "prompt_used": prompt,
        "model_used": provider.name,
        "cost": total_cost,
        "currency": currency,
        "image_info": image_info,
    }


def _aspect_to_size(aspect_ratio: str) -> str:
    """宽高比转尺寸参数（Seedream 用质量级别，实际比例由 prompt 控制）"""
    size_map = {
        "1:1": "4k",
        "3:4": "4k",
        "4:3": "4k",
        "4:5": "4k",
        "5:4": "4k",
        "9:16": "4k",
        "16:9": "4k",
        "61:25": "4k",
    }
    return size_map.get(aspect_ratio, "4k")
