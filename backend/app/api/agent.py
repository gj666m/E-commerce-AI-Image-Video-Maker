# 对话式 Agent API
# POST /api/agent/chat        — SSE 流式对话
# POST /api/agent/upload-images — 上传参考图，返回 image_id 列表
import logging

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from app.agents.image_store import image_store
from app.agents.runner import run_agent
from app.config import settings
from app.deps import get_current_user
from app.services.image_utils import compress_image

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agent", tags=["agent"])


class ChatRequest(BaseModel):
    message: str
    thread_id: str
    uploaded_image_ids: list[str] | None = None  # 前端先调 upload-images 拿到的 image_id


@router.post("/chat")
async def agent_chat(
    req: ChatRequest,
    current_user=Depends(get_current_user),
):
    """对话式 Agent SSE 流"""
    if not settings.has_claude:
        raise HTTPException(503, "Agent 不可用：未配置 Claude API Key")
    if not req.message.strip():
        raise HTTPException(400, "消息不能为空")
    if not req.thread_id:
        raise HTTPException(400, "thread_id 不能为空")

    # 构建用户已上传图引用（注入 system prompt 让 Claude 知道可用引用）
    uploaded_refs: list[dict] = []
    for iid in (req.uploaded_image_ids or []):
        meta = await image_store.get_meta(iid)
        if meta is not None:
            uploaded_refs.append({"image_id": iid, "filename": meta.get("filename", "")})

    user_id = current_user["id"]

    async def event_stream():
        async for sse_data in run_agent(
            user_message=req.message,
            user_id=user_id,
            thread_id=req.thread_id,
            uploaded_refs=uploaded_refs,
        ):
            if sse_data:
                yield sse_data

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginx 关闭缓冲
        },
    )


@router.post("/upload-images")
async def upload_images(
    files: list[UploadFile] = File(...),
    current_user=Depends(get_current_user),
):
    """上传参考图，压缩后存 ImageStore，返回 image_id 列表

    前端拿到 image_id 后，在 /chat 请求的 uploaded_image_ids 中传入，
    Claude 即可在工具调用时通过 reference_image_ids 引用。
    """
    if not files:
        raise HTTPException(400, "请至少上传一张图片")
    if len(files) > 6:
        raise HTTPException(400, "最多上传 6 张参考图")

    # 用 user_id + 随机串作为 thread_id 隔离（上传时还没 thread_id，用临时域）
    thread_id = f"u{current_user['id']}_refs"

    results = []
    for f in files:
        raw = await f.read()
        if not raw:
            continue
        # 校验大小
        if len(raw) > settings.max_upload_size_mb * 1024 * 1024:
            raise HTTPException(400, f"{f.filename} 超过 {settings.max_upload_size_mb}MB 限制")
        # 压缩
        try:
            compressed = compress_image(raw, format="JPEG")
        except Exception as e:
            raise HTTPException(400, f"{f.filename} 不是有效图片：{e}")
        # 推断 mime
        mime = f.content_type or "image/jpeg"
        if not mime.startswith("image/"):
            mime = "image/jpeg"
        image_id = await image_store.put(
            compressed,
            thread_id=thread_id,
            mime=mime,
            filename=f.filename or "reference.jpg",
            prefix="img",
        )
        results.append({"image_id": image_id, "filename": f.filename or "reference.jpg"})

    return {"success": True, "images": results}
