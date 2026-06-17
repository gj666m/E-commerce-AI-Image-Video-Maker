# 视频生成 API - 提交任务 / 查询状态 / 获取结果
import asyncio
import logging
import time
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.config import settings
from app.deps import get_current_user
from app.services.image_utils import compress_image, get_image_info, stylize_for_video
from app.services.prompt_engine import build_video_prompt
from app.services.video_utils import (
    make_video_url,
    save_video,
)
from app.services.task_store import create_task, get_task, update_task_status, cleanup_expired_tasks, get_user_active_tasks, compute_real_cost
from app.services.video_history_store import cleanup_expired_video_history
from app.providers.mock_video_provider import MockVideoProvider
from app.providers.seedance_provider import SeedanceVideoProvider
from app.providers.seedance_apiyi_provider import SeedanceApiyiVideoProvider
from app.providers.video_base import VideoProvider
from app.api.balance import fetch_quota_snapshot

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/video", tags=["video"])

# ========== 视频 Provider 注册表 ==========

_mock_video = MockVideoProvider()
_seedance_video = SeedanceVideoProvider()
_seedance_apiyi_video = SeedanceApiyiVideoProvider()


def _get_available_video_providers() -> dict[str, VideoProvider]:
    """获取所有可用的视频 Provider"""
    providers: dict[str, VideoProvider] = {
        "mock_video": _mock_video,
    }
    if settings.has_seedance:
        providers["seedance"] = _seedance_video
    if settings.has_seedance_apiyi:
        providers["seedance_apiyi"] = _seedance_apiyi_video
    return providers


def _get_video_provider(model_name: str | None = None) -> VideoProvider:
    """根据用户指定模型或自动路由获取视频 Provider"""
    providers = _get_available_video_providers()

    if model_name and model_name in providers:
        return providers[model_name]

    if settings.has_seedance_apiyi:
        return providers["seedance_apiyi"]
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
    "seedance_apiyi": {
        "display_name": "Seedance 2.0（API易中转）",
        "description": "Seedance 2.0 通过 API易中转站接入，不限并发不排队，按 token 计费",
        "capabilities": ["image_to_video", "text_to_video"],
        "api_key_hint": "SEEDANCE_APIYI_API_KEY",
    },
}

# ========== Provider 实例缓存（用于 poll/get_result） ==========
# 提交时缓存 provider 实例到内存，poll 时按 provider_name 重新获取
def _get_provider_by_name(name: str) -> VideoProvider | None:
    providers = _get_available_video_providers()
    return providers.get(name)


# 同步清理 MockVideoProvider 的内存任务表
def cleanup_mock_tasks():
    """清理 Mock Provider 中过期的内存任务"""
    expired_keys = [
        tid for tid, t in _mock_video._tasks.items()
        if t.status in ("completed", "failed")
        and t.meta.get("completed_at")
        and (time.time() - t.meta["completed_at"]) > 3600
    ]
    for tid in expired_keys:
        _mock_video._tasks.pop(tid, None)


# ========== API 端点 ==========


@router.post("/generate")
async def generate_video(
    current_user=Depends(get_current_user),
    product_images: list[UploadFile] = File(default=[], description="商品图（1-6张）"),
    model_images: list[UploadFile] = File(default=[], description="模特素材图（0-3张，可选）"),
    model_has_face: bool = Form(True, description="模特图是否含人脸"),
    images: list[UploadFile] = File(default=[], description="[旧] 参考图（最多6张）"),
    image: UploadFile | None = File(None, description="[旧] 参考图（兼容单张）"),
    description: str = Form(..., description="视频描述"),
    duration: int = Form(5, description="视频时长（秒）"),
    model_name: str | None = Form(None, description="指定模型"),
    style: str | None = Form(None, description="风格偏好"),
    custom_prompt: str | None = Form(None, description="用户自定义 Prompt"),
    ratio: str = Form("16:9", description="视频比例"),
    generate_audio: bool = Form(False, description="是否生成音频"),
    camera_movement: str | None = Form(None, description="镜头运动"),
    product_info: str | None = Form(None, description="商品信息文本"),
    resolution: str | None = Form(None, description="分辨率"),
):
    """提交视频生成任务"""
    user_id = current_user["id"]
    await cleanup_expired_video_history()
    await cleanup_expired_tasks()
    cleanup_mock_tasks()

    # 参数校验
    if duration not in (5, 10, 15, -1):
        raise HTTPException(400, "视频时长仅支持 5/10/15/-1（自动）秒")
    valid_video_ratios = {"16:9", "9:16", "1:1"}
    if ratio not in valid_video_ratios:
        raise HTTPException(400, f"视频比例仅支持: {', '.join(sorted(valid_video_ratios))}")
    valid_cameras = {"推近", "拉远", "环绕", "平移", "跟随", None}
    if camera_movement not in valid_cameras:
        raise HTTPException(400, "镜头运动仅支持: 推近/拉远/环绕/平移/跟随")
    valid_resolutions = {"480p", "720p", "1080p", None}
    if resolution not in valid_resolutions:
        raise HTTPException(400, "分辨率仅支持: 480p / 720p / 1080p")
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

    if not product_raw and not model_raw:
        old_raw = await _read_images(images, 20 * 1024 * 1024, "参考图")
        if not old_raw and image:
            raw = await image.read()
            if len(raw) > 20 * 1024 * 1024:
                raise HTTPException(400, "图片大小不能超过 20MB")
            if raw:
                old_raw.append(raw)
        product_raw = old_raw

    # ========== 2. 图片处理 ==========
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

    # 提交前对 API易 余额做一次快照（仅对 API易 中转的 provider 有意义）
    balance_before = None
    if provider.name == "seedance_apiyi":
        try:
            balance_before = await fetch_quota_snapshot()
        except Exception as e:
            logger.warning(f"提交前余额快照失败（降级 token 估算）: {e}")

    try:
        external_id = await provider.submit(
            prompt, image=main_image, extra_images=extra_images,
            params={"duration": duration, "ratio": ratio, "generate_audio": generate_audio, "resolution": resolution},
        )
    except RuntimeError as e:
        error_msg = str(e)
        if "PrivacyInformation" in error_msg or "real person" in error_msg:
            raise HTTPException(400, "参考图包含真实人脸，Seedance 不支持真人图片生成视频。请使用商品图或 AI 生成的模特图。")
        if "SensitiveContent" in error_msg:
            raise HTTPException(400, "参考图内容未通过安全审核，请更换图片后重试。")
        if "额度不足" in error_msg:
            raise HTTPException(429, error_msg)
        raise HTTPException(500, f"视频提交失败: {error_msg}")

    # ========== 5. 记录任务到 SQLite ==========
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

    logger.info(f"视频任务已提交: task_id={task_id}, provider={provider.name}, user={user_id}")

    return {
        "success": True,
        "task_id": task_id,
        "status": "pending",
    }


@router.get("/status/{task_id}")
async def video_status(task_id: str, current_user=Depends(get_current_user)):
    """查询视频生成任务状态"""
    task_info = await get_task(task_id)
    if not task_info:
        raise HTTPException(404, "任务不存在")

    # 权限检查：普通用户只能看自己的任务
    if current_user["role"] != "admin" and task_info["user_id"] != current_user["id"]:
        raise HTTPException(403, "无权查看此任务")

    provider = _get_provider_by_name(task_info["provider_name"])
    if not provider:
        raise HTTPException(500, f"Provider {task_info['provider_name']} 不可用")

    external_id = task_info["external_id"]

    # 查询状态
    video_task = await provider.poll(external_id)

    # 真实扣费计算（仅对 API易 中转 + 任务刚完成的场景）
    # 逻辑：取提交前的 quota 快照 vs 当前 quota，差值即为 API易 实际扣费（含补扣费）
    real_cost = None
    real_currency = video_task.currency
    is_first_complete = (
        video_task.status == "completed"
        and not task_info.get("video_url")  # DB 里还没 video_url = 首次完成
    )

    # 路径 A：DB 里已有持久化的 cost（非首次完成 poll）→ 直接用，避免降级回 token 估算
    if (
        video_task.status == "completed"
        and task_info.get("cost") is not None
    ):
        real_cost = float(task_info["cost"])
        real_currency = task_info.get("currency") or video_task.currency

    # 路径 B：首次完成 + API易 + 有 balance_before 快照 → 立即算 + 持久化
    elif (
        is_first_complete
        and task_info.get("provider_name") == "seedance_apiyi"
        and task_info.get("balance_before") is not None
    ):
        try:
            balance_after = await fetch_quota_snapshot()
            cost_val = compute_real_cost(task_info.get("balance_before"), balance_after)
            if cost_val is not None:
                real_cost = cost_val
                real_currency = "$"  # API易 按美元计费
                logger.info(
                    f"视频真实扣费 task={task_id}: quota {task_info['balance_before']}→{balance_after}, "
                    f"cost=${real_cost} (token 估算 ¥{video_task.cost})"
                )
        except Exception as e:
            logger.warning(f"完成后余额快照失败，降级 token 估算: {e}")

    # 构建返回
    result = {
        "task_id": task_id,
        "status": video_task.status,
        "progress": video_task.progress,
        "model_used": video_task.model_used or provider.name,
        "prompt_used": video_task.prompt_used or task_info["prompt"],
        "cost": real_cost if real_cost is not None else video_task.cost,
        "currency": real_currency,
    }

    # 完成时：获取视频 → 保存临时文件 → 返回 URL
    if video_task.status == "completed" and not video_task.video_url:
        try:
            video_data = await provider.get_result(external_id)
            ext = "gif" if provider.name == "mock_video" else "mp4"
            rel_path = save_video(task_info["user_id"], task_id, video_data, ext=ext)
            video_task.video_url = make_video_url(rel_path)
            # 同时持久化 cost（首次完成时算出的真实扣费或降级 token 估算）
            cost_to_save = real_cost if real_cost is not None else video_task.cost
            currency_to_save = real_currency if real_cost is not None else video_task.currency
            await update_task_status(
                task_id, "completed",
                video_url=video_task.video_url,
                cost=cost_to_save,
                currency=currency_to_save,
            )
        except RuntimeError as e:
            result["status"] = "failed"
            result["error"] = str(e)
            await update_task_status(task_id, "failed", error=str(e))
            return result

    if video_task.video_url:
        result["video_url"] = video_task.video_url

    if video_task.error:
        result["error"] = video_task.error

    return result


@router.get("/tasks")
async def list_user_video_tasks(current_user=Depends(get_current_user)):
    """获取当前用户进行中的视频任务（切页面后恢复轮询用）"""
    tasks = await get_user_active_tasks(current_user["id"])
    return {"tasks": tasks}


@router.get("/models")
async def video_models():
    """返回可用的视频模型列表"""
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

    default = "mock_video"
    for name in providers:
        if name != "mock_video":
            default = name
            break

    return {
        "models": models,
        "default": default,
    }
