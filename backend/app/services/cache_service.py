"""
LLM Response Cache Service

提供語義相似度快取機制，避免重複呼叫 LLM。
支援 DiskCache（本地）與 Redis（分散式）後端。

Features:
- 語義相似度比對（使用 BGE-M3 嵌入）
- TTL 過期機制
- 統計與監控
- 自動清理過期項目
"""

import hashlib
import json
import os
import time
from typing import Any, Optional

import numpy as np
import structlog
from diskcache import FanoutCache
from sentence_transformers import SentenceTransformer

from app.core.config import settings

logger = structlog.get_logger()

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data"
)
CACHE_DIR = os.path.join(DATA_DIR, "llm_cache")


class SemanticCache:
    """語義相似度快取服務。

    使用向量嵌入計算查詢相似度，而非精確字串匹配。
    這樣可以命中「語意相同但用詞不同」的查詢。
    """

    def __init__(
        self,
        cache_dir: str = CACHE_DIR,
        similarity_threshold: float = 0.95,
        ttl_seconds: int = 3600,
        max_cache_size: int = 1000,
    ):
        """初始化快取服務。

        Args:
            cache_dir: 快取儲存目錄
            similarity_threshold: 相似度閾值（0-1），高於此值視為命中
            ttl_seconds: 快取過期時間（秒）
            max_cache_size: 最大快取項目數
        """
        self.cache_dir = cache_dir
        self.similarity_threshold = similarity_threshold
        self.ttl_seconds = ttl_seconds
        self.max_cache_size = max_cache_size

        os.makedirs(cache_dir, exist_ok=True)

        self._cache: FanoutCache = FanoutCache(
            directory=cache_dir,
            shards=8,
            timeout=1,
            size_limit=500 * 1024 * 1024,
        )

        self._embedder: Optional[SentenceTransformer] = None
        self._embedder_name = "BAAI/bge-m3"
        self._initialized = False

        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
        }

    def _lazy_init(self) -> bool:
        """延遲初始化嵌入模型。"""
        if self._initialized:
            return True

        try:
            logger.info("Initializing SemanticCache embedder")

            device = "cpu"
            try:
                import torch

                if torch.backends.mps.is_available():
                    device = "mps"
                elif torch.cuda.is_available():
                    device = "cuda"
            except ImportError:
                pass

            self._embedder = SentenceTransformer(self._embedder_name, device=device)
            self._initialized = True

            logger.info("SemanticCache initialized", device=device)
            return True

        except Exception as e:
            logger.error("Failed to initialize SemanticCache", error=str(e))
            return False

    def _compute_embedding(self, text: str) -> np.ndarray:
        """計算文字的嵌入向量。"""
        if not self._lazy_init():
            raise RuntimeError("SemanticCache not initialized")

        embedding = self._embedder.encode(text, normalize_embeddings=True)
        return embedding

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """計算餘弦相似度。"""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

    def _generate_cache_key(
        self, prompt: str, system_prompt: str = "", model: str = ""
    ) -> str:
        """生成快取鍵（使用 MD5 hash）。"""
        content = f"{system_prompt}|{prompt}|{model}"
        return hashlib.md5(content.encode()).hexdigest()

    def get(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str = "",
    ) -> Optional[dict]:
        """查詢快取。

        使用語義相似度比對，而非精確匹配。
        如果找到相似度超過閾值的項目，返回該項目。

        Args:
            prompt: 使用者提示
            system_prompt: 系統提示
            model: 模型名稱

        Returns:
            命中時返回 {"response": str, "cached_at": float, "similarity": float}
            未命中時返回 None
        """
        if not self._lazy_init():
            return None

        try:
            prompt_embedding = self._compute_embedding(prompt)
            exact_key = self._generate_cache_key(prompt, system_prompt, model)

            if exact_key in self._cache:
                cached = self._cache[exact_key]
                if time.time() - cached["timestamp"] < self.ttl_seconds:
                    self._stats["hits"] += 1
                    logger.debug("Cache exact hit", key=exact_key)
                    return {
                        "response": cached["response"],
                        "cached_at": cached["timestamp"],
                        "similarity": 1.0,
                        "match_type": "exact",
                    }

            for key in list(self._cache.iterkeys()):
                try:
                    cached = self._cache[key]
                    if time.time() - cached["timestamp"] >= self.ttl_seconds:
                        del self._cache[key]
                        self._stats["evictions"] += 1
                        continue

                    if cached.get("model") != model:
                        continue

                    if cached.get("system_prompt") != system_prompt:
                        continue

                    cached_embedding = np.array(cached["embedding"])
                    similarity = self._cosine_similarity(
                        prompt_embedding, cached_embedding
                    )

                    if similarity >= self.similarity_threshold:
                        self._stats["hits"] += 1
                        logger.debug(
                            "Cache semantic hit",
                            key=key,
                            similarity=similarity,
                        )
                        return {
                            "response": cached["response"],
                            "cached_at": cached["timestamp"],
                            "similarity": similarity,
                            "match_type": "semantic",
                        }

                except Exception:
                    continue

            self._stats["misses"] += 1
            return None

        except Exception as e:
            logger.error("Cache lookup failed", error=str(e))
            return None

    def set(
        self,
        prompt: str,
        response: str,
        system_prompt: str = "",
        model: str = "",
    ) -> bool:
        """設定快取。

        Args:
            prompt: 使用者提示
            response: LLM 回應
            system_prompt: 系統提示
            model: 模型名稱

        Returns:
            是否成功設定快取
        """
        if not self._lazy_init():
            return False

        try:
            key = self._generate_cache_key(prompt, system_prompt, model)
            embedding = self._compute_embedding(prompt)

            self._cache[key] = {
                "prompt": prompt[:500],
                "response": response,
                "system_prompt": system_prompt[:200],
                "model": model,
                "embedding": embedding.tolist(),
                "timestamp": time.time(),
            }

            logger.debug("Cache set", key=key)
            return True

        except Exception as e:
            logger.error("Cache set failed", error=str(e))
            return False

    def clear(self) -> int:
        """清空快取。

        Returns:
            清除的項目數量
        """
        count = 0
        try:
            for key in list(self._cache.iterkeys()):
                del self._cache[key]
                count += 1
            logger.info("Cache cleared", count=count)
            return count
        except Exception as e:
            logger.error("Cache clear failed", error=str(e))
            return count

    def cleanup_expired(self) -> int:
        """清理過期項目。

        Returns:
            清除的項目數量
        """
        count = 0
        try:
            for key in list(self._cache.iterkeys()):
                cached = self._cache.get(key)
                if (
                    cached
                    and time.time() - cached.get("timestamp", 0) >= self.ttl_seconds
                ):
                    del self._cache[key]
                    count += 1

            if count > 0:
                logger.info("Cache cleanup completed", evicted=count)
            return count

        except Exception as e:
            logger.error("Cache cleanup failed", error=str(e))
            return count

    def get_stats(self) -> dict:
        """取得快取統計資訊。"""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0

        cache_size = 0
        try:
            cache_size = len(list(self._cache.iterkeys()))
        except Exception:
            pass

        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "evictions": self._stats["evictions"],
            "hit_rate": hit_rate,
            "cache_size": cache_size,
            "ttl_seconds": self.ttl_seconds,
            "similarity_threshold": self.similarity_threshold,
        }


semantic_cache = SemanticCache()
