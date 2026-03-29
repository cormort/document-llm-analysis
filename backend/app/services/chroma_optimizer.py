"""
ChromaDB Optimization Service

提供 ChromaDB 索引優化、定期清理與維護功能。

Features:
- 索引參數調校 (HNSW)
- 自動清理過期 collection
- 統計監控
- 索引重建優化
"""

import os
import time
from datetime import datetime, timedelta
from typing import Optional

import chromadb
import structlog
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings

logger = structlog.get_logger()

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data"
)
CHROMA_PERSIST_DIR = os.path.join(DATA_DIR, "chroma_db")


class ChromaDBOptimizer:
    """ChromaDB 優化與維護服務。"""

    def __init__(self, persist_directory: str = CHROMA_PERSIST_DIR):
        """初始化優化服務。

        Args:
            persist_directory: ChromaDB 資料目錄
        """
        self.persist_directory = persist_directory
        self._client: Optional[chromadb.Client] = None
        self._initialized = False

    def _lazy_init(self) -> bool:
        """延遲初始化 ChromaDB 客戶端。"""
        if self._initialized:
            return True

        try:
            os.makedirs(self.persist_directory, exist_ok=True)

            self._client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )
            self._initialized = True
            logger.info("ChromaDB Optimizer initialized", path=self.persist_directory)
            return True

        except Exception as e:
            logger.error("Failed to initialize ChromaDB Optimizer", error=str(e))
            return False

    def get_collection_stats(self, collection_name: str) -> dict:
        """取得 collection 統計資訊。

        Args:
            collection_name: Collection 名稱

        Returns:
            統計資訊字典
        """
        if not self._lazy_init():
            return {"error": "Not initialized"}

        try:
            collection = self._client.get_collection(collection_name)
            count = collection.count()
            metadata = collection.metadata or {}

            return {
                "name": collection_name,
                "count": count,
                "metadata": metadata,
                "indexed_at": metadata.get("indexed_at", "Unknown"),
                "file_name": metadata.get("file_name", "Unknown"),
                "file_type": metadata.get("file_type", "Unknown"),
            }

        except Exception as e:
            return {"error": str(e), "collection": collection_name}

    def list_all_collections_stats(self) -> list[dict]:
        """列出所有 collection 的統計資訊。"""
        if not self._lazy_init():
            return []

        try:
            collections = self._client.list_collections()
            stats = []

            for col in collections:
                stat = self.get_collection_stats(col.name)
                stats.append(stat)

            return stats

        except Exception as e:
            logger.error("Failed to list collections", error=str(e))
            return []

    def cleanup_expired_collections(
        self,
        max_age_days: int = 30,
        min_count: int = 0,
        dry_run: bool = True,
    ) -> dict:
        """清理過期或空的 collections。

        Args:
            max_age_days: 最大保留天數
            min_count: 最小文件數量（低於此數可刪除）
            dry_run: 是否為演練模式（不實際刪除）

        Returns:
            清理結果
        """
        if not self._lazy_init():
            return {"error": "Not initialized", "deleted": 0}

        deleted_count = 0
        candidates = []

        try:
            collections = self._client.list_collections()
            cutoff_date = datetime.now() - timedelta(days=max_age_days)

            for col in collections:
                meta = col.metadata or {}
                indexed_at_str = meta.get("indexed_at", "")

                should_delete = False
                reason = ""

                if col.count() == 0:
                    should_delete = True
                    reason = "Empty collection"

                elif col.count() < min_count and min_count > 0:
                    should_delete = True
                    reason = f"Below min_count ({col.count()} < {min_count})"

                elif indexed_at_str:
                    try:
                        indexed_at = datetime.fromisoformat(indexed_at_str)
                        if indexed_at < cutoff_date:
                            should_delete = True
                            reason = f"Older than {max_age_days} days"
                    except ValueError:
                        pass

                if should_delete:
                    candidates.append(
                        {
                            "name": col.name,
                            "count": col.count(),
                            "reason": reason,
                        }
                    )

            for candidate in candidates:
                if not dry_run:
                    try:
                        self._client.delete_collection(candidate["name"])
                        deleted_count += 1
                        logger.info(
                            "Collection deleted",
                            name=candidate["name"],
                            reason=candidate["reason"],
                        )
                    except Exception as e:
                        logger.error(
                            "Failed to delete collection",
                            name=candidate["name"],
                            error=str(e),
                        )

            return {
                "dry_run": dry_run,
                "candidates": candidates,
                "deleted": deleted_count if not dry_run else 0,
                "would_delete": len(candidates),
            }

        except Exception as e:
            logger.error("Cleanup failed", error=str(e))
            return {"error": str(e), "deleted": deleted_count}

    def optimize_collection(self, collection_name: str) -> dict:
        """優化 collection 索引。

        ChromaDB 使用 HNSW 索引，可以透過重建索引來優化。

        Args:
            collection_name: Collection 名稱

        Returns:
            優化結果
        """
        if not self._lazy_init():
            return {"error": "Not initialized"}

        try:
            collection = self._client.get_collection(collection_name)
            original_count = collection.count()

            if original_count == 0:
                return {"status": "skipped", "reason": "Empty collection"}

            all_data = collection.get(include=["embeddings", "documents", "metadatas"])

            if not all_data["ids"]:
                return {"status": "skipped", "reason": "No data"}

            original_metadata = collection.metadata

            optimized_metadata = original_metadata.copy() if original_metadata else {}
            optimized_metadata.update(
                {
                    "hnsw:space": "cosine",
                    "hnsw:construction_ef": 200,
                    "hnsw:M": 16,
                }
            )

            self._client.delete_collection(collection_name)

            new_collection = self._client.create_collection(
                name=collection_name,
                metadata=optimized_metadata,
            )

            if all_data["embeddings"]:
                new_collection.add(
                    ids=all_data["ids"],
                    embeddings=all_data["embeddings"],
                    documents=all_data["documents"],
                    metadatas=all_data["metadatas"],
                )

            logger.info(
                "Collection optimized",
                name=collection_name,
                count=new_collection.count(),
            )

            return {
                "status": "success",
                "collection": collection_name,
                "count": new_collection.count(),
                "optimized_metadata": optimized_metadata,
            }

        except Exception as e:
            logger.error("Optimization failed", error=str(e))
            return {"status": "error", "error": str(e)}

    def get_storage_info(self) -> dict:
        """取得儲存空間資訊。"""
        if not self._lazy_init():
            return {"error": "Not initialized"}

        try:
            total_size = 0

            for root, dirs, files in os.walk(self.persist_directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    total_size += os.path.getsize(file_path)

            collections = self._client.list_collections()
            total_vectors = sum(col.count() for col in collections)

            return {
                "persist_directory": self.persist_directory,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "collections_count": len(collections),
                "total_vectors": total_vectors,
            }

        except Exception as e:
            return {"error": str(e)}

    def health_check(self) -> dict:
        """健康檢查。"""
        result = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "checks": {},
        }

        if not self._lazy_init():
            result["status"] = "unhealthy"
            result["checks"]["initialization"] = "failed"
            return result

        result["checks"]["initialization"] = "passed"

        try:
            collections = self._client.list_collections()
            result["checks"]["list_collections"] = "passed"
            result["checks"]["collections_count"] = len(collections)
        except Exception as e:
            result["checks"]["list_collections"] = f"failed: {str(e)}"
            result["status"] = "degraded"

        storage_info = self.get_storage_info()
        if "error" not in storage_info:
            result["checks"]["storage_accessible"] = "passed"
            result["storage"] = storage_info
        else:
            result["checks"]["storage_accessible"] = "failed"
            result["status"] = "degraded"

        return result


chroma_optimizer = ChromaDBOptimizer()
