"""
RAG Indexer Mixin — document indexing, reindexing, listing, and deletion.
"""

import hashlib
import os

import structlog

logger = structlog.get_logger()


class RAGIndexerMixin:
    """Provides document indexing and management capabilities to RAGService."""

    async def index_document(
        self,
        file_path: str,
        content: str,
        metadata: dict = None,
        build_graph: bool = True,
        use_langextract: bool = True,
        chunking_strategy: str = "semantic",
    ) -> dict:
        """Index document with metadata and optional graph building.

        Args:
            file_path: Path to the document file.
            content: Text content to index.
            metadata: Optional extra metadata dict.
            build_graph: Whether to build a knowledge graph from the content.
            use_langextract: Whether to use LangExtract for enhanced extraction.
            chunking_strategy: "semantic" (embedding-based) or "fixed" (size-based).
        """
        if not self._lazy_init():
            return {"success": False, "error": "RAG Service not initialized"}

        doc_id = hashlib.md5(file_path.encode()).hexdigest()[:16]
        collection_name = f"doc_{doc_id}"

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

            # LangExtract: generate rich metadata
            extracted_tags = []
            if langextract_available and langextract_service:
                try:
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

            # Build Knowledge Graph
            if build_graph:
                from app.services.graph_rag_service import graph_rag_service
                from app.services.llm_service import llm_service

                logger.info("Building Knowledge Graph", chunks=len(chunks))
                process_limit = min(len(chunks), 20)
                for i in range(process_limit):
                    chunk = chunks[i]
                    cid = f"{doc_id}_{i}"
                    extraction_data = None

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

                    if not extraction_data:
                        extraction_data = await llm_service.extract_entities(chunk)

                    if extraction_data and isinstance(extraction_data, dict):
                        graph_rag_service.add_triplets(extraction_data, cid)

                graph_rag_service.save_graph()

            return {
                "success": True,
                "collection_name": collection_name,
                "chunks_count": len(chunks),
                "extracted_tags": extracted_tags,
            }

        except Exception as e:
            logger.error("Error indexing document", error=str(e))
            return {"success": False, "error": str(e)}

    def _convert_langextract_to_triplets(self, lx_result: dict) -> dict:
        """Convert LangExtract output to triplet format for graph_rag_service."""
        entities = []
        relations = []

        for ext in lx_result.get("extractions", []):
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
        """List all indexed document collections."""
        if not self._lazy_init():
            return []
        try:
            collections = self.client.list_collections()
            return [
                {
                    "collection_name": col.name,
                    "file_name": (col.metadata or {}).get("file_name", "Unknown"),
                    "file_type": (col.metadata or {}).get("file_type", "Unknown"),
                    "indexed_at": (col.metadata or {}).get("indexed_at", "Unknown"),
                    "count": col.count(),
                }
                for col in collections
            ]
        except Exception as e:
            logger.error("List collections failed", error=str(e))
            return []

    def delete_document_index(self, collection_name: str) -> bool:
        """Delete a document index."""
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
        Rebuild embeddings for all indexed documents using the current model.
        Useful after switching embedding models.
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
                    all_docs = col.get(include=["documents", "metadatas"])
                    if not all_docs or not all_docs["documents"]:
                        results.append(
                            {"collection": col_name, "status": "skipped", "reason": "empty"}
                        )
                        continue

                    documents = all_docs["documents"]
                    metadatas = all_docs["metadatas"] or [{}] * len(documents)
                    ids = all_docs["ids"]

                    logger.info(f"Re-embedding {len(documents)} chunks for {col_name}")
                    new_embeddings = self.embedder.encode(
                        documents,
                        batch_size=32,
                        show_progress_bar=False,
                        convert_to_numpy=True,
                    ).tolist()

                    self.client.delete_collection(col_name)
                    new_col = self.client.get_or_create_collection(
                        name=col_name, metadata=meta
                    )
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
        """Switch the active collection."""
        if not self._lazy_init():
            return False
        try:
            self.collection = self.client.get_collection(collection_name)
            return True
        except Exception as e:
            logger.error(f"Switch to {collection_name} failed", error=str(e))
            return False

    async def generate_document_summary(
        self, collection_name: str, max_chars: int = 8000
    ) -> dict:
        """Generate a summary and keywords for a document."""
        import json

        if not self._lazy_init():
            return {"success": False, "error": "Service not initialized"}

        from app.services.llm_service import llm_service

        try:
            collection = self.client.get_collection(collection_name)
            meta = collection.metadata or {}

            if meta.get("cached_summary"):
                return {
                    "success": True,
                    "summary": meta.get("cached_summary"),
                    "keywords": meta.get("cached_keywords", "").split(","),
                    "from_cache": True,
                }

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
                try:
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
