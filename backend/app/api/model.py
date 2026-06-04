# 模特生成与管理 API
import asyncio
import base64
import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.services.model_router import get_provider
from app.services.model_store import save_model, list_models, delete_model
from app.services.postprocess import apply_realistic_filter
from app.services.prompt_engine import build_model_prompt

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/model", tags=["model"])


# ---- 请求模型 ----

class ModelSaveRequest(BaseModel):
    """模特保存请求"""
    name: str = Field(..., description="模特名称")
    params: dict = Field(..., description="生成参数")
    image_data: str = Field(..., description="模特图 base64")


# ---- API 端点 ----

@router.post("/generate")
async def generate_model(
    gender: str = Form("female"),
    ethnicity: str = Form("caucasian"),
    age: str = Form("25-30"),
    body_type: str = Form("standard"),
    hair_desc: str = Form(""),
    expression: str = Form(""),
    pose: str = Form(""),
    clothing: str = Form(""),
    background: str = Form("white"),
    composition: str = Form("full_body"),
    style: str = Form("ecommerce"),
    custom_desc: str = Form(""),
    count: int = Form(1, description="生成数量（1-4 张）"),
    aspect_ratio: str = Form("1:1", description="宽高比: 1:1 / 3:4 / 4:3 / 4:5 / 9:16 / 16:9"),
    image: UploadFile | None = File(None, description="参考图片（单张，图生图模式）"),
    images: list[UploadFile] = File(default=[], description="多张参考图片（图生图模式，最多3张）"),
):
    """生成预设模特图

    两种模式：
    - 文生图：不传 image/images，纯参数生成
    - 图生图：传 image 或 images 参考图，基于参考图做变体
    """
    from app.services.image_utils import compress_image

    # 1. 收集参考图（images 优先，兼容 image）
    ref_images: list[bytes] = []
    for img_file in images:
        raw = await img_file.read()
        ref_images.append(compress_image(raw))
        logger.info(f"参考图已上传: {img_file.filename}, {len(raw)} bytes")
    if not ref_images and image:
        raw = await image.read()
        ref_images.append(compress_image(raw))
        logger.info(f"参考图已上传（单张）: {len(raw)} bytes")

    has_ref = len(ref_images) > 0

    # 2. 拼装 prompt
    prompt = build_model_prompt(
        gender=gender,
        ethnicity=ethnicity,
        age=age,
        body_type=body_type,
        hair_desc=hair_desc,
        background=background,
        composition=composition,
        style=style,
        expression=expression,
        pose=pose,
        clothing=clothing,
        custom_desc=custom_desc,
        has_reference_image=has_ref,
    )
    count = max(1, min(count, 4))
    logger.info(f"模特生成 prompt ({'图生图' if has_ref else '文生图'}), 参考图: {len(ref_images)} 张, 数量: {count}")

    # 3. 并行调用 Seedream 生成多张
    provider = get_provider("model_gen", model_name="volcengine")
    from app.services.prompt_engine import _aspect_to_resolution
    ratio_desc = _aspect_to_resolution(aspect_ratio)
    if ratio_desc and ratio_desc not in prompt:
        prompt += f"\n构图比例：{ratio_desc}"

    # 传参考图：单张用 image，多张用 images
    gen_kwargs = {"images": ref_images} if len(ref_images) > 1 else {"image": ref_images[0]} if ref_images else {}
    tasks = [provider.generate(prompt, **gen_kwargs, params={"size": "4k"}) for _ in range(count)]
    results = await asyncio.gather(*tasks)

    # 4. 收集成功的图片（自动后处理）
    images_b64 = []
    total_cost = 0.0
    for r in results:
        if r.success and r.images:
            # 自动后处理：轻微颗粒+色调调整
            processed = apply_realistic_filter(r.images[0], intensity="light")
            images_b64.append(base64.b64encode(processed).decode("utf-8"))
            total_cost += r.cost
        else:
            logger.warning(f"某张生成失败: {r.error}")

    if not images_b64:
        raise HTTPException(500, "全部生成失败，请稍后重试")

    return {
        "success": True,
        "images": images_b64,
        "prompt_used": prompt,
        "model_used": provider.name,
        "cost": total_cost,
    }


@router.post("/save")
async def save_model_to_library(req: ModelSaveRequest):
    """保存模特到模特库"""
    image_bytes = base64.b64decode(req.image_data)
    record = save_model(req.name, req.params, image_bytes)
    return {"success": True, "model_id": record["id"]}


@router.get("/list")
async def get_model_list():
    """获取模特库列表"""
    models = list_models()
    return {"success": True, "models": models}


@router.delete("/{model_id}")
async def delete_model_from_library(model_id: str):
    """删除模特"""
    ok = delete_model(model_id)
    if not ok:
        raise HTTPException(404, f"模特 {model_id} 不存在")
    return {"success": True}
