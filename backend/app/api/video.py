# 视频生成 API - 提交任务 / 查询状态 / 获取结果
import asyncio
import logging
import time
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import settings
from app.services.image_utils import compress_image, get_image_info, stylize_for_video
from app.services.prompt_engine import build_video_prompt
from app.services.video_utils import (
    cleanup_expired,
    make_video_url,
    save_video,
)
from app.providers.mock_video_provider import MockVideoProvider
from app.providers.seedance_provider import SeedanceVideoProvider
from app.providers.video_base import VideoProvider

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/video", tags=["video"])

# ========== 视频 Provider 注册表 ==========

_mock_video = MockVideoProvider()
_seedance_video = SeedanceVideoProvider()


def _get_available_video_providers() -> dict[str, VideoProvider]:
    """获取所有可用的视频 Provider"""
    providers: dict[str, VideoProvider] = {
        "mock_video": _mock_video,
    }
    if settings.has_seedance:
        providers["seedance"] = _seedance_video
    return providers


def _get_video_provider(model_name: str | None = None) -> VideoProvider:
    """根据用户指定模型或自动路由获取视频 Provider"""
    providers = _get_available_video_providers()

    # 用户指定了模型
    if model_name and model_name in providers:
        return providers[model_name]

    # 自动路由：优先真实 Provider，mock 兜底
    if settings.has_seedance:
        return providers["seedance"]

    return providers["mock_video"]


# 视频模型元信息注册表
_VIDEO_MODEL_META = {
    "mock_video": {
        "display_name": "Mock 视频生成（测试模式）",
        "description": "无 API Key 时使用，返回占位 GIF",
        "capabilities": ["image_to_video", "text_to_video"],
        "api_key_hint": "无需 Key",
    },
    "seedance": {
        "display_name": "Seedance 2.0",
        "description": "字节跳动 Seedance 视频生成，支持图生视频 + 音频生成",
        "capabilities": ["image_to_video", "text_to_video"],
        "api_key_hint": "VOLCENGINE_SEEDANCE_ENDPOINT",
    },
}

# ========== 内存任务表 ==========

_tasks: dict[str, dict] = {}
_TASK_EXPIRE_SECONDS = 3600  # 已完成任务保留 1 小时后清理


def cleanup_tasks():
    """清理过期的已完成任务，防止内存泄漏"""
    now = time.time()
    expired_keys = [
        tid for tid, t in _tasks.items()
        if t.get("completed_at") and (now - t["completed_at"]) > _TASK_EXPIRE_SECONDS
    ]
    for tid in expired_keys:
        _tasks.pop(tid, None)
    if expired_keys:
        logger.info(f"清理过期视频任务: {len(expired_keys)} 个")


# 同步清理 MockVideoProvider 的内存任务表
def cleanup_mock_tasks():
    """清理 Mock Provider 中过期的内存任务"""
    expired_keys = [
        tid for tid, t in _mock_video._tasks.items()
        if t.status in ("completed", "failed")
        and t.meta.get("completed_at")
        and (time.time() - t.meta["completed_at"]) > _TASK_EXPIRE_SECONDS
    ]
    for tid in expired_keys:
        _mock_video._tasks.pop(tid, None)


# ========== API 端点 ==========


@router.post("/generate")
async def generate_video(
    # 新参数：商品图 + 模特素材图分区
    product_images: list[UploadFile] = File(default=[], description="商品图（1-6张）"),
    model_images: list[UploadFile] = File(default=[], description="模特素材图（0-3张，可选）"),
    model_has_face: bool = Form(True, description="模特图是否含人脸（默认勾选，含人脸则自动风格化）"),
    # 兼容旧参数
    images: list[UploadFile] = File(default=[], description="[旧] 参考图（最多6张）"),
    image: UploadFile | None = File(None, description="[旧] 参考图（兼容单张）"),
    # 通用参数
    description: str = Form(..., description="视频描述"),
    duration: int = Form(5, description="视频时长（秒）: 5 / 10 / 15 / -1（自动）"),
    model_name: str | None = Form(None, description="指定模型，None 则自动路由"),
    style: str | None = Form(None, description="风格偏好"),
    custom_prompt: str | None = Form(None, description="用户自定义 Prompt 补充"),
    ratio: str = Form("16:9", description="视频比例: 16:9 / 9:16 / 1:1"),
    generate_audio: bool = Form(False, description="是否生成音频"),
    camera_movement: str | None = Form(None, description="镜头运动: 推近/拉远/环绕/平移/跟随"),
    product_info: str | None = Form(None, description="商品信息文本"),
):
    """提交视频生成任务

    流程：接收参数 → 商品图压缩 → 模特图风格转换（按需） → Prompt 拼装 → 提交任务 → 返回 task_id
    """
    cleanup_expired()
    cleanup_tasks()
    cleanup_mock_tasks()

    # 参数校验
    if duration not in (5, 10, 15, -1):
        raise HTTPException(400, "视频时长仅支持 5/10/15/-1（自动）秒")
    valid_video_ratios = {"16:9", "9:16", "1:1"}
    if ratio not in valid_video_ratios:
        raise HTTPException(400, f"视频比例仅支持: {', '.join(sorted(valid_video_ratios))}")
    valid_cameras = {"推近", "拉远", "环绕", "平移", "跟随", None}
    if camera_movement not in valid_cameras:
        raise HTTPException(400, f"镜头运动仅支持: 推近/拉远/环绕/平移/跟随")
    if not description or not description.strip():
        raise HTTPException(400, "视频描述不能为空")

    # ========== 1. 图片读取 ==========
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

    # 兼容旧参数：新参数为空时从旧参数读取（统一放商品图区）
    if not product_raw and not model_raw:
        old_raw = await _read_images(images, 20 * 1024 * 1024, "参考图")
        if not old_raw and image:
            raw = await image.read()
            if len(raw) > 20 * 1024 * 1024:
                raise HTTPException(400, "图片大小不能超过 20MB")
            if raw:
                old_raw.append(raw)
        product_raw = old_raw  # 旧参数全部当商品图处理

    # ========== 2. 图片处理 ==========
    # 商品图：仅压缩
    product_bytes = [compress_image(raw) for raw in product_raw]

    # 模特图：含人脸 → 风格转换；不含人脸 → 仅压缩
    has_stylized_model = False
    model_bytes: list[bytes] = []

    if model_raw:
        if model_has_face:
            logger.info(f"模特素材图含人脸，开始风格转换（{len(model_raw)} 张）...")
            # 并行风格转换所有模特图
            stylized_list = await asyncio.gather(
                *[stylize_for_video(raw) for raw in model_raw]
            )
            # 风格转换后的图再压缩
            model_bytes = [compress_image(s) for s in stylized_list]
            has_stylized_model = True
            logger.info("模特素材图风格转换完成")
        else:
            model_bytes = [compress_image(raw) for raw in model_raw]

    # 合并所有图片：商品图在前，模特图在后
    all_images = product_bytes + model_bytes

    if all_images:
        sizes_str = ", ".join(f"{get_image_info(b)['width']}x{get_image_info(b)['height']}" for b in all_images)
        logger.info(f"参考图总数: {len(all_images)} (商品{len(product_bytes)}+模特{len(model_bytes)}), 尺寸: {sizes_str}")

    # ========== 3. Prompt 拼装 ==========
    prompt = build_video_prompt(
        description=description,
        style=style,
        duration=duration,
        user_custom=custom_prompt,
        camera_movement=camera_movement,
        product_info_text=product_info,
        has_stylized_model=has_stylized_model,
    )
    logger.info(f"视频 Prompt 拼装完成，长度: {len(prompt)}, 含风格化引导: {has_stylized_model}")

    # ========== 4. 提交任务 ==========
    provider = _get_video_provider(model_name)
    main_image = all_images[0] if all_images else None
    extra_images = all_images[1:] if len(all_images) > 1 else []
    try:
        external_id = await provider.submit(
            prompt, image=main_image, extra_images=extra_images,
            params={"duration": duration, "ratio": ratio, "generate_audio": generate_audio},
        )
    except RuntimeError as e:
        error_msg = str(e)
        if "PrivacyInformation" in error_msg or "real person" in error_msg:
            raise HTTPException(400, "参考图包含真实人脸，Seedance 不支持真人图片生成视频。请使用商品图或 AI 生成的模特图。")
        if "SensitiveContent" in error_msg:
            raise HTTPException(400, "参考图内容未通过安全审核，请更换图片后重试。")
        # 429 限流等用户可理解的错误直接透传
        if "额度不足" in error_msg:
            raise HTTPException(429, error_msg)
        raise HTTPException(500, f"视频提交失败: {error_msg}")

    # ========== 5. 记录任务 ==========
    task_id = uuid.uuid4().hex[:12]
    _tasks[task_id] = {
        "external_id": external_id,
        "provider": provider,
        "prompt": prompt,
    }

    logger.info(f"视频任务已提交: task_id={task_id}, provider={provider.name}")

    return {
        "success": True,
        "task_id": task_id,
        "status": "pending",
    }


@router.get("/status/{task_id}")
async def video_status(task_id: str):
    """查询视频生成任务状态"""
    task_info = _tasks.get(task_id)
    if not task_info:
        raise HTTPException(404, "任务不存在")

    provider: VideoProvider = task_info["provider"]
    external_id = task_info["external_id"]

    # 查询状态
    video_task = await provider.poll(external_id)

    # 构建返回
    result = {
        "task_id": task_id,
        "status": video_task.status,
        "progress": video_task.progress,
        "model_used": video_task.model_used or provider.name,
        "prompt_used": video_task.prompt_used or task_info["prompt"],
        "cost": video_task.cost,
        "currency": video_task.currency,
    }

    # 完成时：获取视频 → 保存临时文件 → 返回 URL
    if video_task.status == "completed" and not video_task.video_url:
        try:
            video_data = await provider.get_result(external_id)
            ext = "gif" if provider.name == "mock_video" else "mp4"
            filename = save_video(task_id, video_data, ext=ext)
            video_task.video_url = make_video_url(filename)
            # 记录完成时间，用于后续清理
            task_info["completed_at"] = time.time()
        except RuntimeError as e:
            result["status"] = "failed"
            result["error"] = str(e)
            task_info["completed_at"] = time.time()
            return result

    if video_task.video_url:
        result["video_url"] = video_task.video_url

    if video_task.error:
        result["error"] = video_task.error

    return result


@router.get("/models")
async def video_models():
    """返回可用的视频模型列表（供前端展示）"""
    providers = _get_available_video_providers()
    models = []
    for name, provider in providers.items():
        meta = _VIDEO_MODEL_META.get(name, {})
        models.append({
            "name": name,
            "display_name": meta.get("display_name", name),
            "available": provider.is_available,
            "description": meta.get("description", ""),
            "capabilities": meta.get("capabilities", []),
            "api_key_hint": meta.get("api_key_hint", ""),
        })

    # 默认模型：优先真实 Provider
    default = "mock_video"
    for name in providers:
        if name != "mock_video":
            default = name
            break

    return {
        "models": models,
        "default": default,
    }
