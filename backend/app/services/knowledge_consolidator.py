"""
Knowledge Consolidator for Astute RAG.

Consolidates information from LLM internal knowledge and external retrieval,
identifying consistencies, conflicts, and information gaps.
"""

import json
from typing import Any

import structlog
from app.services.llm_service import llm_service
from app.services.reliability_scorer import (
    ReliabilityScorer,
    SourceType,
    reliability_scorer,
)

logger = structlog.get_logger()


class KnowledgeConsolidator:
    """
    Consolidates internal (LLM) and external (retrieved) knowledge.

    Key responsibilities:
    1. Compare internal and external knowledge
    2. Identify consistent and conflicting information
    3. Assess reliability of each piece of information
    4. Produce a unified knowledge base for answer generation
    """

    def __init__(
        self,
        scorer: ReliabilityScorer | None = None,
    ) -> None:
        """Initialize consolidator with scorer."""
        self.scorer = scorer or reliability_scorer

    async def consolidate(
        self,
        query: str,
        internal_knowledge: dict[str, Any],
        retrieved_passages: list[dict[str, Any]],
        provider: str | None = None,
        model_name: str | None = None,
        local_url: str | None = None,
    ) -> dict[str, Any]:
        """
        Consolidate internal and external knowledge.

        Args:
            query: Original user query
            internal_knowledge: LLM's internal knowledge response
            retrieved_passages: Retrieved document passages
            provider: LLM provider for consolidation
            model_name: Model name
            local_url: Local LLM URL if applicable

        Returns:
            {
                "consistent_facts": list,   # Facts confirmed by both sources
                "conflicts": list,          # Conflicting information
                "external_only": list,      # Only in retrieved docs
                "internal_only": list,      # Only in LLM knowledge
                "consolidation_summary": str,
                "total_facts": int,
                "reliability_distribution": dict,
            }
        """
        logger.info("Consolidating knowledge", query=query[:50])

        # Extract key facts from internal knowledge
        internal_facts = internal_knowledge.get("key_facts", [])
        internal_answer = internal_knowledge.get("internal_answer", "")
        internal_confidence = internal_knowledge.get("confidence", 0.5)

        # Format retrieved passages for comparison
        external_contents = [p.get("content", "") for p in retrieved_passages]
        external_metadata = [p.get("metadata", {}) for p in retrieved_passages]
        external_scores = [p.get("rerank_score", p.get("score", 0.5)) for p in retrieved_passages]

        # Use LLM to perform detailed consolidation
        consolidation_result = await self._llm_consolidate(
            query=query,
            internal_answer=internal_answer,
            internal_facts=internal_facts,
            external_contents=external_contents,
            provider=provider,
            model_name=model_name,
            local_url=local_url,
        )

        # Compute reliability scores for each fact category
        consistent_facts = []
        for fact in consolidation_result.get("consistent_facts", []):
            score = self.scorer.compute_score(
                fact={"text": fact},
                source_type=SourceType.BOTH,
                is_consistent=True,
                llm_confidence=internal_confidence,
                rerank_score=max(external_scores) if external_scores else 0.5,
                source_metadata=external_metadata[0] if external_metadata else {},
            )
            consistent_facts.append({
                "text": fact,
                "source_type": SourceType.BOTH.value,
                "reliability_score": score.score,
                "reliability_detail": score.explanation,
            })

        conflicts = []
        for conflict in consolidation_result.get("conflicts", []):
            conflict_type, severity = self.scorer.assess_conflict(
                internal_fact=conflict.get("internal", ""),
                external_fact=conflict.get("external", ""),
            )
            conflicts.append({
                "internal": conflict.get("internal", ""),
                "external": conflict.get("external", ""),
                "conflict_type": conflict_type.value,
                "severity": severity,
                "description": conflict.get("description", ""),
            })

        external_only = []
        for i, fact in enumerate(consolidation_result.get("external_only", [])):
            meta = external_metadata[i] if i < len(external_metadata) else {}
            ext_score = external_scores[i] if i < len(external_scores) else 0.5
            score = self.scorer.compute_score(
                fact={"text": fact},
                source_type=SourceType.EXTERNAL,
                is_consistent=False,
                rerank_score=ext_score,
                source_metadata=meta,
            )
            external_only.append({
                "text": fact,
                "source_type": SourceType.EXTERNAL.value,
                "reliability_score": score.score,
                "reliability_detail": score.explanation,
            })

        internal_only = []
        for fact in consolidation_result.get("internal_only", []):
            score = self.scorer.compute_score(
                fact={"text": fact},
                source_type=SourceType.INTERNAL,
                is_consistent=False,
                llm_confidence=internal_confidence,
            )
            internal_only.append({
                "text": fact,
                "source_type": SourceType.INTERNAL.value,
                "reliability_score": score.score,
                "reliability_detail": score.explanation,
            })

        # Compute reliability distribution
        all_scores = (
            [f["reliability_score"] for f in consistent_facts]
            + [f["reliability_score"] for f in external_only]
            + [f["reliability_score"] for f in internal_only]
        )

        reliability_distribution = {
            "high": len([s for s in all_scores if s >= 0.7]),
            "medium": len([s for s in all_scores if 0.4 <= s < 0.7]),
            "low": len([s for s in all_scores if s < 0.4]),
        }

        return {
            "consistent_facts": consistent_facts,
            "conflicts": conflicts,
            "external_only": external_only,
            "internal_only": internal_only,
            "consolidation_summary": consolidation_result.get("summary", ""),
            "total_facts": len(consistent_facts) + len(external_only) + len(internal_only),
            "reliability_distribution": reliability_distribution,
        }

    async def _llm_consolidate(
        self,
        query: str,
        internal_answer: str,
        internal_facts: list[str],
        external_contents: list[str],
        provider: str | None = None,
        model_name: str | None = None,
        local_url: str | None = None,
    ) -> dict[str, Any]:
        """Use LLM to perform detailed knowledge consolidation."""
        internal_facts_text = "\n".join(f"- {f}" for f in internal_facts) if internal_facts else "（無）"
        external_text = "\n\n".join(
            f"[文件 {i + 1}]\n{content[:500]}..." if len(content) > 500 else f"[文件 {i + 1}]\n{content}"
            for i, content in enumerate(external_contents[:5])
        )

        prompt = f"""分析以下兩個資訊來源，識別一致性與衝突。

【使用者問題】
{query}

【LLM 內部知識】
回答：{internal_answer[:500]}

關鍵事實：
{internal_facts_text}

【檢索文件內容】
{external_text if external_text else "（無檢索結果）"}

請以 JSON 格式輸出分析結果：
{{
    "consistent_facts": ["兩者都支持的事實1", "事實2", ...],
    "conflicts": [
        {{"internal": "內部知識說法", "external": "外部文件說法", "description": "衝突描述"}},
        ...
    ],
    "external_only": ["僅在外部文件中出現的重要資訊"],
    "internal_only": ["僅在內部知識中的資訊（可能需要驗證）"],
    "summary": "整體一致性評估摘要"
}}

只輸出 JSON，不要其他說明。"""

        try:
            result = await llm_service.analyze_text(
                text="",
                user_instruction=prompt,
                provider=provider,
                model_name=model_name,
                local_url=local_url,
            )

            # Parse JSON from response
            result = result.strip()
            if result.startswith("```"):
                lines = result.split("\n")
                result = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            return json.loads(result)

        except json.JSONDecodeError as e:
            logger.warning("Failed to parse consolidation JSON", error=str(e))
            return {
                "consistent_facts": [],
                "conflicts": [],
                "external_only": [],
                "internal_only": internal_facts,
                "summary": "無法完成整合分析",
            }
        except Exception as e:
            logger.error("Consolidation LLM call failed", error=str(e))
            return {
                "consistent_facts": [],
                "conflicts": [],
                "external_only": [c[:200] for c in external_contents],
                "internal_only": internal_facts,
                "summary": f"整合失敗: {e!s}",
            }

    def get_reliable_facts(
        self,
        consolidated: dict[str, Any],
        min_reliability: float = 0.5,
    ) -> list[dict[str, Any]]:
        """
        Get all facts above reliability threshold.

        Args:
            consolidated: Result from consolidate()
            min_reliability: Minimum score threshold

        Returns:
            List of reliable facts from all sources
        """
        all_facts = (
            consolidated.get("consistent_facts", [])
            + consolidated.get("external_only", [])
            + consolidated.get("internal_only", [])
        )

        return self.scorer.filter_by_reliability(all_facts, min_reliability)

    def format_for_answer_generation(
        self,
        consolidated: dict[str, Any],
        include_conflicts: bool = True,
        min_reliability: float = 0.4,
    ) -> str:
        """
        Format consolidated knowledge for final answer generation.

        Args:
            consolidated: Result from consolidate()
            include_conflicts: Whether to include conflict notes
            min_reliability: Minimum reliability to include

        Returns:
            Formatted context string for LLM
        """
        parts = []

        # High reliability facts (consistent)
        consistent = consolidated.get("consistent_facts", [])
        if consistent:
            reliable_consistent = [f for f in consistent if f.get("reliability_score", 0) >= 0.7]
            if reliable_consistent:
                parts.append("【高可靠性資訊（來源一致）】")
                for f in reliable_consistent:
                    parts.append(f"• {f['text']}")

        # Medium reliability external facts
        external = consolidated.get("external_only", [])
        reliable_external = [f for f in external if f.get("reliability_score", 0) >= min_reliability]
        if reliable_external:
            parts.append("\n【來自文件的資訊】")
            for f in reliable_external:
                score = f.get("reliability_score", 0)
                parts.append(f"• {f['text']} (可靠性: {score:.0%})")

        # Internal knowledge (with caveat)
        internal = consolidated.get("internal_only", [])
        reliable_internal = [f for f in internal if f.get("reliability_score", 0) >= min_reliability]
        if reliable_internal:
            parts.append("\n【來自背景知識（待驗證）】")
            for f in reliable_internal:
                parts.append(f"• {f['text']}")

        # Conflicts (if requested)
        if include_conflicts:
            conflicts = consolidated.get("conflicts", [])
            if conflicts:
                parts.append("\n【⚠️ 資訊衝突（請謹慎使用）】")
                for c in conflicts:
                    parts.append(f"• 內部: {c.get('internal', '?')}")
                    parts.append(f"  外部: {c.get('external', '?')}")
                    if c.get("description"):
                        parts.append(f"  說明: {c['description']}")

        return "\n".join(parts)


# Singleton instance
knowledge_consolidator = KnowledgeConsolidator()
