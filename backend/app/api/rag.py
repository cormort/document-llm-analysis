"""RAG API endpoints with SSE streaming support."""

import asyncio
import json
from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.models.rag import (
    DocumentInfo,
    RAGIndexRequest,
    RAGIndexResponse,
    RAGQueryRequest,
    RAGQueryResponse,
)
from app.services.document_service import document_service
from app.services.llm_service import llm_service
from app.services.rag_service import rag_service

router = APIRouter()


async def stream_rag_response(answer: str) -> AsyncGenerator[dict[str, str], None]:
    """Stream RAG response content for SSE."""
    words = (await answer).split() if asyncio.iscoroutine(answer) else answer.split()
    # If answer is already a string, we just split it.
    # But wait, rag_answer is async now.

    # Correction: stream_rag_response should take the awaited result.
    buffer = ""
    for i, word in enumerate(words):
        buffer += word + " "
        if i % 3 == 0 or i == len(words) - 1:
            yield {"event": "message", "data": buffer}
            buffer = ""
            await asyncio.sleep(0.02)
    yield {"event": "done", "data": "[DONE]"}


@router.post("/query", response_model=RAGQueryResponse)
async def query_documents(request: RAGQueryRequest) -> RAGQueryResponse:
    """Query indexed documents using RAG with full optimization pipeline."""
    try:
        api_key = request.config.api_key

        if not request.collection_names:
            raise HTTPException(status_code=400, detail="未提供查詢集合名稱 (collection_names is empty)")

        # Search across collections
        if len(request.collection_names) > 1:
            results = await rag_service.search_across_collections(
                query=request.question,
                collection_names=request.collection_names,
                n_results=request.n_results,
                use_rerank=request.use_rerank,
            )
            context_parts = []
            for r in results:
                source_info = f"[來源: {r.get('source_file', 'Unknown')}]"
                context_parts.append(f"{source_info}\n{r['content']}")
            context = "\n\n".join(context_parts)
            sources = results
        else:
            # Use optimized context with full pipeline
            optimized = await rag_service.get_optimized_context(
                query=request.question,
                collection_name=request.collection_names[0],
                n_results=request.n_results,
                use_rerank=request.use_rerank,
                use_hybrid=request.use_hybrid,
                use_query_expansion=request.use_query_expansion,
                use_compression=request.use_compression,
                compression_method=request.compression_method,
                fast_config=request.fast_config.model_dump()
                if request.fast_config
                else {},
            )
            context = optimized["context"]
            sources = optimized["sources"]

        # Generate answer
        answer = await llm_service.rag_answer(
            question=request.question,
            context=context,
            provider=request.config.provider,
            model_name=request.config.model_name,
            local_url=request.config.local_url,
            context_window=request.config.context_window,
            api_key=api_key,
        )

        return RAGQueryResponse(answer=answer, sources=sources)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/query/stream")
async def query_documents_stream(request: RAGQueryRequest) -> EventSourceResponse:
    """Query documents with SSE streaming response."""
    try:
        api_key = request.config.api_key

        if not request.collection_names:
            raise HTTPException(status_code=400, detail="未提供查詢集合名稱 (collection_names is empty)")

        # Check for summary intent to boost retrieved chunks
        is_summary = any(k in request.question.lower() for k in ["摘要", "總結", "重點", "大綱", "結論", "summary", "summarize"])
        active_n_results = 25 if is_summary and request.n_results < 25 else request.n_results

        # Search across collections
        if len(request.collection_names) > 1:
            results = await rag_service.search_across_collections(
                query=request.question,
                collection_names=request.collection_names,
                n_results=active_n_results,
                use_rerank=request.use_rerank,
            )
            context_parts = []
            for r in results:
                source_info = f"[來源: {r.get('source_file', 'Unknown')}]"
                context_parts.append(f"{source_info}\n{r['content']}")
            context = "\n\n".join(context_parts)
        else:
            # Use optimized context with full pipeline
            optimized = await rag_service.get_optimized_context(
                query=request.question,
                collection_name=request.collection_names[0],
                n_results=active_n_results,
                use_rerank=request.use_rerank,
                use_hybrid=request.use_hybrid,
                use_query_expansion=request.use_query_expansion,
                use_compression=request.use_compression,
                compression_method=request.compression_method,
                fast_config=request.fast_config.model_dump()
                if request.fast_config
                else {},
            )
            context = optimized["context"]

        # Generate answer
        answer = await llm_service.rag_answer(
            question=request.question,
            context=context,
            provider=request.config.provider,
            model_name=request.config.model_name,
            local_url=request.config.local_url,
            context_window=request.config.context_window,
            api_key=api_key,
        )

        return EventSourceResponse(stream_rag_response(answer))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/index", response_model=RAGIndexResponse)
async def index_document(request: RAGIndexRequest) -> RAGIndexResponse:
    """Index a document for RAG queries."""
    try:
        # 1. Extract content first using document_service
        content = await document_service.extract_text(request.file_path)
        if not content or content.startswith("[Error"):
            return RAGIndexResponse(
                success=False,
                collection_name=None,
                message=f"Failed to extract text: {content}",
            )

        # 2. Index using rag_service
        res = await rag_service.index_document(
            request.file_path, content, chunking_strategy=request.chunking_strategy
        )

        if res.get("success"):
            return RAGIndexResponse(
                success=True,
                collection_name=res.get("collection_name"),
                message=f"Successfully indexed {request.file_path}",
            )
        return RAGIndexResponse(
            success=False,
            collection_name=None,
            message=res.get("error", "Failed to index document"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/documents", response_model=list[DocumentInfo])
async def list_documents() -> list[DocumentInfo]:
    """List all indexed documents."""
    try:
        docs = await rag_service.list_indexed_documents()
        return [
            DocumentInfo(
                collection_name=d["collection_name"],
                file_name=d["file_name"],
                chunk_count=d["count"],
                indexed_at=d["indexed_at"],
            )
            for d in docs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/reindex-all")
async def reindex_all_documents():
    """
    Rebuild embeddings for all indexed documents using the current model.
    Useful after switching embedding models.
    """
    try:
        result = await rag_service.reindex_all_documents()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/documents/{collection_name}")
async def delete_document(collection_name: str) -> dict[str, str | bool]:
    """Delete an indexed document."""
    try:
        success = rag_service.delete_document_index(collection_name)
        if success:
            return {"success": True, "message": f"Deleted {collection_name}"}
        return {"success": False, "message": f"Failed to delete {collection_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/documents/{collection_name}/reindex")
async def reindex_document(collection_name: str) -> dict[str, str | list[str] | bool]:
    """Reindex a document with LangExtract enhancement."""
    import os

    try:
        # 1. 取得文件資訊
        docs = await rag_service.list_indexed_documents()
        target_doc = next(
            (d for d in docs if d["collection_name"] == collection_name), None
        )

        if not target_doc:
            return {
                "success": False,
                "message": f"Document {collection_name} not found",
            }

        file_name = target_doc["file_name"]

        # 2. 找到文件路徑 (使用與其他 API 相同的方式)
        data_dir = Path(__file__).parent.parent.parent.parent / "data"
        file_path = str(data_dir / file_name)

        if not os.path.exists(file_path):
            return {
                "success": False,
                "message": f"File {file_name} not found on disk",
            }

        # 3. 刪除舊索引
        rag_service.delete_document_index(collection_name)

        # 4. 重新提取內容
        content = await document_service.extract_text(file_path)
        if not content or content.startswith("[Error"):
            return {
                "success": False,
                "message": f"Failed to extract text: {content}",
            }

        # 5. 重新建立索引 (使用 LangExtract)
        res = await rag_service.index_document(file_path, content)

        if res.get("success"):
            return {
                "success": True,
                "message": f"Reindexed {file_name} with LangExtract",
                "extracted_tags": res.get("extracted_tags", []),
            }
        return {
            "success": False,
            "message": res.get("error", "Failed to reindex document"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ========== Astute RAG Endpoints ==========

from app.models.rag import (
    AstuteRAGQueryRequest,
    AstuteRAGQueryResponse,
    ConflictInfo,
    InternalKnowledgeResponse,
    ReliabilityDistribution,
    SourceInfo,
    VerifyAnswerRequest,
    VerifyAnswerResponse,
)
from app.services.astute_rag_service import astute_rag_service


@router.post("/astute/query", response_model=AstuteRAGQueryResponse)
async def astute_query(request: AstuteRAGQueryRequest) -> AstuteRAGQueryResponse:
    """
    Execute Astute RAG query with internal knowledge elicitation and reliability assessment.

    This endpoint implements the full Astute RAG pipeline:
    1. Elicit internal knowledge from LLM
    2. Decide if retrieval is needed
    3. Perform retrieval (if needed)
    4. Consolidate internal and external knowledge
    5. Generate reliability-based answer
    """
    try:
        api_key = request.config.api_key

        # Determine collection name (use first if provided, else None)
        collection_name = (
            request.collection_names[0] if request.collection_names else None
        )

        # Execute Astute RAG query
        result = await astute_rag_service.query(
            query=request.question,
            rag_service=rag_service,
            collection_name=collection_name,
            n_results=request.n_results,
            use_hybrid=request.use_hybrid,
            use_rerank=request.use_rerank,
            provider=request.config.provider,
            model_name=request.config.model_name,
            local_url=request.config.local_url,
            force_retrieval=request.force_retrieval,
        )

        # Convert to response model
        sources_used = [
            SourceInfo(
                text=s.get("text", "")[:200],
                source_type=s.get("type", "unknown"),
                reliability=s.get("reliability", 0.5),
            )
            for s in result.get("sources_used", [])
        ]

        conflicts_noted = [
            ConflictInfo(
                conflict_type=c.get("type", "unknown"),
                description=c.get("description", ""),
                internal=c.get("internal", ""),
                external=c.get("external", ""),
            )
            for c in result.get("conflicts_noted", [])
        ]

        reliability_dist = result.get("reliability_distribution", {})

        return AstuteRAGQueryResponse(
            answer=result.get("answer", ""),
            confidence=result.get("confidence", 0.5),
            sources_used=sources_used,
            conflicts_noted=conflicts_noted,
            knowledge_type=result.get("knowledge_type", "unknown"),
            query_decision=result.get("query_decision", "unknown"),
            internal_confidence=result.get("internal_confidence", 0.5),
            retrieval_performed=result.get("retrieval_performed", False),
            consolidation_summary=result.get("consolidation_summary", ""),
            reliability_distribution=ReliabilityDistribution(
                high=reliability_dist.get("high", 0),
                medium=reliability_dist.get("medium", 0),
                low=reliability_dist.get("low", 0),
            ),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/astute/elicit", response_model=InternalKnowledgeResponse)
async def elicit_internal_knowledge(
    question: str,
    provider: str | None = None,
    model_name: str | None = None,
    local_url: str | None = None,
) -> InternalKnowledgeResponse:
    """
    Elicit internal knowledge from LLM without performing retrieval.

    Useful for understanding what the LLM already knows before deciding
    whether to use RAG.
    """
    try:
        result = await astute_rag_service.elicit_internal_knowledge(
            query=question,
            provider=provider,
            model_name=model_name,
            local_url=local_url,
        )

        return InternalKnowledgeResponse(
            internal_answer=result.get("internal_answer", ""),
            confidence=result.get("confidence", 0.5),
            key_facts=result.get("key_facts", []),
            knowledge_gaps=result.get("knowledge_gaps", []),
            needs_retrieval=result.get("needs_retrieval", True),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/astute/verify", response_model=VerifyAnswerResponse)
async def verify_answer(request: VerifyAnswerRequest) -> VerifyAnswerResponse:
    """
    Verify an existing answer against indexed documents.

    This endpoint checks if the provided answer is supported by the
    indexed documents and identifies any contradictions.
    """
    try:
        api_key = request.config.api_key

        # Search for relevant passages
        all_passages = []
        for collection_name in request.collection_names:
            passages = await rag_service.search_with_rerank(
                query=request.question,
                n_results=5,
                collection_name=collection_name,
            )
            all_passages.extend(passages)

        if not all_passages:
            return VerifyAnswerResponse(
                is_verified=False,
                confidence=0.0,
                supporting_facts=[],
                contradicting_facts=[],
                summary="無法找到相關文件進行驗證",
            )

        # Use LLM to verify
        passages_text = "\n\n".join(
            f"[文件 {i + 1}]: {p.get('content', '')[:500]}"
            for i, p in enumerate(all_passages[:5])
        )

        verify_prompt = f"""請驗證以下回答是否被文件內容支持。

【問題】
{request.question}

【待驗證的回答】
{request.answer}

【文件內容】
{passages_text}

請以 JSON 格式輸出：
{{
    "is_verified": true/false,
    "confidence": 0-1 之間的數字,
    "supporting_facts": ["支持回答的事實1", ...],
    "contradicting_facts": ["與回答矛盾的事實1", ...],
    "summary": "驗證結論摘要"
}}

只輸出 JSON。"""

        result = await llm_service.analyze_text(
            text_content="",
            user_instruction=verify_prompt,
            provider=request.config.provider,
            model_name=request.config.model_name,
            local_url=request.config.local_url,
        )

        # Parse result
        result = result.strip()
        if result.startswith("```"):
            lines = result.split("\n")
            result = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        parsed = json.loads(result)

        return VerifyAnswerResponse(
            is_verified=parsed.get("is_verified", False),
            confidence=parsed.get("confidence", 0.5),
            supporting_facts=parsed.get("supporting_facts", []),
            contradicting_facts=parsed.get("contradicting_facts", []),
            summary=parsed.get("summary", ""),
        )

    except json.JSONDecodeError:
        return VerifyAnswerResponse(
            is_verified=False,
            confidence=0.3,
            supporting_facts=[],
            contradicting_facts=[],
            summary="驗證過程中發生解析錯誤",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
