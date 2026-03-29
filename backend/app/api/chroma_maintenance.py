"""
ChromaDB Maintenance API Endpoints

提供 ChromaDB 維護與優化的 API 端點。
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.chroma_optimizer import chroma_optimizer

router = APIRouter(prefix="/chroma", tags=["chroma-maintenance"])


class CleanupRequest(BaseModel):
    max_age_days: int = 30
    min_count: int = 0
    dry_run: bool = True


class OptimizeRequest(BaseModel):
    collection_name: str


@router.get("/stats")
async def get_all_stats():
    """取得所有 collection 統計資訊。"""
    stats = chroma_optimizer.list_all_collections_stats()
    return {"collections": stats}


@router.get("/stats/{collection_name}")
async def get_collection_stats(collection_name: str):
    """取得特定 collection 統計資訊。"""
    stats = chroma_optimizer.get_collection_stats(collection_name)
    if "error" in stats:
        raise HTTPException(status_code=404, detail=stats["error"])
    return stats


@router.get("/storage")
async def get_storage_info():
    """取得儲存空間資訊。"""
    return chroma_optimizer.get_storage_info()


@router.post("/cleanup")
async def cleanup_collections(request: CleanupRequest):
    """清理過期或空的 collections。

    Args:
        request: 清理參數

    Returns:
        清理結果（包含候選列表）
    """
    result = chroma_optimizer.cleanup_expired_collections(
        max_age_days=request.max_age_days,
        min_count=request.min_count,
        dry_run=request.dry_run,
    )
    return result


@router.post("/optimize")
async def optimize_collection(request: OptimizeRequest):
    """優化 collection 索引。

    重建 HNSW 索引以提升查詢效能。

    Args:
        request: 包含 collection_name

    Returns:
        優化結果
    """
    result = chroma_optimizer.optimize_collection(request.collection_name)

    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("error"))

    return result


@router.get("/health")
async def health_check():
    """ChromaDB 健康檢查。"""
    return chroma_optimizer.health_check()
