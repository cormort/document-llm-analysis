"""
Astute RAG Service.

Implements the Astute RAG methodology for handling imperfect retrieval
and knowledge conflicts in RAG systems.

Based on: "Astute RAG: Overcoming Imperfect Retrieval Augmentation
and Knowledge Conflicts for Large Language Models" (Wang et al.)
"""

import json
from enum import Enum
from typing import Any

import structlog
from app.services.knowledge_consolidator import (
    KnowledgeConsolidator,
    knowledge_consolidator,
)
from app.services.llm_service import llm_service
from app.services.reliability_scorer import (
    ReliabilityScorer,
    SourceType,
    reliability_scorer,
)

logger = structlog.get_logger()


class QueryDecision(str, Enum):
    """Decision on how to handle a query."""

    INTERNAL_SUFFICIENT = "internal_sufficient"  # LLM knowledge is enough
    RETRIEVAL_REQUIRED = "retrieval_required"  # Need external retrieval
    VERIFICATION_NEEDED = "verification_needed"  # Have answer but need verification


class AstuteRAGService:
    """
    Astute RAG implementation with three core mechanisms:

    1. Adaptive Elicitation: Extract LLM's internal knowledge
    2. Source-Aware Consolidation: Merge and verify internal/external knowledge
    3. Reliability-Based Finalization: Generate answers based on reliability
    """

    def __init__(
        self,
        consolidator: KnowledgeConsolidator | None = None,
        scorer: ReliabilityScorer | None = None,
        internal_confidence_threshold: float = 0.7,
        retrieval_confidence_threshold: float = 0.4,
    ) -> None:
        """
        Initialize Astute RAG service.

        Args:
            consolidator: Knowledge consolidator instance
            scorer: Reliability scorer instance
            internal_confidence_threshold: Above this, LLM knowledge may be sufficient
            retrieval_confidence_threshold: Below this, retrieval is required
        """
        self.consolidator = consolidator or knowledge_consolidator
        self.scorer = scorer or reliability_scorer
        self.internal_threshold = internal_confidence_threshold
        self.retrieval_threshold = retrieval_confidence_threshold

    # =========================================================================
    # Phase 1: Internal Knowledge Elicitation
    # =========================================================================

    async def elicit_internal_knowledge(
        self,
        query: str,
        provider: str | None = None,
        model_name: str | None = None,
        local_url: str | None = None,
    ) -> dict[str, Any]:
        """
        Extract relevant knowledge from LLM's internal knowledge base.

        This is the first step of Astute RAG - understanding what the LLM
        already knows before retrieval.

        Args:
            query: User's question
            provider: LLM provider
            model_name: Model name
            local_url: Local LLM URL

        Returns:
            {
                "internal_answer": str,       # LLM's preliminary answer
                "confidence": float,          # Self-assessed confidence (0-1)
                "key_facts": list[str],       # Extracted key facts
                "knowledge_gaps": list[str],  # Identified knowledge gaps
                "needs_retrieval": bool,      # Whether retrieval is recommended
            }
        """
        logger.info("Eliciting internal knowledge", query=query[:50])

        prompt = f"""你是專業助手。請根據你的知識回答以下問題，並誠實評估你的確定程度。

【問題】
{query}

請以 JSON 格式提供：
{{
    "internal_answer": "根據你的知識，對問題的回答",
    "confidence": 0.0到1.0之間的數字，表示你對這個回答的信心程度,
    "key_facts": ["你確定的關鍵事實1", "事實2", ...],
    "knowledge_gaps": ["你不確定或需要查證的部分1", "部分2", ...]
}}

重要提示：
- confidence 接近 1.0 表示你非常確定
- confidence 接近 0.0 表示你完全不確定或這是你不熟悉的領域
- 如果問題涉及特定文件、最新數據、或特定組織內部資訊，confidence 應該較低
- 只輸出 JSON，不要其他說明"""

        try:
            result = await llm_service.analyze_text(
                text="",
                user_instruction=prompt,
                provider=provider,
                model_name=model_name,
                local_url=local_url,
            )

            # Parse JSON
            result = result.strip()
            if result.startswith("```"):
                lines = result.split("\n")
                result = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            parsed = json.loads(result)

            # Determine if retrieval is needed
            confidence = float(parsed.get("confidence", 0.5))
            knowledge_gaps = parsed.get("knowledge_gaps", [])
            needs_retrieval = confidence < self.internal_threshold or len(knowledge_gaps) > 0

            return {
                "internal_answer": parsed.get("internal_answer", ""),
                "confidence": confidence,
                "key_facts": parsed.get("key_facts", []),
                "knowledge_gaps": knowledge_gaps,
                "needs_retrieval": needs_retrieval,
            }

        except json.JSONDecodeError as e:
            logger.warning("Failed to parse internal knowledge JSON", error=str(e))
            return {
                "internal_answer": "",
                "confidence": 0.3,
                "key_facts": [],
                "knowledge_gaps": ["無法解析回應"],
                "needs_retrieval": True,
            }
        except Exception as e:
            logger.error("Internal knowledge elicitation failed", error=str(e))
            return {
                "internal_answer": "",
                "confidence": 0.0,
                "key_facts": [],
                "knowledge_gaps": [str(e)],
                "needs_retrieval": True,
            }

    # =========================================================================
    # Phase 4: Adaptive Decision Making
    # =========================================================================

    async def classify_query_need(
        self,
        query: str,
        internal_confidence: float,
        knowledge_gaps: list[str],
    ) -> QueryDecision:
        """
        Determine how to handle the query based on internal knowledge assessment.

        Args:
            query: User's question
            internal_confidence: LLM's self-assessed confidence
            knowledge_gaps: Identified knowledge gaps

        Returns:
            QueryDecision enum indicating recommended approach
        """
        # Check for document-specific queries
        doc_indicators = [
            "根據文件", "文件中", "報告裡", "按照", "依據",
            "這份", "該文", "此文件", "上述", "如附件"
        ]
        is_doc_specific = any(ind in query for ind in doc_indicators)

        # Check for time-sensitive queries
        time_indicators = ["最新", "目前", "現在", "今年", "2024", "2025", "2026"]
        is_time_sensitive = any(ind in query for ind in time_indicators)

        if is_doc_specific:
            return QueryDecision.RETRIEVAL_REQUIRED

        if internal_confidence >= self.internal_threshold and not knowledge_gaps:
            if is_time_sensitive:
                return QueryDecision.VERIFICATION_NEEDED
            return QueryDecision.INTERNAL_SUFFICIENT

        if internal_confidence >= self.retrieval_threshold:
            return QueryDecision.VERIFICATION_NEEDED

        return QueryDecision.RETRIEVAL_REQUIRED

    # =========================================================================
    # Phase 5: Enhanced Answer Generation
    # =========================================================================

    async def generate_astute_answer(
        self,
        query: str,
        consolidated: dict[str, Any],
        internal_knowledge: dict[str, Any],
        provider: str | None = None,
        model_name: str | None = None,
        local_url: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate final answer based on consolidated, reliability-assessed knowledge.

        Args:
            query: Original user query
            consolidated: Result from knowledge consolidation
            internal_knowledge: Original internal knowledge elicitation
            provider: LLM provider
            model_name: Model name
            local_url: Local LLM URL

        Returns:
            {
                "answer": str,
                "confidence": float,
                "sources_used": list,
                "conflicts_noted": list,
                "knowledge_type": "internal" | "external" | "hybrid"
            }
        """
        logger.info("Generating Astute RAG answer", query=query[:50])

        # Prepare context from consolidated knowledge
        context = self.consolidator.format_for_answer_generation(
            consolidated,
            include_conflicts=True,
            min_reliability=0.4,
        )

        # Determine primary knowledge source
        consistent_count = len(consolidated.get("consistent_facts", []))
        external_count = len(consolidated.get("external_only", []))
        internal_count = len(consolidated.get("internal_only", []))
        conflicts = consolidated.get("conflicts", [])

        if consistent_count > 0:
            knowledge_type = "hybrid"
        elif external_count > internal_count:
            knowledge_type = "external"
        else:
            knowledge_type = "internal"

        # Build conflict notes
        conflict_notes = []
        for c in conflicts:
            conflict_notes.append({
                "type": c.get("conflict_type", "unknown"),
                "description": c.get("description", ""),
                "internal": c.get("internal", "")[:100],
                "external": c.get("external", "")[:100],
            })

        # Generate answer
        answer_prompt = f"""基於以下經過驗證和評分的資訊回答問題。

【問題】
{query}

{context}

【回答要求】
1. 優先使用「高可靠性資訊」
2. 使用「來自文件的資訊」時，可標注來源
3. 使用「來自背景知識」的資訊時，語氣應較保守
4. 如有「資訊衝突」，應客觀呈現不同觀點
5. 如果資訊不足以回答問題，請誠實說明

請提供專業、準確的回答："""

        try:
            answer = await llm_service.analyze_text(
                text="",
                user_instruction=answer_prompt,
                provider=provider,
                model_name=model_name,
                local_url=local_url,
            )

            # Calculate overall confidence
            reliability_dist = consolidated.get("reliability_distribution", {})
            high_count = reliability_dist.get("high", 0)
            total = consolidated.get("total_facts", 1)
            confidence = min((high_count / max(total, 1)) * 1.2, 1.0)  # Boost for high reliability

            # Adjust confidence based on conflicts
            if conflicts:
                confidence = max(confidence - 0.1 * len(conflicts), 0.3)

            # Compile sources used
            sources_used = []
            for fact in consolidated.get("consistent_facts", []):
                sources_used.append({
                    "text": fact.get("text", "")[:100],
                    "type": "consistent",
                    "reliability": fact.get("reliability_score", 0),
                })
            for fact in consolidated.get("external_only", [])[:3]:
                sources_used.append({
                    "text": fact.get("text", "")[:100],
                    "type": "external",
                    "reliability": fact.get("reliability_score", 0),
                })

            return {
                "answer": answer,
                "confidence": round(confidence, 2),
                "sources_used": sources_used,
                "conflicts_noted": conflict_notes,
                "knowledge_type": knowledge_type,
                "reliability_distribution": reliability_dist,
            }

        except Exception as e:
            logger.error("Astute answer generation failed", error=str(e))
            # Fallback to internal knowledge
            return {
                "answer": internal_knowledge.get("internal_answer", "無法生成回答"),
                "confidence": internal_knowledge.get("confidence", 0.3) * 0.5,
                "sources_used": [],
                "conflicts_noted": [],
                "knowledge_type": "internal",
                "error": str(e),
            }

    # =========================================================================
    # Main Query Pipeline
    # =========================================================================

    async def query(
        self,
        query: str,
        rag_service: Any,  # RAGService instance
        collection_name: str | None = None,
        n_results: int = 5,
        use_hybrid: bool = True,
        use_rerank: bool = True,
        provider: str | None = None,
        model_name: str | None = None,
        local_url: str | None = None,
        force_retrieval: bool = False,
    ) -> dict[str, Any]:
        """
        Execute full Astute RAG query pipeline.

        Pipeline:
        1. Elicit internal knowledge from LLM
        2. Decide if retrieval is needed
        3. Perform retrieval (if needed)
        4. Consolidate internal and external knowledge
        5. Generate reliability-based answer

        Args:
            query: User's question
            rag_service: RAGService instance for retrieval
            collection_name: Document collection to search
            n_results: Number of results to retrieve
            use_hybrid: Use hybrid search
            use_rerank: Use reranking
            provider: LLM provider
            model_name: Model name
            local_url: Local LLM URL
            force_retrieval: Always perform retrieval

        Returns:
            Complete Astute RAG response with answer, sources, conflicts, etc.
        """
        logger.info("Starting Astute RAG query", query=query[:50])

        # Step 1: Elicit internal knowledge
        internal_knowledge = await self.elicit_internal_knowledge(
            query=query,
            provider=provider,
            model_name=model_name,
            local_url=local_url,
        )

        # Step 2: Decide on retrieval
        decision = await self.classify_query_need(
            query=query,
            internal_confidence=internal_knowledge["confidence"],
            knowledge_gaps=internal_knowledge["knowledge_gaps"],
        )

        logger.info(
            "Query decision",
            decision=decision.value,
            internal_confidence=internal_knowledge["confidence"],
        )

        # Step 3: Perform retrieval if needed
        retrieved_passages = []
        retrieval_stats = {}

        if force_retrieval or decision != QueryDecision.INTERNAL_SUFFICIENT:
            try:
                retrieval_result = await rag_service.get_optimized_context(
                    query=query,
                    collection_name=collection_name,
                    n_results=n_results,
                    use_hybrid=use_hybrid,
                    use_rerank=use_rerank,
                )
                retrieved_passages = retrieval_result.get("sources", [])
                retrieval_stats = retrieval_result.get("stats", {})
            except Exception as e:
                logger.error("Retrieval failed", error=str(e))
                # Continue with internal knowledge only

        # Step 4: Consolidate knowledge
        if retrieved_passages:
            consolidated = await self.consolidator.consolidate(
                query=query,
                internal_knowledge=internal_knowledge,
                retrieved_passages=retrieved_passages,
                provider=provider,
                model_name=model_name,
                local_url=local_url,
            )
        else:
            # No retrieval - use internal knowledge only
            consolidated = {
                "consistent_facts": [],
                "conflicts": [],
                "external_only": [],
                "internal_only": [
                    {
                        "text": fact,
                        "source_type": SourceType.INTERNAL.value,
                        "reliability_score": internal_knowledge["confidence"],
                        "reliability_detail": "僅來自 LLM 內部知識",
                    }
                    for fact in internal_knowledge.get("key_facts", [])
                ],
                "consolidation_summary": "未進行檢索，僅使用內部知識",
                "total_facts": len(internal_knowledge.get("key_facts", [])),
                "reliability_distribution": {"high": 0, "medium": 0, "low": 0},
            }

        # Step 5: Generate final answer
        result = await self.generate_astute_answer(
            query=query,
            consolidated=consolidated,
            internal_knowledge=internal_knowledge,
            provider=provider,
            model_name=model_name,
            local_url=local_url,
        )

        # Add metadata
        result["query_decision"] = decision.value
        result["internal_confidence"] = internal_knowledge["confidence"]
        result["retrieval_performed"] = len(retrieved_passages) > 0
        result["retrieval_stats"] = retrieval_stats
        result["consolidation_summary"] = consolidated.get("consolidation_summary", "")

        return result


# Singleton instance
astute_rag_service = AstuteRAGService()
