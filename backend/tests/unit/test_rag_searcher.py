"""RAG 搜尋的併發安全測試。

原本 `get_optimized_context()` 會呼叫 `switch_to_document()` 改寫共用的
`self.collection`，兩個同時進行的請求會互相污染檢索結果。這裡用 stub client
驗證：查詢路徑不再改寫共用狀態，且每個請求都使用自己指定的 collection。
"""

import asyncio

import pytest

from app.services.rag.searcher import RAGSearcherMixin


class StubEmbedder:
    def encode(self, texts, convert_to_numpy=True):  # noqa: ARG002
        class _Arr:
            def tolist(self):
                return [[0.1, 0.2, 0.3]]

        return _Arr()


class StubCollection:
    def __init__(self, name: str):
        self.name = name
        self.queries: list[int] = []

    def query(self, query_embeddings=None, n_results=5):  # noqa: ARG002
        self.queries.append(1)
        return {
            "documents": [[f"{self.name}-doc"]],
            "distances": [[0.1]],
            "metadatas": [[{"source": self.name}]],
        }

    def get(self, **kwargs):  # noqa: ARG002
        return {"documents": [], "metadatas": []}


class StubClient:
    def __init__(self):
        self.collections = {}

    def get_collection(self, name):
        if name not in self.collections:
            self.collections[name] = StubCollection(name)
        return self.collections[name]

    def create_collection(self, name, metadata=None):  # noqa: ARG002
        return self.get_collection(name)


class StubSearcher(RAGSearcherMixin):
    """只帶搜尋 mixin 的輕量受測物件（不載入 chromadb）。"""

    def __init__(self):
        self.collection = None
        self.embedder = StubEmbedder()
        self.reranker = None
        self.context_compressor = None
        self.client = StubClient()
        self._initialized = True

    def _lazy_init(self) -> bool:
        return True

    async def _run_sync(self, func, *args, **kwargs):
        return func(*args, **kwargs)


@pytest.mark.asyncio
async def test_optimized_context_does_not_mutate_shared_collection():
    searcher = StubSearcher()
    default = StubCollection("default")
    searcher.collection = default

    result = await searcher.get_optimized_context(
        query="問題", collection_name="docA", use_hybrid=False, use_rerank=False
    )

    assert searcher.collection is default, "查詢不應該改寫共用的 self.collection"
    assert result["sources"][0]["metadata"]["source"] == "docA"


@pytest.mark.asyncio
async def test_concurrent_queries_use_their_own_collection():
    searcher = StubSearcher()

    async def run(name: str):
        return await searcher.get_optimized_context(
            query=f"q-{name}", collection_name=name, use_hybrid=True, use_rerank=False
        )

    results = await asyncio.gather(run("docA"), run("docB"), run("docC"))

    sources = {r["sources"][0]["metadata"]["source"] for r in results}
    assert sources == {"docA", "docB", "docC"}, f"檢索結果互相污染: {sources}"


@pytest.mark.asyncio
async def test_search_uses_explicit_collection():
    searcher = StubSearcher()
    searcher.collection = StubCollection("default")

    results = await searcher.search("q", n_results=1, collection_name="docX")

    assert results[0]["source_collection"] == "docX"


@pytest.mark.asyncio
async def test_search_falls_back_to_default_collection():
    searcher = StubSearcher()
    searcher.collection = StubCollection("default")

    results = await searcher.search("q", n_results=1)

    assert results[0]["source_collection"] == "default"


@pytest.mark.asyncio
async def test_missing_collection_returns_empty():
    searcher = StubSearcher()

    class FailingClient(StubClient):
        def get_collection(self, name):
            raise ValueError("not found")

    searcher.client = FailingClient()

    assert await searcher.search("q", collection_name="nope") == []
