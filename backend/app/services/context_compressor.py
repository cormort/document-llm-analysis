"""
Context Compressor - Reduce context size while preserving semantic content.

Strategies:
1. Extractive: Keep only sentences most relevant to the query
2. Summary: Use LLM to summarize the context (more token-intensive upfront)
"""

import numpy as np
import structlog

logger = structlog.get_logger()


class ContextCompressor:
    """壓縮 RAG context 以減少 Token 使用"""

    def __init__(self, embedder, llm_service=None):
        """
        Initialize context compressor.

        Args:
            embedder: SentenceTransformer or compatible encoder
            llm_service: Optional LLM service for summary-based compression
        """
        self.embedder = embedder
        self.llm_service = llm_service

    async def compress(
        self,
        context: str,
        query: str,
        target_ratio: float = 0.5,
        method: str = "extractive",  # "extractive" | "summary"
    ) -> dict:
        """
        Compress context to reduce token usage.

        Args:
            context: Original context from RAG retrieval
            query: User query for relevance scoring
            target_ratio: Target compression ratio (0.5 = keep 50%)
            method: Compression method

        Returns:
            dict with keys: compressed_context, original_len, compressed_len, ratio
        """
        if not context:
            return {
                "compressed_context": "",
                "original_len": 0,
                "compressed_len": 0,
                "ratio": 1.0,
            }

        original_len = len(context)

        if method == "extractive":
            compressed = await self._extractive_compress(context, query, target_ratio)
        elif method == "summary" and self.llm_service:
            compressed = await self._summary_compress(context, query, target_ratio)
        else:
            # Fallback: simple truncation
            target_len = int(original_len * target_ratio)
            compressed = context[:target_len]

        compressed_len = len(compressed)

        logger.info(
            "Context compressed",
            method=method,
            original=original_len,
            compressed=compressed_len,
            ratio=compressed_len / original_len if original_len > 0 else 1.0,
        )

        return {
            "compressed_context": compressed,
            "original_len": original_len,
            "compressed_len": compressed_len,
            "ratio": compressed_len / original_len if original_len > 0 else 1.0,
        }

    async def _extractive_compress(
        self, context: str, query: str, target_ratio: float
    ) -> str:
        """
        Extractive compression: Keep sentences most relevant to query.

        Algorithm:
        1. Split context into sentences
        2. Embed query and all sentences
        3. Score sentences by similarity to query
        4. Keep top-k sentences that fit target ratio
        """

        # Split into sentences (preserve chunk headers)
        lines = context.split("\n")
        sentences = []
        current_header = ""

        for line in lines:
            if line.startswith("[") and "]" in line:
                # This is a chunk header
                current_header = line
            elif line.strip():
                sentences.append((current_header, line.strip()))

        if len(sentences) <= 2:
            return context

        # Embed query and sentences
        try:
            query_embedding = self.embedder.encode(
                [query], show_progress_bar=False, convert_to_numpy=True
            )[0]

            sentence_texts = [s[1] for s in sentences]
            sentence_embeddings = self.embedder.encode(
                sentence_texts, show_progress_bar=False, convert_to_numpy=True
            )
        except Exception as e:
            logger.warning("Embedding failed in compression", error=str(e))
            return context

        # Score by cosine similarity
        scores = []
        for i, emb in enumerate(sentence_embeddings):
            sim = self._cosine_similarity(query_embedding, emb)
            scores.append((i, sim))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        # Select sentences up to target ratio
        target_len = int(len(context) * target_ratio)
        selected_indices = set()
        current_len = 0

        for idx, score in scores:
            sentence = sentences[idx][1]
            if current_len + len(sentence) <= target_len:
                selected_indices.add(idx)
                current_len += len(sentence) + 1  # +1 for space

        # Rebuild context preserving order
        result_parts = []
        last_header = ""
        for i, (header, sentence) in enumerate(sentences):
            if i in selected_indices:
                if header and header != last_header:
                    result_parts.append(header)
                    last_header = header
                result_parts.append(sentence)

        return "\n".join(result_parts)

    async def _summary_compress(
        self, context: str, query: str, target_ratio: float
    ) -> str:
        """
        Summary compression: Use LLM to summarize context.

        More expensive but can achieve better compression with semantic preservation.
        """
        if not self.llm_service:
            return context

        target_chars = int(len(context) * target_ratio)

        prompt = f"""請將以下內容壓縮摘要，保留與問題最相關的資訊。
目標長度約 {target_chars} 字元。

問題: {query}

原始內容:
{context}

請直接輸出壓縮後的內容，不要加任何說明:"""

        try:
            result = await self.llm_service.generate_text(prompt)
            if result:
                return result.strip()
            return context
        except Exception as e:
            logger.warning("Summary compression failed", error=str(e))
            return context

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
