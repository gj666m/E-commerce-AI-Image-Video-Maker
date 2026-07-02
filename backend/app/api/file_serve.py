# 静态文件鉴权访问（替代裸 StaticFiles 挂载）
# 续10 安全 Review P0-R2：原 /video-files /model-files /gen-files 三处 StaticFiles
# 挂载完全不走 token 校验，任何人凭 URL 可下载任何用户文件（含未登录外部访问）。
# 本端点统一收口：token via query param（兼容 <img> 不能加 header），
# 解析路径第一段 user_id 做归属校验，admin 旁路放行。
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.auth import decode_token
from app.config import settings

router = APIRouter(prefix="/api/file", tags=["file"])

# kind → 磁盘根目录
_KIND_DIR = {
    "video-files": settings.video_temp_dir,
    "model-files": settings.model_store_dir,
    "gen-files": settings.generation_history_dir,
}


@router.get("/{kind}/{path:path}")
async def serve_file(kind: str, path: str, token: str = Query(default="")):
    """鉴权访问用户文件

    路径约定：第一段为 user_id（如 "3/abc.mp4"）。
    - admin：可访问任意 user_id（管理员看所有人历史/素材）
    - user：只能访问本人 user_id 下的文件
    - 任何越权/不存在统一返 404（不泄露文件存在性）
    """
    # 1. 校验 token（未带或无效统一返 401）
    if not token:
        raise HTTPException(401, "缺少 token")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(401, "token 无效或已过期")

    role = payload.get("role", "user")
    try:
        current_uid = int(payload.get("sub", 0))
    except (TypeError, ValueError):
        current_uid = 0

    # 2. 校验 kind
    if kind not in _KIND_DIR:
        raise HTTPException(404)

    base_dir = Path(_KIND_DIR[kind]).resolve()
    base_dir.mkdir(parents=True, exist_ok=True)

    # 3. 解析路径 + 防穿越
    clean = path.lstrip("/")
    file_path = (base_dir / clean).resolve()
    try:
        file_path.relative_to(base_dir)
    except ValueError:
        # 越出 base_dir，视为越权
        raise HTTPException(404)

    if not file_path.is_file():
        raise HTTPException(404)

    # 4. 归属校验：第一段必须为 user_id
    parts = clean.split("/", 1)
    if len(parts) < 2:
        # 没有 user_id 前缀（旧数据可能），保守拒绝
        raise HTTPException(404)

    try:
        owner_uid = int(parts[0])
    except ValueError:
        raise HTTPException(404)

    if role != "admin" and current_uid != owner_uid:
        raise HTTPException(404)

    return FileResponse(file_path)
