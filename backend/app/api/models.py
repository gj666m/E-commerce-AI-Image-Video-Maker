# 模型列表接口
from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.services.model_router import get_models_list, get_available_providers

router = APIRouter(prefix="/api", tags=["models"])


@router.get("/models")
async def list_models(current_user=Depends(get_current_user)):
    """返回可用模型列表及状态"""
    providers = get_available_providers()
    models = get_models_list()
    return {
        "models": models,
        "default": next(
            (m["name"] for m in models if m["name"] != "mock"),
            "mock",
        ),
        "total": len(models),
    }
