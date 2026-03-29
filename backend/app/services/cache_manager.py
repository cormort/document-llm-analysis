"""統一快取管理器。

根據環境配置自動選擇快取後端：
- 本地開發：DiskCache
- 生產環境：Redis（如有配置）

Features:
- 自動後端切換
- 統一 API 介面
- 降級處理
"""

import os
from typing import Any, Optional

import structlog

logger = structlog.get_logger()


class CacheManager:
    """統一快取管理器。"""

    def __init__(self, prefer_redis: bool = True):
        """初始化快取管理器。

        Args:
            prefer_redis: 是否優先使用 Redis（如有配置）
        """
        self._backend = None
        self._backend_name = "none"
        self._prefer_redis = prefer_redis
        self._initialized = False

    def _lazy_init(self) -> bool:
        """延遲初始化快取後端。"""
        if self._initialized:
            return self._backend is not None

        redis_url = os.getenv("REDIS_URL", "")

        if self._prefer_redis and redis_url:
            try:
                from app.services.redis_cache import RedisCache

                self._backend = RedisCache(redis_url=redis_url)
                self._backend_name = "redis"

                if self._backend._lazy_init():
                    logger.info("CacheManager: Using Redis backend", url=redis_url)
                    self._initialized = True
                    return True
                else:
                    logger.warning(
                        "CacheManager: Redis init failed, falling back to DiskCache"
                    )
                    self._backend = None
            except ImportError:
                logger.warning(
                    "CacheManager: Redis not available, falling back to DiskCache"
                )

        if self._backend is None:
            from app.services.cache_service import SemanticCache

            self._backend = SemanticCache()
            self._backend_name = "diskcache"
            logger.info("CacheManager: Using DiskCache backend")
            self._initialized = True
            return True

        return False

    def get(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str = "",
    ) -> Optional[dict[str, Any]]:
        """查詢快取。"""
        if not self._lazy_init():
            return None
        return self._backend.get(prompt, system_prompt, model)

    def set(
        self,
        prompt: str,
        response: str,
        system_prompt: str = "",
        model: str = "",
    ) -> bool:
        """設定快取。"""
        if not self._lazy_init():
            return False
        return self._backend.set(prompt, response, system_prompt, model)

    def clear(self) -> int:
        """清空快取。"""
        if not self._lazy_init():
            return 0
        return self._backend.clear()

    def get_stats(self) -> dict[str, Any]:
        """取得快取統計資訊。"""
        if not self._lazy_init():
            return {"backend": "none", "error": "Not initialized"}
        stats = self._backend.get_stats()
        stats["backend"] = self._backend_name
        return stats

    @property
    def backend_name(self) -> str:
        """目前使用的後端名稱。"""
        return self._backend_name


cache_manager = CacheManager()
