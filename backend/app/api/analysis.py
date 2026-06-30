# 商品视觉分析接口
import json
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from typing import List

from app.deps import get_current_user
from app.providers.deepseek_provider import ProductAnalysisProvider
from app.providers.gemini_provider import GeminiProvider
from app.services.image_utils import compress_image, get_image_info

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["analysis"])

# 全局单例：_provider（豆包，商品/人设分析）、_gemini（Gemini，创意类任务）
_provider = ProductAnalysisProvider()
_gemini = GeminiProvider()


@router.post("/analyze")
async def analyze(
    current_user=Depends(get_current_user),
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
    current_user=Depends(get_current_user),
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
    current_user=Depends(get_current_user),
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
        result = await _gemini.plan_shots(
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
    current_user=Depends(get_current_user),
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
        result = await _gemini.recommend_styles(
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
    current_user=Depends(get_current_user),
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
        text = await _gemini.free_text_query(image_bytes, prompt, mime_type)
    except RuntimeError as e:
        logger.error(f"自由文本查询失败: {e}")
        raise HTTPException(500, str(e))

    return {
        "success": True,
        "text": text,
    }


@router.post("/plan-aplus")
async def plan_aplus(
    current_user=Depends(get_current_user),
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
        result = await _gemini.plan_aplus(
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


@router.post("/enhance-video-prompt")
async def enhance_video_prompt(
    current_user=Depends(get_current_user),
    description: str = Form(..., description="用户的简短动作描述"),
    duration: int = Form(5, description="视频时长（秒）"),
    style: str | None = Form(None, description="风格偏好（可选）"),
    image: UploadFile | None = File(None, description="参考图（可选，帮助 AI 理解服装）"),
):
    """视频 Prompt 智能扩写接口

    简短动作描述 → Gemini 扩写成专业视频叙事 prompt（英文，适配 Seedance）
    """
    if not description.strip():
        raise HTTPException(400, "description 不能为空")

    image_bytes = None
    mime_type = "image/jpeg"
    if image:
        raw = await image.read()
        if len(raw) > 20 * 1024 * 1024:
            raise HTTPException(400, "图片大小不能超过 20MB")
        image_bytes = compress_image(raw, max_long_edge=1280, format="JPEG")
        mime_type = "image/jpeg"

    logger.info(f"视频 prompt 扩写: desc={description[:50]}... duration={duration}s")

    try:
        prompt = await _gemini.enhance_video_prompt(
            description=description,
            duration=duration,
            style=style,
            image=image_bytes,
            mime_type=mime_type,
        )
    except RuntimeError as e:
        logger.error(f"视频 prompt 扩写失败: {e}")
        raise HTTPException(500, str(e))

    return {
        "success": True,
        "prompt": prompt,
    }


# 图片类任务白名单（视频类走 /enhance-video-prompt，不在此）
_IMAGE_TASK_TYPES = {"quick", "outfit", "model_gen", "seed_grass", "product_main", "aplus"}


@router.post("/enhance-prompt")
async def enhance_prompt(
    current_user=Depends(get_current_user),
    user_text: str = Form("", description="用户的简短方向（可空，完全由 AI 创意）"),
    task_type: str = Form(..., description="任务类型：quick/outfit/model_gen/seed_grass/product_main/aplus"),
    aspect_ratio: str | None = Form(None, description="比例（可选，如 9:16）"),
    structured: bool = Form(False, description="True 时返回结构化 JSON（8 要素 + 拼装 prompt），用于工坊结构化模式"),
    image: UploadFile | None = File(None, description="参考图（可选，有图时 AI 看图理解商品样貌）"),
):
    """图片 Prompt 智能创意接口

    简短方向（可选）+ 参考图（可选）→ Gemini 创意出专业级图片生成 prompt。
    用于 QuickImage / 一键穿搭 / 模特生成 / 种草图 / 商品主图 / A+ 图 的"智能创意"按钮。
    视频类任务请走 /enhance-video-prompt。

    structured=True 时返回 {success, structured:{elements, prompt}}，用于工坊要素卡片模式；
    structured=False 返回 {success, text}（兼容旧调用方）。
    """
    if task_type not in _IMAGE_TASK_TYPES:
        raise HTTPException(400, f"不支持的 task_type: {task_type}，图片类允许值：{sorted(_IMAGE_TASK_TYPES)}")

    image_bytes = None
    mime_type = "image/jpeg"
    if image:
        raw = await image.read()
        if len(raw) > 20 * 1024 * 1024:
            raise HTTPException(400, "图片大小不能超过 20MB")
        image_bytes = compress_image(raw, max_long_edge=1280, format="JPEG")
        mime_type = "image/jpeg"

    logger.info(
        f"图片 prompt 智能创意: task={task_type} structured={structured} "
        f"user_text={user_text[:50]!r} has_image={image is not None}"
    )

    try:
        text = await _gemini.enhance_image_prompt(
            user_text=user_text,
            task_type=task_type,
            image=image_bytes,
            mime_type=mime_type,
            aspect_ratio=aspect_ratio,
            structured=structured,
        )
    except RuntimeError as e:
        logger.error(f"图片 prompt 智能创意失败: {e}")
        raise HTTPException(500, str(e))

    if structured:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as e:
            # 正常不应到这（Provider 层已兜底），防御性抛 500
            logger.error(f"structured 模式 JSON 二次解析失败: {e}")
            raise HTTPException(500, "结构化 prompt 解析失败")
        return {
            "success": True,
            "structured": {
                "elements": payload["elements"],
                "prompt": payload["prompt"],
            },
        }

    return {
        "success": True,
        "text": text,
    }
