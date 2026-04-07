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
from app.services.graph_rag_service import graph_rag_service
from app.services.llm_service import llm_service
from app.services.semantic_chunker import SemanticChunker
from sentence_transformers import CrossEncoder, SentenceTransformer
from app.core.metrics import CHROMADB_QUERY_LATENCY_SECONDS

logger = structlog.get_logger()

# Define data directory for backend
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data"
)


class RAGService:
    def __init__(self, persist_directory: str = None):
        """Initialize RAG Service"""
        self.persist_directory = persist_directory or os.path.join(
            DATA_DIR, "chroma_db"
        )
        self.collection = None
        self.embedder = None
        self.reranker = None
        self._initialized = False
        self.device = self._get_device()
        self._executor = ThreadPoolExecutor(max_workers=4)
        self.semantic_chunker = None  # Lazy init with embedder
        self.context_compressor = None  # Lazy init with embedder

    async def _run_sync(self, func, *args, **kwargs):
        """Run sync function in thread pool"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, lambda: func(*args, **kwargs))

    def _get_device(self):
        """Auto-detect device (MPS > CUDA > CPU)"""
        if torch.backends.mps.is_available():
            return "mps"
        elif torch.cuda.is_available():
            return "cuda"
        else:
            return "cpu"

    def _lazy_init(self):
        """Lazy initialization of models"""
        if self._initialized:
            return True

        try:
            logger.info("Initializing RAG Service", device=self.device)

            # BAAI/bge-m3: 多語言、支援 8192 tokens 長文本
            model_name = "BAAI/bge-m3"
            self.embedder = SentenceTransformer(model_name, device=self.device)

            # Load Re-ranker
            reranker_name = "BAAI/bge-reranker-base"
            self.reranker = CrossEncoder(reranker_name, device=self.device)

            os.makedirs(self.persist_directory, exist_ok=True)
            self.client = chromadb.PersistentClient(path=self.persist_directory)

            # Initialize semantic chunker with embedder
            self.semantic_chunker = SemanticChunker(
                embedder=self.embedder,
                threshold=0.5,
                min_chunk_size=100,
                max_chunk_size=800,
            )

            # Initialize context compressor
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

    async def index_document(
        self,
        file_path: str,
        content: str,
        metadata: dict = None,
        build_graph: bool = True,
        use_langextract: bool = True,
        chunking_strategy: str = "semantic",  # "semantic" or "fixed"
    ) -> dict[str, any]:
        """Index document with metadata and optional graph building.

        Args:
            file_path: Path to the document file
            content: Text content to index
            metadata: Optional metadata dict
            build_graph: Whether to build knowledge graph
            use_langextract: Whether to use LangExtract for enhanced extraction
            chunking_strategy: "semantic" for embedding-based, "fixed" for size-based
        """
        if not self._lazy_init():
            return {"success": False, "error": "RAG Service not initialized"}

        doc_id = hashlib.md5(file_path.encode()).hexdigest()[:16]
        collection_name = f"doc_{doc_id}"

        # Try to import LangExtract service
        langextract_available = False
        langextract_service = None
        if use_langextract:
            try:
                from app.services.langextract_service import (
                    langextract_service as lx_service,
                )

                langextract_service = lx_service
                langextract_available = lx_service.is_available
            except ImportError:
                logger.warning("LangExtract not available, using fallback")

        try:
            base_metadata = {
                "file_type": os.path.splitext(file_path)[1],
                "file_name": os.path.basename(file_path),
                "doc_id": doc_id,
            }
            if metadata:
                base_metadata.update(metadata)

            # ========== LangExtract: 產生 Rich Metadata ==========
            extracted_tags = []
            if langextract_available and langextract_service:
                try:
                    # 使用前 8000 字元提取 metadata
                    sample_text = content[:8000]
                    extract_result = await langextract_service.extract(
                        text=sample_text,
                        extraction_type="key_facts",
                    )
                    if extract_result.get("success"):
                        classes_found = extract_result.get("classes_found", [])
                        total_count = extract_result.get("total_count", 0)
                        base_metadata.update(
                            {
                                "langextract_classes": ",".join(classes_found),
                                "langextract_count": str(total_count),
                            }
                        )
                        extracted_tags = classes_found
                        logger.info(
                            "LangExtract metadata generated",
                            classes=classes_found,
                            count=total_count,
                        )
                except Exception as e:
                    logger.warning(
                        "LangExtract metadata extraction failed", error=str(e)
                    )

            try:
                self.client.delete_collection(collection_name)
            except Exception:
                pass

            collection = self._get_or_create_collection(collection_name, base_metadata)

            # Choose chunking strategy
            if chunking_strategy == "semantic" and self.semantic_chunker:
                logger.info("Using semantic chunking")
                chunks = self.semantic_chunker.chunk(content)
            else:
                logger.info("Using fixed-size chunking")
                chunks = self._chunk_text(content)

            if not chunks:
                return {"success": False, "error": "Document has no content"}

            logger.info("Generating embeddings", count=len(chunks))
            embeddings = self.embedder.encode(
                chunks, batch_size=32, show_progress_bar=False, convert_to_numpy=True
            ).tolist()

            metadatas = [
                {
                    "source": file_path,
                    "doc_id": doc_id,
                    "chunk_id": f"{doc_id}_{i}",
                    "chunk_text_preview": chunk[:100],
                }
                for i, chunk in enumerate(chunks)
            ]

            collection.add(
                ids=[f"chunk_{i}" for i in range(len(chunks))],
                embeddings=embeddings,
                documents=chunks,
                metadatas=metadatas,
            )
            self.collection = collection

            # ========== 建立 Knowledge Graph ==========
            if build_graph:
                logger.info("Building Knowledge Graph", chunks=len(chunks))
                process_limit = min(len(chunks), 20)
                for i in range(process_limit):
                    chunk = chunks[i]
                    cid = f"{doc_id}_{i}"

                    extraction_data = None

                    # 優先使用 LangExtract (更精確)
                    if langextract_available and langextract_service:
                        try:
                            lx_result = await langextract_service.extract(
                                text=chunk,
                                extraction_type="entities",
                            )
                            if lx_result.get("success"):
                                extraction_data = self._convert_langextract_to_triplets(
                                    lx_result
                                )
                        except Exception as e:
                            logger.warning(
                                "LangExtract entity extraction failed",
                                chunk=i,
                                error=str(e),
                            )

                    # Fallback 到原有 LLM 提取
                    if not extraction_data:
                        extraction_data = await llm_service.extract_entities(chunk)

                    if extraction_data:
                        graph_rag_service.add_triplets(extraction_data, cid)

                graph_rag_service.save_graph()

            return {
                "success": True,
                "collection_name": collection_name,
                "chunks_count": len(chunks),
                "extracted_tags": extracted_tags,  # 回傳供 UI 使用
            }

        except Exception as e:
            logger.error("Error indexing document", error=str(e))
            return {"success": False, "error": str(e)}

    def _convert_langextract_to_triplets(self, lx_result: dict) -> dict:
        """Convert LangExtract output to triplet format for graph_rag_service."""
        entities = []
        relations = []

        extractions = lx_result.get("extractions", [])
        for ext in extractions:
            ext_class = ext.get("class", "")
            ext_text = ext.get("text", "")
            attributes = ext.get("attributes", {})

            if ext_class in ["person", "organization", "location", "product", "event"]:
                entities.append(
                    {
                        "name": ext_text,
                        "type": ext_class,
                        "description": str(attributes),
                        "aliases": [],
                    }
                )
            elif ext_class in ["relationship", "relation"]:
                # 嘗試解析關係
                if "subject" in attributes and "object" in attributes:
                    relations.append(
                        {
                            "subject": attributes.get("subject", ""),
                            "object": attributes.get("object", ""),
                            "relation": ext_text,
                        }
                    )

        return {"entities": entities, "relations": relations}

    async def list_indexed_documents(self) -> list[dict]:
        """List all indexed document collections"""
        if not self._lazy_init():
            return []
        try:
            collections = self.client.list_collections()
            results = []
            for col in collections:
                # ChromaDB collection object, we need metadata
                meta = col.metadata or {}
                results.append(
                    {
                        "collection_name": col.name,
                        "file_name": meta.get("file_name", "Unknown"),
                        "file_type": meta.get("file_type", "Unknown"),
                        "indexed_at": meta.get("indexed_at", "Unknown"),
                        "count": col.count(),
                    }
                )
            return results
        except Exception as e:
            logger.error("List collections failed", error=str(e))
            return []

    def delete_document_index(self, collection_name: str) -> bool:
        """Delete a document index"""
        if not self._lazy_init():
            return False
        try:
            self.client.delete_collection(collection_name)
            if self.collection and self.collection.name == collection_name:
                self.collection = None
            return True
        except Exception as e:
            logger.error(f"Delete collection {collection_name} failed", error=str(e))
            return False

    async def reindex_all_documents(self, progress_callback=None) -> dict:
        """
        Rebuild embeddings for all indexed documents using current model.
        Useful after switching embedding models.

        Args:
            progress_callback: Optional callback(current, total, collection_name)
        """
        if not self._lazy_init():
            return {"success": False, "error": "Service not initialized"}

        try:
            collections = self.client.list_collections()
            total = len(collections)

            if total == 0:
                return {
                    "success": True,
                    "reindexed": 0,
                    "message": "No documents to reindex",
                }

            results = []
            for i, col in enumerate(collections):
                col_name = col.name
                meta = col.metadata or {}

                if progress_callback:
                    progress_callback(i + 1, total, meta.get("file_name", col_name))

                try:
                    # 1. Get all documents from collection
                    all_docs = col.get(include=["documents", "metadatas"])
                    if not all_docs or not all_docs["documents"]:
                        results.append(
                            {
                                "collection": col_name,
                                "status": "skipped",
                                "reason": "empty",
                            }
                        )
                        continue

                    documents = all_docs["documents"]
                    metadatas = all_docs["metadatas"] or [{}] * len(documents)
                    ids = all_docs["ids"]

                    # 2. Generate new embeddings with current model
                    logger.info(f"Re-embedding {len(documents)} chunks for {col_name}")
                    new_embeddings = self.embedder.encode(
                        documents,
                        batch_size=32,
                        show_progress_bar=False,
                        convert_to_numpy=True,
                    ).tolist()

                    # 3. Delete old collection
                    self.client.delete_collection(col_name)

                    # 4. Recreate collection with same metadata
                    new_col = self.client.get_or_create_collection(
                        name=col_name, metadata=meta
                    )

                    # 5. Add documents with new embeddings
                    new_col.add(
                        ids=ids,
                        embeddings=new_embeddings,
                        documents=documents,
                        metadatas=metadatas,
                    )

                    results.append(
                        {
                            "collection": col_name,
                            "file_name": meta.get("file_name", "Unknown"),
                            "status": "success",
                            "chunks": len(documents),
                        }
                    )

                except Exception as e:
                    results.append(
                        {"collection": col_name, "status": "error", "error": str(e)}
                    )
                    logger.error(f"Reindex failed for {col_name}", error=str(e))

            success_count = sum(1 for r in results if r.get("status") == "success")
            return {
                "success": True,
                "reindexed": success_count,
                "total": total,
                "details": results,
            }

        except Exception as e:
            logger.error("Reindex all failed", error=str(e))
            return {"success": False, "error": str(e)}

    def switch_to_document(self, collection_name: str) -> bool:
        """Switch active collection"""
        if not self._lazy_init():
            return False
        try:
            self.collection = self.client.get_collection(collection_name)
            return True
        except Exception as e:
            logger.error(f"Switch to {collection_name} failed", error=str(e))
            return False

    async def search(
        self, query: str, n_results: int = 5, collection_name: str = None
    ) -> list[dict]:
        """Basic semantic search on a specific or default collection"""
        target_collection = self.collection

        if collection_name:
            if not self._lazy_init():
                return []
            try:
                target_collection = self.client.get_collection(collection_name)
            except Exception:
                logger.warning(f"Collection {collection_name} not found")
                return []

        if not target_collection:
            logger.warning("No collection available for search")
            return []

        try:
            query_embedding = await self._run_sync(
                self.embedder.encode, [query], convert_to_numpy=True
            )
            query_embedding = query_embedding.tolist()
            with CHROMADB_QUERY_LATENCY_SECONDS.labels(
                collection=target_collection.name
            ).time():
                results = target_collection.query(
                    query_embeddings=query_embedding, n_results=n_results
                )

            formatted = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    formatted.append(
                        {
                            "content": doc,
                            "distance": results["distances"][0][i]
                            if results["distances"]
                            else 0,
                            "metadata": results["metadatas"][0][i]
                            if results["metadatas"]
                            else {},
                            "source_collection": target_collection.name,
                        }
                    )
            return formatted
        except Exception as e:
            logger.error("Search failed", error=str(e))
            return []

    async def search_across_collections(
        self,
        query: str,
        collection_names: list[str],
        n_results: int = 5,
        use_rerank: bool = True,
    ) -> list[dict]:
        """Search across multiple collections and merge results"""
        all_results = []
        # Search each collection (parallel execution)
        tasks = [
            self.search(query, n_results=n_results, collection_name=name)
            for name in collection_names
        ]
        results_list = await asyncio.gather(*tasks)
        for results in results_list:
            all_results.extend(results)

        # Deduplication based on chunk_id or content? Content might be safer.
        # Actually standard RAG dedups by chunk ID if from same doc, but here we have diff docs.
        # Just sort by distance/score.

        # If reranking
        if use_rerank and self.reranker and all_results:
            pairs = [[query, r["content"]] for r in all_results]
            # Limit rerank to top 50 global
            if len(pairs) > 50:
                # Pre-sort by distance (approx)
                all_results.sort(key=lambda x: x.get("distance", 1.0))
                all_results = all_results[:50]
                pairs = [[query, r["content"]] for r in all_results]

            scores = await self._run_sync(
                self.reranker.predict, pairs, show_progress_bar=False
            )
            ranked = sorted(zip(all_results, scores), key=lambda x: x[1], reverse=True)

            final_results = []
            for result, score in ranked[:n_results]:
                result["rerank_score"] = float(score)
                final_results.append(result)
            return final_results
        else:
            # Sort by distance (ascending = better match)
            all_results.sort(key=lambda x: x.get("distance", 1.0))
            return all_results[:n_results]

    async def search_with_rerank(
        self,
        query: str,
        n_results: int = 5,
        initial_k: int = 20,
        collection_name: str = None,
    ) -> list[dict]:
        """Search with Re-ranking on single collection"""
        initial_results = await self.search(
            query, min(initial_k, 50), collection_name=collection_name
        )
        if not initial_results:
            return []

        if not self.reranker:
            return initial_results[:n_results]

        try:
            pairs = [[query, r["content"]] for r in initial_results]
            scores = await self._run_sync(
                self.reranker.predict, pairs, show_progress_bar=False
            )

            ranked = sorted(
                zip(initial_results, scores), key=lambda x: x[1], reverse=True
            )

            final_results = []
            for result, score in ranked[:n_results]:
                result["rerank_score"] = float(score)
                final_results.append(result)
            return final_results
        except Exception as e:
            logger.error("Re-ranking failed", error=str(e))
            return initial_results[:n_results]

    async def get_context_for_query(
        self,
        query: str,
        n_results: int = 5,
        use_rerank: bool = True,
        use_graph: bool = False,
        tau_a: float = 0.5,
        tau_d: float = 0.45,
        tau_r: float = 0.5,
    ) -> str:
        """
        Get enhanced context for SA-RAG (Async)
        """
        # 1. Vector Search
        results = []
        if use_rerank and self.reranker:
            results = await self.search_with_rerank(query, n_results * 2)
        else:
            results = await self.search(query, n_results * 2)

        # Filter by distance (tau_d)
        filtered_results = []
        for r in results:
            similarity = 1.0 - r.get("distance", 1.0)
            if similarity >= tau_d:
                filtered_results.append(r)

        # 2. Graph Enhancement
        graph_results = []
        rel_texts = []

        if use_graph:
            try:
                # Extract seed entities
                extraction = await llm_service.extract_entities(
                    f"Identify entities: {query}"
                )
                seed_entities = [
                    e["name"] for e in extraction.get("entities", []) if e.get("name")
                ]

                if seed_entities:
                    activated_chunk_ids = graph_rag_service.spreading_activation(
                        seed_entities, threshold=tau_a
                    )
                    if activated_chunk_ids:
                        # Fetch chunks from Chroma
                        if self.collection:
                            target_cids = [
                                cid
                                for cid in activated_chunk_ids
                                if not any(
                                    r["metadata"].get("chunk_id") == cid
                                    for r in filtered_results
                                )
                            ]
                            if target_cids:
                                res = self.collection.get(
                                    where={"chunk_id": {"$in": target_cids[:5]}},
                                    include=["documents", "metadatas"],
                                )
                                if res and res["documents"]:
                                    for i, doc in enumerate(res["documents"]):
                                        graph_results.append(
                                            {
                                                "content": doc,
                                                "metadata": res["metadatas"][i],
                                            }
                                        )

                    # Graph relations
                    for u, v, d in graph_rag_service.graph.edges(data=True):
                        if d.get("weight", 0) >= tau_r and d.get("relation"):
                            rel_texts.append(
                                f"Relation: {u} --({d['relation']})--> {v}"
                            )
            except Exception as e:
                logger.error("Graph enhancement failed", error=str(e))

        # 3. Combine
        context_parts = []
        for i, r in enumerate(filtered_results[:n_results], 1):
            sim = 1.0 - r.get("distance", 1.0)
            context_parts.append(f"[Vector Chunk {i}] (Sim: {sim:.3f})\n{r['content']}")

        for i, r in enumerate(graph_results, 1):
            context_parts.append(f"[Graph Chunk {i}]\n{r['content']}")

        if rel_texts:
            context_parts.append("[Entities]\n" + "\n".join(rel_texts[:5]))

        return "\n\n".join(context_parts)

    async def get_optimized_context(
        self,
        query: str,
        collection_name: str = None,
        n_results: int = 5,
        use_rerank: bool = True,
        use_hybrid: bool = True,
        use_query_expansion: bool = False,
        use_graph: bool = False,
        use_compression: bool = False,
        compression_method: str = "extractive",  # "extractive" | "summary"
        compression_ratio: float = 0.5,
        fast_config: dict = None,
    ) -> dict:
        """
        Enhanced RAG query with full optimization pipeline.

        Pipeline:
        1. Query Expansion (optional) - Generate query variants
        2. Hybrid Search - Combine vector + keyword search
        3. Rerank - Cross-encoder reranking
        4. Context Assembly - Format for LLM

        Returns:
            dict with keys: context, sources, stats
        """
        stats = {
            "original_query": query,
            "expanded_queries": [],
            "search_method": "vector",
            "total_candidates": 0,
            "final_results": 0,
        }

        # Switch to target collection if specified
        if collection_name:
            self.switch_to_document(collection_name)

        # 1. Query Expansion
        queries = [query]
        if use_query_expansion:
            try:
                queries = await self.query_expansion(
                    query, num_variants=2, config=fast_config
                )
                stats["expanded_queries"] = queries[1:]  # Exclude original
                logger.info("Query expanded", variants=len(queries))
            except Exception as e:
                logger.warning("Query expansion failed, using original", error=str(e))

        # 2. Search (Hybrid or Vector)
        all_results = []
        if use_hybrid:
            stats["search_method"] = "hybrid"
            for q in queries:
                results = await self.hybrid_search(
                    q, collection_name, n_results=n_results * 2
                )
                all_results.extend(results)
        else:
            for q in queries:
                results = await self.search(q, n_results * 2, collection_name)
                all_results.extend(results)

        # Deduplicate by content hash
        seen = set()
        unique_results = []
        for r in all_results:
            content_hash = hash(r["content"][:100])
            if content_hash not in seen:
                seen.add(content_hash)
                unique_results.append(r)

        stats["total_candidates"] = len(unique_results)

        # 3. Rerank
        if use_rerank and self.reranker and unique_results:
            try:
                pairs = [
                    [query, r["content"]] for r in unique_results[:30]
                ]  # Limit for speed
                scores = await self._run_sync(
                    self.reranker.predict, pairs, show_progress_bar=False
                )
                ranked = sorted(
                    zip(unique_results[:30], scores), key=lambda x: x[1], reverse=True
                )
                unique_results = []
                for result, score in ranked:
                    result["rerank_score"] = float(score)
                    unique_results.append(result)
            except Exception as e:
                logger.warning("Rerank failed", error=str(e))
                unique_results.sort(key=lambda x: x.get("distance", 1.0))
        else:
            unique_results.sort(
                key=lambda x: x.get("hybrid_score", 0) or (1 - x.get("distance", 1.0)),
                reverse=True,
            )

        # 4. Take top N
        final_results = unique_results[:n_results]
        stats["final_results"] = len(final_results)

        # 5. Graph Enhancement (optional)
        if use_graph and final_results:
            # Simplified graph enhancement - just add relation info if available
            try:
                for r in final_results:
                    chunk_id = r.get("metadata", {}).get("chunk_id")
                    if chunk_id:
                        relations = graph_rag_service.get_relations_for_chunk(chunk_id)
                        if relations:
                            r["graph_relations"] = relations[:3]
            except Exception:
                pass

        # 6. Format Context
        context_parts = []
        sources = []
        for i, r in enumerate(final_results, 1):
            match_type = r.get("match_type", "vector")
            score = (
                r.get("rerank_score")
                or r.get("hybrid_score")
                or (1 - r.get("distance", 1.0))
            )

            # Format chunk with metadata
            chunk_header = f"[Chunk {i}] ({match_type}, score: {score:.3f})"
            context_parts.append(f"{chunk_header}\n{r['content']}")

            sources.append(
                {
                    "content": r["content"][:200] + "..."
                    if len(r["content"]) > 200
                    else r["content"],
                    "match_type": match_type,
                    "score": float(score),
                    "metadata": r.get("metadata", {}),
                }
            )

        # 7. Context Compression (optional)
        raw_context = "\n\n".join(context_parts)
        final_context = raw_context

        if use_compression and self.context_compressor:
            try:
                compression_result = await self.context_compressor.compress(
                    context=raw_context,
                    query=query,
                    target_ratio=compression_ratio,
                    method=compression_method,
                )
                final_context = compression_result["compressed_context"]
                stats["compression"] = {
                    "original_len": compression_result["original_len"],
                    "compressed_len": compression_result["compressed_len"],
                    "ratio": compression_result["ratio"],
                    "method": compression_method,
                }
            except Exception as e:
                logger.warning("Context compression failed", error=str(e))

        return {
            "context": final_context,
            "sources": sources,
            "stats": stats,
        }

    # ========== MCP 優化功能 ==========

    async def hybrid_search(
        self,
        query: str,
        collection_name: str = None,
        n_results: int = 5,
        weights: dict = None,
    ) -> list[dict]:
        """
        混合搜尋：結合向量語意搜尋與關鍵字精確匹配

        Args:
            query: 查詢字串
            collection_name: 目標 collection
            n_results: 返回結果數量
            weights: {"vector": 0.7, "keyword": 0.3}
        """
        if weights is None:
            weights = {"vector": 0.7, "keyword": 0.3}

        target_collection = self.collection
        if collection_name:
            if not self._lazy_init():
                return []
            try:
                target_collection = self.client.get_collection(collection_name)
            except Exception:
                logger.warning(f"Collection {collection_name} not found")
                return []

        if not target_collection:
            return []

        try:
            # 1. Vector Search
            vector_results = await self.search(query, n_results * 2, collection_name)

            # 2. Keyword Search (using ChromaDB where filter on document content)
            # Note: ChromaDB's where_document provides basic text matching
            keyword_results = []
            try:
                # Extract keywords from query (simple split)
                keywords = [w.strip() for w in query.split() if len(w.strip()) > 1]
                if keywords:
                    # Use first 3 keywords for matching
                    for kw in keywords[:3]:
                        res = target_collection.query(
                            query_texts=[kw],
                            n_results=n_results,
                            where_document={"$contains": kw},
                        )
                        if res["documents"] and res["documents"][0]:
                            for i, doc in enumerate(res["documents"][0]):
                                keyword_results.append(
                                    {
                                        "content": doc,
                                        "distance": res["distances"][0][i]
                                        if res["distances"]
                                        else 0.5,
                                        "metadata": res["metadatas"][0][i]
                                        if res["metadatas"]
                                        else {},
                                        "match_type": "keyword",
                                    }
                                )
            except Exception as e:
                logger.warning("Keyword search failed", error=str(e))

            # 3. Merge and Score
            seen_content = set()
            merged = []

            for r in vector_results:
                content_hash = hash(r["content"][:100])
                if content_hash not in seen_content:
                    seen_content.add(content_hash)
                    # Normalize vector score (distance -> similarity)
                    vec_sim = 1.0 - r.get("distance", 1.0)
                    r["hybrid_score"] = vec_sim * weights["vector"]
                    r["match_type"] = "vector"
                    merged.append(r)

            for r in keyword_results:
                content_hash = hash(r["content"][:100])
                if content_hash not in seen_content:
                    seen_content.add(content_hash)
                    kw_sim = 1.0 - r.get("distance", 0.5)
                    r["hybrid_score"] = kw_sim * weights["keyword"]
                    merged.append(r)
                else:
                    # Boost existing entry if found in both
                    for m in merged:
                        if hash(m["content"][:100]) == content_hash:
                            kw_sim = 1.0 - r.get("distance", 0.5)
                            m["hybrid_score"] += kw_sim * weights["keyword"]
                            m["match_type"] = "hybrid"
                            break

            # Sort by hybrid score
            merged.sort(key=lambda x: x.get("hybrid_score", 0), reverse=True)
            return merged[:n_results]

        except Exception as e:
            logger.error("Hybrid search failed", error=str(e))
            return []

    async def query_expansion(
        self, query: str, num_variants: int = 3, config: dict = None
    ) -> list[str]:
        """
        查詢擴展：使用 LLM 生成同義表達和相關概念

        Args:
            query: 原始查詢
            num_variants: 生成變體數量
            config: Optional LLM config override (e.g. fast_config)
        """
        try:
            expansion_prompt = f"""請將以下查詢改寫為 {num_variants} 個不同的表達方式，以便進行更全面的搜尋。
保持語意相同但使用不同的詞彙和句式。

原始查詢: {query}

請只輸出改寫後的查詢，每行一個，不要加編號或解釋。"""

            # Resolving config (Use passed config OR default fast routing)
            # If config is passed, it means user overrode it in UI (Fast Tier)
            # otherwise we fallback to default get_routing_config("fast")
            routing = config if config else llm_service.get_routing_config("fast")

            # Use LLM service to generate expansions
            result = await llm_service.generate_text(
                expansion_prompt,
                provider=routing.get("provider"),
                model_name=routing.get("model_name"),
                local_url=routing.get("local_url"),
                api_key=routing.get("api_key_input"),
            )
            if result:
                variants = [v.strip() for v in result.strip().split("\n") if v.strip()]
                # Always include original query
                return [query] + variants[:num_variants]
            return [query]
        except Exception as e:
            logger.warning("Query expansion failed", error=str(e))
            return [query]

    async def generate_document_summary(
        self, collection_name: str, max_chars: int = 8000
    ) -> dict:
        """
        生成文件摘要與關鍵詞

        Args:
            collection_name: 目標 collection
            max_chars: 用於摘要的最大字元數
        """
        if not self._lazy_init():
            return {"success": False, "error": "Service not initialized"}

        try:
            collection = self.client.get_collection(collection_name)
            meta = collection.metadata or {}

            # Check cache in metadata
            if meta.get("cached_summary"):
                return {
                    "success": True,
                    "summary": meta.get("cached_summary"),
                    "keywords": meta.get("cached_keywords", "").split(","),
                    "from_cache": True,
                }

            # Fetch first N chunks for summarization
            res = collection.get(limit=20, include=["documents"])
            if not res or not res["documents"]:
                return {"success": False, "error": "Document is empty"}

            content_sample = "\n\n".join(res["documents"])[:max_chars]

            summary_prompt = f"""請為以下文件內容生成一個簡潔的摘要（約 200 字）和 5-8 個關鍵詞。

文件內容:
{content_sample}

請以 JSON 格式輸出:
{{"summary": "...", "keywords": ["關鍵詞1", "關鍵詞2", ...]}}"""

            result = await llm_service.generate_text(summary_prompt)

            if result:
                import json

                try:
                    # Try to parse JSON from result
                    # Handle potential markdown code blocks
                    clean_result = result.strip()
                    if clean_result.startswith("```"):
                        clean_result = clean_result.split("```")[1]
                        if clean_result.startswith("json"):
                            clean_result = clean_result[4:]
                    parsed = json.loads(clean_result)

                    return {
                        "success": True,
                        "summary": parsed.get("summary", ""),
                        "keywords": parsed.get("keywords", []),
                        "from_cache": False,
                    }
                except json.JSONDecodeError:
                    # Fallback: return raw text as summary
                    return {
                        "success": True,
                        "summary": result[:500],
                        "keywords": [],
                        "from_cache": False,
                    }

            return {"success": False, "error": "LLM generation failed"}

        except Exception as e:
            logger.error("Document summary generation failed", error=str(e))
            return {"success": False, "error": str(e)}


rag_service = RAGService()
