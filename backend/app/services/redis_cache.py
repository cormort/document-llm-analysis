"""Redis 分散式快取服務。

提供 Redis 後端的語義快取實作，適合多實例部署環境。

Features:
- 語義相似度快取（與 DiskCache 相同介面）
- 支援分散式部署
- TTL 過期機制
- 自動序列化/反序列化
"""

import hashlib
import json
import os
import time
from typing import Any, Optional

import numpy as np
import structlog

logger = structlog.get_logger()


class RedisCache:
    """Redis 分散式快取服務。"""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        key_prefix: str = "doc_llm:",
        similarity_threshold: float = 0.95,
        ttl_seconds: int = 3600,
    ):
        """初始化 Redis 快取。

        Args:
            redis_url: Redis 連線 URL（如 redis://localhost:6379/0）
            key_prefix: Redis key 前綴
            similarity_threshold: 語義相似度閾值
            ttl_seconds: 快取過期時間（秒）
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.key_prefix = key_prefix
        self.similarity_threshold = similarity_threshold
        self.ttl_seconds = ttl_seconds
        self._redis = None
        self._embedder = None
        self._initialized = False

        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
        }

    def _lazy_init(self) -> bool:
        """延遲初始化 Redis 連線和嵌入模型。"""
        if self._initialized:
            return True

        try:
            import redis
            from sentence_transformers import SentenceTransformer

            self._redis = redis.from_url(self.redis_url, decode_responses=True)
            self._redis.ping()

            device = "cpu"
            try:
                import torch

                if torch.backends.mps.is_available():
                    device = "mps"
                elif torch.cuda.is_available():
                    device = "cuda"
            except ImportError:
                pass

            self._embedder = SentenceTransformer("BAAI/bge-m3", device=device)
            self._initialized = True

            logger.info("RedisCache initialized", url=self.redis_url, device=device)
            return True

        except Exception as e:
            logger.warning(
                "RedisCache initialization failed, falling back to disabled",
                error=str(e),
            )
            return False

    def _compute_embedding(self, text: str) -> np.ndarray:
        """計算文字的嵌入向量。"""
        if not self._lazy_init():
            raise RuntimeError("RedisCache not initialized")

        embedding = self._embedder.encode(text, normalize_embeddings=True)
        return embedding

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """計算餘弦相似度。"""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

    def _generate_cache_key(
        self, prompt: str, system_prompt: str = "", model: str = ""
    ) -> str:
        """生成快取鍵。"""
        content = f"{system_prompt}|{prompt}|{model}"
        return f"{self.key_prefix}{hashlib.md5(content.encode()).hexdigest()}"

    def _serialize_embedding(self, embedding: np.ndarray) -> str:
        """序列化嵌入向量。"""
        return json.dumps(embedding.tolist())

    def _deserialize_embedding(self, data: str) -> np.ndarray:
        """反序列化嵌入向量。"""
        return np.array(json.loads(data), dtype=np.float32)

    def get(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str = "",
    ) -> Optional[dict[str, Any]]:
        """查詢快取。

        Args:
            prompt: 使用者提示
            system_prompt: 系統提示
            model: 模型名稱

        Returns:
            命中時返回快取結果，未命中時返回 None
        """
        if not self._lazy_init():
            return None

        try:
            prompt_embedding = self._compute_embedding(prompt)
            exact_key = self._generate_cache_key(prompt, system_prompt, model)

            cached = self._redis.get(exact_key)
            if cached:
                data = json.loads(cached)
                if time.time() - data["timestamp"] < self.ttl_seconds:
                    self._stats["hits"] += 1
                    logger.debug("Redis cache exact hit", key=exact_key)
                    return {
                        "response": data["response"],
                        "cached_at": data["timestamp"],
                        "similarity": 1.0,
                        "match_type": "exact",
                    }

            for key in self._redis.scan_iter(f"{self.key_prefix}*"):
                if key == exact_key:
                    continue

                cached = self._redis.get(key)
                if not cached:
                    continue

                data = json.loads(cached)
                if time.time() - data["timestamp"] >= self.ttl_seconds:
                    self._redis.delete(key)
                    self._stats["evictions"] += 1
                    continue

                if data.get("model") != model:
                    continue

                cached_embedding = self._deserialize_embedding(data["embedding"])
                similarity = self._cosine_similarity(prompt_embedding, cached_embedding)

                if similarity >= self.similarity_threshold:
                    self._stats["hits"] += 1
                    logger.debug(
                        "Redis cache semantic hit", key=key, similarity=similarity
                    )
                    return {
                        "response": data["response"],
                        "cached_at": data["timestamp"],
                        "similarity": similarity,
                        "match_type": "semantic",
                    }

            self._stats["misses"] += 1
            return None

        except Exception as e:
            logger.error("Redis cache lookup failed", error=str(e))
            return None

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

        try:
            key = self._generate_cache_key(prompt, system_prompt, model)
            embedding = self._compute_embedding(prompt)

            data = {
                "prompt": prompt[:500],
                "response": response,
                "system_prompt": system_prompt[:200],
                "model": model,
                "embedding": self._serialize_embedding(embedding),
                "timestamp": time.time(),
            }

            self._redis.setex(key, self.ttl_seconds, json.dumps(data))

            logger.debug("Redis cache set", key=key)
            return True

        except Exception as e:
            logger.error("Redis cache set failed", error=str(e))
            return False

    def clear(self) -> int:
        """清空快取。"""
        count = 0
        try:
            for key in self._redis.scan_iter(f"{self.key_prefix}*"):
                self._redis.delete(key)
                count += 1
            logger.info("Redis cache cleared", count=count)
            return count
        except Exception as e:
            logger.error("Redis cache clear failed", error=str(e))
            return count

    def get_stats(self) -> dict[str, Any]:
        """取得快取統計資訊。"""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0

        cache_size = 0
        try:
            if self._redis:
                cache_size = len(list(self._redis.scan_iter(f"{self.key_prefix}*")))
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
            "backend": "redis",
        }


def get_cache_backend() -> RedisCache:
    """取得快取後端實例。"""
    return RedisCache()


redis_cache = RedisCache()
