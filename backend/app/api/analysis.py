# 商品视觉分析接口
import json
import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from typing import List

from app.providers.deepseek_provider import ProductAnalysisProvider
from app.services.image_utils import compress_image, get_image_info

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["analysis"])

# 全局单例
_provider = ProductAnalysisProvider()


@router.post("/analyze")
async def analyze(
    image: UploadFile = File(..., description="商品图片"),
    extra_prompt: str | None = Form(None, description="用户额外提示（可选）"),
    existing_info: str | None = Form(None, description="用户已填写的商品信息 JSON（可选）"),
):
    """商品视觉分析接口

    上传商品图片 → 豆包视觉模型分析 → 返回结构化商品信息
    支持 existing_info 参数，AI 会在此基础上优化补全
    """
    # 1. 读取并压缩图片
    raw = await image.read()
    if len(raw) > 20 * 1024 * 1024:
        raise HTTPException(400, "图片大小不能超过 20MB")

    image_bytes = compress_image(raw)
    image_info = get_image_info(image_bytes)
    logger.info(f"分析请求: {image_info}")

    # 解析已有信息
    parsed_existing = None
    if existing_info:
        try:
            parsed_existing = json.loads(existing_info)
        except json.JSONDecodeError:
            raise HTTPException(400, "existing_info 格式错误，需要 JSON 字符串")

    # 推断 MIME 类型
    mime_type = image.content_type or "image/jpeg"

    # 2. 调用分析 Provider
    try:
        result = await _provider.analyze(image_bytes, mime_type, extra_prompt, parsed_existing)
    except RuntimeError as e:
        logger.error(f"分析失败: {e}")
        raise HTTPException(500, str(e))

    return {
        "success": True,
        "analysis": result,
        "image_info": image_info,
    }


@router.post("/analyze-persona")
async def analyze_persona(
    image: UploadFile = File(..., description="博主照片"),
):
    """博主人设分析接口

    上传博主照片 → 豆包视觉模型分析 → 返回结构化人设信息
    """
    raw = await image.read()
    if len(raw) > 20 * 1024 * 1024:
        raise HTTPException(400, "图片大小不能超过 20MB")

    image_bytes = compress_image(raw)
    image_info = get_image_info(image_bytes)
    logger.info(f"人设分析请求: {image_info}")

    mime_type = image.content_type or "image/jpeg"

    try:
        result = await _provider.analyze_persona(image_bytes, mime_type)
    except RuntimeError as e:
        logger.error(f"人设分析失败: {e}")
        raise HTTPException(500, str(e))

    return {
        "success": True,
        "persona": result,
        "image_info": image_info,
    }


@router.post("/plan-shots")
async def plan_shots(
    images: List[UploadFile] = File(..., description="商品图片（1-6张）"),
    product_info: str | None = Form(None, description="商品信息文本（可选）"),
    persona: str | None = Form(None, description="博主人设描述（可选）"),
):
    """AI 种草图策划接口

    上传商品图片 → 豆包视觉模型策划 → 返回 4-6 张种草图方案
    """
    if len(images) < 1 or len(images) > 6:
        raise HTTPException(400, "商品图片数量需要 1-6 张")

    # 读取并压缩所有图片
    img_list = []
    for img in images:
        raw = await img.read()
        if len(raw) > 20 * 1024 * 1024:
            raise HTTPException(400, f"图片 {img.filename} 大小不能超过 20MB")
        compressed = compress_image(raw)
        mime_type = img.content_type or "image/jpeg"
        img_list.append((compressed, mime_type))

    logger.info(f"策划请求: {len(img_list)} 张图片")

    try:
        result = await _provider.plan_shots(
            img_list,
            product_info or "",
            persona or "",
        )
    except RuntimeError as e:
        logger.error(f"AI 策划失败: {e}")
        raise HTTPException(500, str(e))

    return {
        "success": True,
        "plans": result.get("plans", []),
        "_meta": result.get("_meta", {}),
    }


@router.post("/recommend-styles")
async def recommend_styles(
    plans: str = Form(..., description="策划方案 JSON 字符串"),
    product_info: str | None = Form(None, description="商品信息文本（可选）"),
    persona: str | None = Form(None, description="博主人设描述（可选）"),
):
    """AI 风格推荐接口

    根据策划方案 + 商品信息 + 人设 → 推荐 3-4 种视觉风格方向
    """
    try:
        parsed_plans = json.loads(plans)
    except json.JSONDecodeError:
        raise HTTPException(400, "plans 格式错误，需要 JSON 字符串")

    if not parsed_plans or not isinstance(parsed_plans, list):
        raise HTTPException(400, "plans 不能为空")

    logger.info(f"风格推荐请求: {len(parsed_plans)} 个方案")

    try:
        result = await _provider.recommend_styles(
            parsed_plans,
            product_info or "",
            persona or "",
        )
    except RuntimeError as e:
        logger.error(f"风格推荐失败: {e}")
        raise HTTPException(500, str(e))

    return {
        "success": True,
        "styles": result.get("styles", []),
        "_meta": result.get("_meta", {}),
    }


@router.post("/analyze-free")
async def analyze_free(
    image: UploadFile = File(..., description="图片"),
    prompt: str = Form(..., description="自由文本提示词"),
):
    """自由文本查询接口

    图片 + 提示词 → 纯文本回复（不走结构化 JSON）
    用于视频描述优化等场景。
    """
    raw = await image.read()
    if len(raw) > 20 * 1024 * 1024:
        raise HTTPException(400, "图片大小不能超过 20MB")

    image_bytes = compress_image(raw)
    mime_type = image.content_type or "image/jpeg"
    logger.info(f"自由文本查询: prompt={prompt[:50]}...")

    try:
        text = await _provider.free_text_query(image_bytes, prompt, mime_type)
    except RuntimeError as e:
        logger.error(f"自由文本查询失败: {e}")
        raise HTTPException(500, str(e))

    return {
        "success": True,
        "text": text,
    }


@router.post("/plan-aplus")
async def plan_aplus(
    images: List[UploadFile] = File(..., description="商品图片（1-6张）"),
    product_info: str | None = Form(None, description="商品信息文本（可选）"),
):
    """AI A+ 内容策划接口

    上传商品图片 → 豆包视觉模型策划 → 返回 3-5 张 A+ 内容图方案
    """
    if len(images) < 1 or len(images) > 6:
        raise HTTPException(400, "商品图片数量需要 1-6 张")

    img_list = []
    for img in images:
        raw = await img.read()
        if len(raw) > 20 * 1024 * 1024:
            raise HTTPException(400, f"图片 {img.filename} 大小不能超过 20MB")
        compressed = compress_image(raw)
        mime_type = img.content_type or "image/jpeg"
        img_list.append((compressed, mime_type))

    logger.info(f"A+ 策划请求: {len(img_list)} 张图片")

    try:
        result = await _provider.plan_aplus(
            img_list,
            product_info or "",
        )
    except RuntimeError as e:
        logger.error(f"A+ 策划失败: {e}")
        raise HTTPException(500, str(e))

    return {
        "success": True,
        "plans": result.get("plans", []),
        "_meta": result.get("_meta", {}),
    }
