"""
RAG Base — shared state, lazy initialization, and low-level helpers.
All other RAG mixins depend on this class.
"""

import asyncio
import hashlib
import os
from concurrent.futures import ThreadPoolExecutor

import chromadb
import structlog

try:
    import torch
except ImportError:
    torch = None

from app.services.context_compressor import ContextCompressor
from app.services.semantic_chunker import SemanticChunker
from sentence_transformers import CrossEncoder, SentenceTransformer
from app.core.metrics import CHROMADB_QUERY_LATENCY_SECONDS

logger = structlog.get_logger()

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "data"
)

# Hard cap on search results to prevent memory exhaustion
MAX_N_RESULTS = 100


class RAGBase:
    """Shared state and helpers for the RAG service."""

    def __init__(self, persist_directory: str = None):
        self.persist_directory = persist_directory or os.path.join(
            DATA_DIR, "chroma_db"
        )
        self.collection = None
        self.embedder = None
        self.reranker = None
        self._initialized = False
        self.device = self._get_device()
        self._executor = ThreadPoolExecutor(max_workers=4)
        self.semantic_chunker = None
        self.context_compressor = None

    async def _run_sync(self, func, *args, **kwargs):
        """Run a synchronous function in a thread pool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, lambda: func(*args, **kwargs))

    def _get_device(self) -> str:
        """Auto-detect best available device (MPS > CUDA > CPU)."""
        if torch is None:
            return "cpu"
        if torch.backends.mps.is_available():
            return "mps"
        if torch.cuda.is_available():
            return "cuda"
        return "cpu"

    def _lazy_init(self) -> bool:
        """Lazy initialization of models and ChromaDB client."""
        if self._initialized:
            return True

        try:
            logger.info("Initializing RAG Service", device=self.device)

            from app.services.llm_service import llm_service

            model_name = "BAAI/bge-m3"
            self.embedder = SentenceTransformer(model_name, device=self.device)

            reranker_name = "BAAI/bge-reranker-base"
            self.reranker = CrossEncoder(reranker_name, device=self.device)

            os.makedirs(self.persist_directory, exist_ok=True)
            self.client = chromadb.PersistentClient(path=self.persist_directory)

            self.semantic_chunker = SemanticChunker(
                embedder=self.embedder,
                threshold=0.5,
                min_chunk_size=100,
                max_chunk_size=800,
            )

            self.context_compressor = ContextCompressor(
                embedder=self.embedder,
                llm_service=llm_service,
            )

            self._initialized = True
            return True

        except Exception as e:
            logger.error("RAG init failed", error=str(e))
            return False

    def _get_or_create_collection(
        self, collection_name: str, file_metadata: dict = None
    ):
        if not self._lazy_init():
            return None
        from datetime import datetime

        metadata = {"hnsw:space": "cosine"}
        if file_metadata:
            metadata.update(
                {
                    "file_name": file_metadata.get("file_name", "Unknown"),
                    "file_type": file_metadata.get("file_type", "Unknown"),
                    "indexed_at": datetime.now().isoformat(),
                }
            )
        return self.client.get_or_create_collection(
            name=collection_name, metadata=metadata
        )

    def _chunk_text(
        self, text: str, chunk_size: int = 512, overlap: int = 50
    ) -> list[str]:
        """Fixed-size text chunking with sentence-boundary awareness."""
        chunks = []
        start = 0
        text_len = len(text)
        while start < text_len:
            end = start + chunk_size
            chunk = text[start:end]
            if end < text_len:
                separators = ["\n\n", "。\n", "。", "！", "？", "\n"]
                for sep in separators:
                    last_sep = chunk.rfind(sep)
                    if last_sep > chunk_size // 2:
                        chunk = chunk[: last_sep + len(sep)]
                        end = start + last_sep + len(sep)
                        break
            if chunk.strip():
                chunks.append(chunk.strip())
            start = end - overlap
        return chunks

    @staticmethod
    def _make_collection_name(file_path: str) -> str:
        doc_id = hashlib.md5(file_path.encode()).hexdigest()[:16]
        return f"doc_{doc_id}", doc_id
