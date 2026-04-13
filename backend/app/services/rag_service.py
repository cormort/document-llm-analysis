"""
RAG Service — backward-compatible re-export module.

The implementation has been split into focused sub-modules under app/services/rag/:
  - rag/base.py    : shared state, lazy init, and low-level helpers
  - rag/indexer.py : document indexing, listing, deletion, and reindexing
  - rag/searcher.py: semantic/hybrid search, query expansion, and context pipeline

All existing imports continue to work unchanged:
    from app.services.rag_service import rag_service
    from app.services.rag_service import RAGService
"""

from app.services.rag import RAGService, rag_service

__all__ = ["RAGService", "rag_service"]
