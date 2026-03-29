"""LLM Cache API Endpoints

提供 LLM 快取管理的 API 端點。
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.cache_service import semantic_cache

router = APIRouter(prefix="/cache", tags=["cache-maintenance"])


class ClearCacheRequest(BaseModel):
    confirm: bool = False


@router.get("/stats")
async def get_cache_stats():
    """取得快取統計資訊。"""
    return semantic_cache.get_stats()


@router.post("/clear")
async def clear_cache(request: ClearCacheRequest):
    """清空快取。

    Args:
        request: 確認請求

    Returns:
        清除的項目數量
    """
    if not request.confirm:
        raise HTTPException(status_code=400, detail="Confirmation required")

    count = semantic_cache.clear()
    return {"cleared": count}


@router.post("/cleanup")
async def cleanup_expired():
    """清理過期的快取項目。

    Returns:
        清理的項目數量
    """
    count = semantic_cache.cleanup_expired()
    return {"evicted": count}
