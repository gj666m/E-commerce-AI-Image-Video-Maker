# 分镜视频生成 API
"""分镜视频板块：AI 策划分镜 + 用户编辑 + 拼装提交

设计：
- POST /api/video-shots/plan — Gemini 策划分镜（按总时长 10/15s 生成 2-3 个分镜）
- POST /api/video-shots/generate — 接收用户编辑后的分镜列表 + 参考图，
  调 build_shot_video_prompt 合并成单段叙事 description，再走 build_video_prompt 拼模板，
  最后复用 video.py 的 _submit_video_to_provider 提交到 Seedance

复用 video.py 的提交链路：Provider 选择、风格化、商品信息注入、防重复扣费、任务恢复。
"""
import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.deps import get_current_user
from app.providers.gemini_provider import GeminiProvider
from app.services.image_utils import compress_image, get_image_info, stylize_for_video
from app.services.prompt_engine import build_shot_video_prompt, build_video_prompt
from app.services.task_store import cleanup_expired_tasks, create_task
from app.services.video_history_store import cleanup_expired_video_history
from app.api.balance import fetch_quota_snapshot
from app.api.video import _get_video_provider, cleanup_mock_tasks

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/video-shots", tags=["video-shots"])

# 全局 Gemini 单例
_gemini = GeminiProvider()


@router.post("/plan")
async def plan_shots(
    current_user=Depends(get_current_user),
    theme: str = Form(..., description="主题/创意描述"),
    total_duration: int = Form(15, description="总时长（10 或 15 秒）"),
    product_info: str = Form("", description="商品信息文本（可选）"),
    extra_prompt: str = Form("", description="额外要求（可选）"),
    reference_image: UploadFile | None = File(None, description="参考图（可选）"),
):
    """AI 策划分镜方案

    流程：
    1. 参数校验（total_duration 为 4-15 秒整数）
    2. Gemini 按总时长规划分镜（Hook → Detail → Recall）
    3. 返回分镜列表（用户可编辑后提交生成）
    """
    if not (4 <= total_duration <= 15):
        raise HTTPException(400, "总时长仅支持 4-15 秒整数")
    if not theme.strip():
        raise HTTPException(400, "主题不能为空")

    logger.info(
        f"分镜策划 user={current_user['username']}, theme={theme[:60]}, duration={total_duration}s"
    )

    # 参考图读取（可选）
    ref_bytes: bytes | None = None
    ref_mime = "image/jpeg"
    if reference_image:
        ref_bytes = await reference_image.read()
        if len(ref_bytes) > 20 * 1024 * 1024:
            raise HTTPException(400, "参考图不能超过 20MB")
        ref_mime = reference_image.content_type or "image/jpeg"

    try:
        shots = await _gemini.plan_video_shots(
            theme=theme.strip(),
            total_duration=total_duration,
            product_info=product_info.strip(),
            extra_prompt=extra_prompt.strip(),
            reference_image=ref_bytes,
            mime_type=ref_mime,
        )
    except (RuntimeError, ValueError) as e:
        logger.error(f"分镜策划失败: {e}")
        raise HTTPException(500, f"AI 策划失败: {e}")

    logger.info(
        f"分镜策划完成 user={current_user['username']}, shots={len(shots)}"
    )

    return {
        "success": True,
        "shots": shots,
        "total_duration": total_duration,
    }


@router.post("/generate")
async def generate_shot_video(
    current_user=Depends(get_current_user),
    shots_json: str = Form(..., description="用户编辑后的分镜列表 JSON 字符串"),
    product_images: list[UploadFile] = File(default=[], description="商品图（1-6张）"),
    model_images: list[UploadFile] = File(default=[], description="模特素材图（0-3张，可选）"),
    model_has_face: bool = Form(True, description="模特图是否含人脸"),
    duration: int = Form(15, description="视频总时长（秒）"),
    model_name: str | None = Form(None, description="指定视频模型"),
    style: str | None = Form(None, description="风格偏好"),
    ratio: str = Form("16:9", description="视频比例"),
    generate_audio: bool = Form(False, description="是否生成音频"),
    resolution: str | None = Form(None, description="分辨率"),
    product_info: str = Form("", description="商品信息文本"),
    custom_prompt: str = Form("", description="用户自定义补充"),
):
    """提交分镜视频生成任务

    流程：
    1. 解析 shots_json → list[dict]，校验
    2. 读图 + 风格化处理（复用 video.py 同套逻辑）
    3. build_shot_video_prompt 合并分镜为单段 description
    4. build_video_prompt 套模板（含商品信息注入 + 风格化前缀）
    5. 调 video.py 共享的 _submit_video_to_provider 提交到 Seedance
    """
    user_id = current_user["id"]
    await cleanup_expired_video_history()
    await cleanup_expired_tasks()
    cleanup_mock_tasks()

    # ========== 1. 参数校验 ==========
    # 分镜视频必须具体时长（不能 -1 自动，AI 需要具体总时长分配分镜）
    if not (4 <= duration <= 15):
        raise HTTPException(400, "视频时长仅支持 4-15 秒整数")
    valid_video_ratios = {"16:9", "9:16", "1:1"}
    if ratio not in valid_video_ratios:
        raise HTTPException(400, f"视频比例仅支持: {', '.join(sorted(valid_video_ratios))}")
    valid_resolutions = {"480p", "720p", "1080p", None}
    if resolution not in valid_resolutions:
        raise HTTPException(400, "分辨率仅支持: 480p / 720p / 1080p")

    # 解析 shots_json
    try:
        shots = json.loads(shots_json)
    except json.JSONDecodeError as e:
        raise HTTPException(400, f"分镜 JSON 解析失败: {e}")
    if not isinstance(shots, list) or not shots:
        raise HTTPException(400, "分镜列表不能为空")
    if len(shots) > 5:
        raise HTTPException(400, "分镜数量不能超过 5 个")

    # ========== 2. 图片读取 + 处理 ==========
    async def _read_images(files: list[UploadFile], max_size: int, label: str) -> list[bytes]:
        result = []
        for f in files:
            raw = await f.read()
            if len(raw) > max_size:
                raise HTTPException(400, f"{label}大小不能超过 {max_size // 1024 // 1024}MB")
            if raw:
                result.append(raw)
        return result

    product_raw = await _read_images(product_images, 20 * 1024 * 1024, "商品图")
    model_raw = await _read_images(model_images, 20 * 1024 * 1024, "模特素材图")

    VIDEO_REF_MAX_EDGE = 1280
    product_bytes = [compress_image(raw, max_long_edge=VIDEO_REF_MAX_EDGE, format="JPEG") for raw in product_raw]

    has_stylized_model = False
    model_bytes: list[bytes] = []
    if model_raw:
        if model_has_face:
            logger.info(f"模特素材图含人脸，开始风格转换（{len(model_raw)} 张）...")
            stylized_list = await asyncio.gather(
                *[stylize_for_video(raw) for raw in model_raw]
            )
            model_bytes = [compress_image(s, max_long_edge=VIDEO_REF_MAX_EDGE, format="JPEG") for s in stylized_list]
            has_stylized_model = True
            logger.info("模特素材图风格转换完成")
        else:
            model_bytes = [compress_image(raw, max_long_edge=VIDEO_REF_MAX_EDGE, format="JPEG") for raw in model_raw]

    all_images = product_bytes + model_bytes
    if all_images:
        sizes_str = ", ".join(
            f"{get_image_info(b)['width']}x{get_image_info(b)['height']}" for b in all_images
        )
        logger.info(f"参考图总数: {len(all_images)} (商品{len(product_bytes)}+模特{len(model_bytes)}), 尺寸: {sizes_str}")

    # ========== 3. 分镜 → 单段 description ==========
    shot_description = build_shot_video_prompt(shots)
    if not shot_description.strip():
        raise HTTPException(400, "分镜描述拼装失败，请检查分镜字段")

    # ========== 4. description 套视频模板（含商品信息/风格化前缀）==========
    prompt = build_video_prompt(
        description=shot_description,
        style=style,
        duration=duration,
        user_custom=custom_prompt if custom_prompt.strip() else None,
        camera_movement=None,  # 分镜每镜自带 camera 字段
        product_info_text=product_info if product_info.strip() else None,
        has_stylized_model=has_stylized_model,
    )
    logger.info(
        f"分镜视频 Prompt 拼装完成，长度: {len(prompt)}, "
        f"分镜数: {len(shots)}, 含风格化引导: {has_stylized_model}"
    )

    # ========== 5. 提交任务（复用 video.py Provider 链路）==========
    provider = _get_video_provider(model_name)
    main_image = all_images[0] if all_images else None
    extra_images = all_images[1:] if len(all_images) > 1 else []

    balance_before = None
    if provider.name == "seedance_apiyi":
        try:
            balance_before = await fetch_quota_snapshot()
        except Exception as e:
            logger.warning(f"提交前余额快照失败（降级 token 估算）: {e}")

    try:
        external_id = await provider.submit(
            prompt,
            image=main_image,
            extra_images=extra_images,
            params={
                "duration": duration,
                "ratio": ratio,
                "generate_audio": generate_audio,
                "resolution": resolution,
            },
        )
    except RuntimeError as e:
        error_msg = str(e)
        if "PrivacyInformation" in error_msg or "real person" in error_msg:
            raise HTTPException(
                400,
                "参考图包含真实人脸，Seedance 不支持真人图片生成视频。请使用商品图或 AI 生成的模特图。",
            )
        if "SensitiveContent" in error_msg:
            raise HTTPException(400, "参考图内容未通过安全审核，请更换图片后重试。")
        if "额度不足" in error_msg:
            raise HTTPException(429, error_msg)
        raise HTTPException(500, f"视频提交失败: {error_msg}")

    task_id = uuid.uuid4().hex[:12]
    await create_task(
        task_id=task_id,
        user_id=user_id,
        external_id=external_id,
        provider_name=provider.name,
        prompt=prompt,
        resolution=resolution,
        balance_before=balance_before,
    )

    logger.info(
        f"分镜视频任务已提交: task_id={task_id}, provider={provider.name}, user={user_id}"
    )

    return {
        "success": True,
        "task_id": task_id,
        "status": "pending",
    }
