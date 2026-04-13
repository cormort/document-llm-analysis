"""
RAG sub-package — re-exports RAGService and rag_service singleton
so that existing imports continue to work unchanged.
"""

from app.services.rag.base import RAGBase
from app.services.rag.indexer import RAGIndexerMixin
from app.services.rag.searcher import RAGSearcherMixin


class RAGService(RAGIndexerMixin, RAGSearcherMixin, RAGBase):
    """
    RAG Service — composed from focused mixins.

    - RAGBase       : shared state, lazy init, helper methods
    - RAGIndexerMixin : document indexing, listing, deletion, reindexing
    - RAGSearcherMixin: semantic/hybrid search, query expansion, context pipeline
    """


rag_service = RAGService()

__all__ = ["RAGService", "rag_service"]
