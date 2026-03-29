"""
Semantic Chunker - Split text based on semantic boundaries.

Uses embedding similarity to find natural breakpoints in text,
resulting in more coherent chunks than fixed-size splitting.
"""

import numpy as np
import structlog

logger = structlog.get_logger()


class SemanticChunker:
    """基於語意相似度的文本分段器"""

    def __init__(
        self,
        embedder,
        threshold: float = 0.5,
        min_chunk_size: int = 100,
        max_chunk_size: int = 1000,
    ):
        """
        Initialize semantic chunker.

        Args:
            embedder: SentenceTransformer or compatible encoder
            threshold: Similarity threshold - lower = more splits (0.3-0.7 typical)
            min_chunk_size: Minimum characters per chunk
            max_chunk_size: Maximum characters per chunk
        """
        self.embedder = embedder
        self.threshold = threshold
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size

    def _split_into_sentences(self, text: str) -> list[str]:
        """
        Split text into sentences using common delimiters.
        Handles Chinese and English punctuation.
        """
        import re

        # Common sentence-ending patterns
        # Split by punctuation but keep the punctuation using look-behind
        # To avoid variable width look-behind, we split on the space AFTER punctuation
        # or use a capturing group and reassemble.
        pattern = r'([。！？.!?]["\'）\)]?\s*)'
        parts = re.split(pattern, text)
        
        # Reassemble: parts will be [text, punct, text, punct, ...]
        sentences = []
        for i in range(0, len(parts) - 1, 2):
            sentences.append(parts[i] + parts[i+1])
        if len(parts) % 2 == 1 and parts[-1]:
            sentences.append(parts[-1])
            
        return [s.strip() for s in sentences if s.strip()]

    def chunk(self, text: str) -> list[str]:
        """
        Split text into semantically coherent chunks.

        Algorithm:
        1. Split into sentences
        2. Embed each sentence
        3. Calculate cosine similarity between adjacent sentences
        4. Split where similarity drops below threshold
        5. Merge small chunks, split large chunks

        Returns:
            List of text chunks
        """
        if not text or len(text) < self.min_chunk_size:
            return [text] if text else []

        # 1. Split into sentences
        sentences = self._split_into_sentences(text)
        if len(sentences) <= 1:
            return self._split_by_size(text)

        logger.debug("Semantic chunking", sentences=len(sentences))

        # 2. Embed sentences (batch)
        try:
            embeddings = self.embedder.encode(
                sentences, show_progress_bar=False, convert_to_numpy=True
            )
        except Exception as e:
            logger.warning("Embedding failed, falling back to size-based", error=str(e))
            return self._split_by_size(text)

        # 3. Calculate similarity between adjacent sentences
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = self._cosine_similarity(embeddings[i], embeddings[i + 1])
            similarities.append(sim)

        # 4. Find split points (where similarity < threshold)
        split_indices = [0]  # Always start with 0
        for i, sim in enumerate(similarities):
            if sim < self.threshold:
                split_indices.append(i + 1)
        split_indices.append(len(sentences))  # Always end with last

        # 5. Create chunks from split points
        raw_chunks = []
        for i in range(len(split_indices) - 1):
            start_idx = split_indices[i]
            end_idx = split_indices[i + 1]
            chunk_text = " ".join(sentences[start_idx:end_idx])
            raw_chunks.append(chunk_text)

        # 6. Merge small chunks, split large chunks
        final_chunks = self._balance_chunks(raw_chunks)

        logger.debug(
            "Semantic chunking complete",
            raw_chunks=len(raw_chunks),
            final_chunks=len(final_chunks),
        )

        return final_chunks

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def _balance_chunks(self, chunks: list[str]) -> list[str]:
        """Merge small chunks and split large chunks."""
        result = []
        buffer = ""

        for chunk in chunks:
            combined = buffer + (" " if buffer else "") + chunk

            if len(combined) < self.min_chunk_size:
                buffer = combined
            elif len(combined) > self.max_chunk_size:
                # First, flush buffer if not empty
                if buffer:
                    result.append(buffer)
                    buffer = ""
                # Split the large chunk
                result.extend(self._split_by_size(chunk))
            else:
                if buffer:
                    result.append(buffer)
                result.append(chunk)
                buffer = ""

        # Don't forget remaining buffer
        if buffer:
            if result and len(result[-1]) + len(buffer) < self.max_chunk_size:
                result[-1] = result[-1] + " " + buffer
            else:
                result.append(buffer)

        return result

    def _split_by_size(self, text: str) -> list[str]:
        """Fallback: split by size with overlap."""
        chunks = []
        start = 0
        overlap = 50

        while start < len(text):
            end = start + self.max_chunk_size

            # Try to find a natural break point
            if end < len(text):
                # Look for sentence endings
                for sep in ["。", "！", "？", ".", "!", "?", "\n", " "]:
                    last_sep = text[start:end].rfind(sep)
                    if last_sep > self.min_chunk_size:
                        end = start + last_sep + 1
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - overlap

        return chunks
