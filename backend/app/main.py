# FastAPI 入口
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import generate, models, model, video, analysis
from app.config import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# ====== 后台定时清理任务 ======
_background_task: asyncio.Task | None = None


async def _periodic_cleanup():
    """每 10 分钟清理过期视频文件和内存任务"""
    while True:
        await asyncio.sleep(600)  # 10 分钟
        try:
            from app.services.video_utils import cleanup_expired
            from app.api.video import cleanup_tasks, cleanup_mock_tasks
            file_count = cleanup_expired()
            cleanup_tasks()
            cleanup_mock_tasks()
            if file_count > 0:
                logging.getLogger(__name__).info(f"定时清理: 删除 {file_count} 个过期视频文件")
        except Exception as e:
            logging.getLogger(__name__).error(f"定时清理失败: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global _background_task
    _background_task = asyncio.create_task(_periodic_cleanup())
    logging.getLogger(__name__).info("后台定时清理任务已启动（每 10 分钟）")
    yield
    if _background_task:
        _background_task.cancel()
        logging.getLogger(__name__).info("后台定时清理任务已停止")
    # 关闭全局 httpx 连接池
    from app.services.http_client import close_http_client
    await close_http_client()


app = FastAPI(
    title="AI 电商图像视频生成工具",
    version="0.2.0",
    debug=settings.debug,
    lifespan=lifespan,
)

# CORS - 允许前端开发服务器访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite 默认端口
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 安全响应头中间件
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# 全局异常处理：防止内部错误泄露敏感信息
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger = logging.getLogger(__name__)
    logger.error(f"未捕获异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误，请稍后重试"},
    )

# 注册路由
app.include_router(generate.router)
app.include_router(models.router)
app.include_router(model.router)
app.include_router(video.router)
app.include_router(analysis.router)

# 挂载临时视频文件静态目录
temp_dir = Path(settings.video_temp_dir)
temp_dir.mkdir(parents=True, exist_ok=True)
app.mount("/video-files", StaticFiles(directory=str(temp_dir)), name="video-files")

# 挂载模特库静态目录（供前端展示模特缩略图）
models_dir = Path(settings.model_store_dir)
models_dir.mkdir(parents=True, exist_ok=True)
app.mount("/model-files", StaticFiles(directory=str(models_dir)), name="model-files")


# ====== 生产环境：托管前端静态文件 ======
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@app.get("/")
async def serve_index():
    """前端首页"""
    if FRONTEND_DIST.exists():
        return FileResponse(FRONTEND_DIST / "index.html")
    return {"message": "AI-ZW API", "docs": "/docs"}


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "env": settings.app_env,
        "providers": {
            "openai": settings.has_openai,
            "fal": settings.has_fal,
            "kling": settings.has_kling,
            "photoroom": settings.has_photoroom,
            "volcengine": settings.has_volcengine,
            "deepseek": settings.has_deepseek,
            "product_analysis": settings.has_product_analysis,
        },
        "mock_mode": not settings.has_any_provider,
    }


# SPA fallback：所有非 /api、非静态文件的请求返回 index.html
@app.get("/{path:path}")
async def serve_spa(path: str):
    """SPA 路由回退"""
    # /api 开头的走后端路由，不处理
    if path.startswith("api/") or path.startswith("video-files/") or path.startswith("model-files/"):
        return None
    file_path = FRONTEND_DIST / path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    # SPA 回退到 index.html
    if FRONTEND_DIST.exists():
        return FileResponse(FRONTEND_DIST / "index.html")
    return {"message": "AI-ZW API", "docs": "/docs"}
