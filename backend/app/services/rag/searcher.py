"""
RAG Searcher Mixin — semantic search, hybrid search, query expansion,
context assembly, and optimization pipeline.
"""

import asyncio

import structlog

from app.core.metrics import CHROMADB_QUERY_LATENCY_SECONDS

logger = structlog.get_logger()

# Imported from base at runtime to avoid circular imports
MAX_N_RESULTS = 100


class RAGSearcherMixin:
    """Provides all search and context retrieval capabilities to RAGService."""

    async def search(
        self, query: str, n_results: int = 5, collection_name: str = None
    ) -> list[dict]:
        """Basic semantic search on a specific or default collection."""
        n_results = min(n_results, MAX_N_RESULTS)
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
        """Search across multiple collections and merge results."""
        n_results = min(n_results, MAX_N_RESULTS)
        tasks = [
            self.search(query, n_results=n_results, collection_name=name)
            for name in collection_names
        ]
        results_list = await asyncio.gather(*tasks)
        all_results = [r for results in results_list for r in results]

        if use_rerank and self.reranker and all_results:
            if len(all_results) > 50:
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
            all_results.sort(key=lambda x: x.get("distance", 1.0))
            return all_results[:n_results]

    async def search_with_rerank(
        self,
        query: str,
        n_results: int = 5,
        initial_k: int = 20,
        collection_name: str = None,
    ) -> list[dict]:
        """Search with cross-encoder re-ranking on a single collection."""
        n_results = min(n_results, MAX_N_RESULTS)
        initial_k = min(initial_k, MAX_N_RESULTS)
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

    async def hybrid_search(
        self,
        query: str,
        collection_name: str = None,
        n_results: int = 5,
        weights: dict = None,
    ) -> list[dict]:
        """Hybrid search combining vector similarity and keyword matching."""
        n_results = min(n_results, MAX_N_RESULTS)
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
            vector_results = await self.search(query, n_results * 2, collection_name)

            keyword_results = []
            try:
                keywords = [w.strip() for w in query.split() if len(w.strip()) > 1]
                if keywords:
                    for kw in keywords[:3]:
                        res = target_collection.get(
                            where_document={"$contains": kw},
                            limit=n_results,
                            include=["documents", "metadatas"],
                        )
                        if res["documents"]:
                            for i, doc in enumerate(res["documents"]):
                                keyword_results.append(
                                    {
                                        "content": doc,
                                        "distance": 0.5,
                                        "metadata": res["metadatas"][i]
                                        if res["metadatas"]
                                        else {},
                                        "match_type": "keyword",
                                    }
                                )
            except Exception as e:
                logger.warning("Keyword search failed", error=str(e))

            seen_content = set()
            merged = []

            for r in vector_results:
                content_hash = hash(r["content"][:100])
                if content_hash not in seen_content:
                    seen_content.add(content_hash)
                    r["hybrid_score"] = (1.0 - r.get("distance", 1.0)) * weights["vector"]
                    r["match_type"] = "vector"
                    merged.append(r)

            for r in keyword_results:
                content_hash = hash(r["content"][:100])
                if content_hash not in seen_content:
                    seen_content.add(content_hash)
                    r["hybrid_score"] = (1.0 - r.get("distance", 0.5)) * weights["keyword"]
                    merged.append(r)
                else:
                    for m in merged:
                        if hash(m["content"][:100]) == content_hash:
                            m["hybrid_score"] += (
                                1.0 - r.get("distance", 0.5)
                            ) * weights["keyword"]
                            m["match_type"] = "hybrid"
                            break

            merged.sort(key=lambda x: x.get("hybrid_score", 0), reverse=True)
            return merged[:n_results]

        except Exception as e:
            logger.error("Hybrid search failed", error=str(e))
            return []

    async def query_expansion(
        self, query: str, num_variants: int = 3, config: dict = None
    ) -> list[str]:
        """Use LLM to generate query variants for broader search coverage."""
        from app.services.llm_service import llm_service

        try:
            expansion_prompt = f"""請將以下查詢改寫為 {num_variants} 個不同的表達方式，以便進行更全面的搜尋。
保持語意相同但使用不同的詞彙和句式。

原始查詢: {query}

請只輸出改寫後的查詢，每行一個，不要加編號或解釋。"""

            routing = config if config else llm_service.get_routing_config("fast")
            result = await llm_service.generate_text(
                expansion_prompt,
                provider=routing.get("provider"),
                model_name=routing.get("model_name"),
                local_url=routing.get("local_url"),
                api_key=routing.get("api_key_input"),
            )
            if result:
                variants = [v.strip() for v in result.strip().split("\n") if v.strip()]
                return [query] + variants[:num_variants]
            return [query]
        except Exception as e:
            logger.warning("Query expansion failed", error=str(e))
            return [query]

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
        """Get enhanced context for SA-RAG with optional graph augmentation."""
        from app.services.graph_rag_service import graph_rag_service
        from app.services.llm_service import llm_service

        if use_rerank and self.reranker:
            results = await self.search_with_rerank(query, n_results * 2)
        else:
            results = await self.search(query, n_results * 2)

        filtered_results = [
            r for r in results if (1.0 - r.get("distance", 1.0)) >= tau_d
        ]

        graph_results = []
        rel_texts = []

        if use_graph:
            try:
                extraction = await llm_service.extract_entities(
                    f"Identify entities: {query}"
                )
                seed_entities = []
                if isinstance(extraction, dict):
                    seed_entities = [
                        e["name"]
                        for e in extraction.get("entities", [])
                        if e.get("name")
                    ]

                if seed_entities:
                    activated_chunk_ids = graph_rag_service.spreading_activation(
                        seed_entities, threshold=tau_a
                    )
                    if activated_chunk_ids and self.collection:
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

                    for u, v, d in graph_rag_service.graph.edges(data=True):
                        if d.get("weight", 0) >= tau_r and d.get("relation"):
                            rel_texts.append(
                                f"Relation: {u} --({d['relation']})--> {v}"
                            )
            except Exception as e:
                logger.error("Graph enhancement failed", error=str(e))

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
        compression_method: str = "extractive",
        compression_ratio: float = 0.5,
        fast_config: dict = None,
    ) -> dict:
        """
        Full RAG optimization pipeline.

        Steps:
        1. Query Expansion (optional)
        2. Hybrid or vector search
        3. Deduplication
        4. Re-ranking
        5. Graph enhancement (optional)
        6. Context formatting
        7. Context compression (optional)
        """
        n_results = min(n_results, MAX_N_RESULTS)
        from app.services.graph_rag_service import graph_rag_service

        stats = {
            "original_query": query,
            "expanded_queries": [],
            "search_method": "vector",
            "total_candidates": 0,
            "final_results": 0,
        }

        if collection_name:
            self.switch_to_document(collection_name)

        # 1. Query Expansion
        queries = [query]
        if use_query_expansion:
            try:
                queries = await self.query_expansion(
                    query, num_variants=2, config=fast_config
                )
                stats["expanded_queries"] = queries[1:]
                logger.info("Query expanded", variants=len(queries))
            except Exception as e:
                logger.warning("Query expansion failed, using original", error=str(e))

        # 2. Search
        all_results = []
        if use_hybrid:
            stats["search_method"] = "hybrid"
            for q in queries:
                all_results.extend(
                    await self.hybrid_search(q, collection_name, n_results=n_results * 2)
                )
        else:
            for q in queries:
                all_results.extend(await self.search(q, n_results * 2, collection_name))

        # 3. Deduplication
        seen = set()
        unique_results = []
        for r in all_results:
            content_hash = hash(r["content"][:100])
            if content_hash not in seen:
                seen.add(content_hash)
                unique_results.append(r)

        stats["total_candidates"] = len(unique_results)

        # 4. Rerank
        if use_rerank and self.reranker and unique_results:
            try:
                pairs = [[query, r["content"]] for r in unique_results[:30]]
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

        # 5. Graph Enhancement
        final_results = unique_results[:n_results]
        stats["final_results"] = len(final_results)

        if use_graph and final_results:
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
            score = float(
                r.get("rerank_score")
                or r.get("hybrid_score")
                or (1 - r.get("distance", 1.0))
            )
            chunk_header = f"[Chunk {i}] ({match_type}, score: {score:.3f})"
            context_parts.append(f"{chunk_header}\n{r['content']}")
            sources.append(
                {
                    "content": r["content"][:200] + "..."
                    if len(r["content"]) > 200
                    else r["content"],
                    "match_type": match_type,
                    "score": score,
                    "metadata": r.get("metadata", {}),
                }
            )

        # 7. Context Compression
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
