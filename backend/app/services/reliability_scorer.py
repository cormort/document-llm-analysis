"""
Reliability Scorer for Astute RAG.

Provides mechanisms to assess the reliability of information
based on source consistency, provenance, and confidence metrics.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class SourceType(str, Enum):
    """Information source type."""

    INTERNAL = "internal"  # LLM internal knowledge
    EXTERNAL = "external"  # Retrieved from documents
    BOTH = "both"  # Confirmed by both sources


class ConflictType(str, Enum):
    """Types of knowledge conflicts."""

    NONE = "none"
    FACTUAL = "factual"  # Numbers, dates, names differ
    SEMANTIC = "semantic"  # Same concept, contradictory meaning
    SCOPE = "scope"  # Different coverage/granularity


@dataclass
class ReliabilityScore:
    """Reliability assessment result."""

    score: float  # 0-1 reliability score
    source_type: SourceType
    consistency_bonus: float
    source_credibility: float
    rerank_weight: float
    confidence_weight: float
    recency_weight: float
    conflict_type: ConflictType = ConflictType.NONE
    explanation: str = ""


class ReliabilityScorer:
    """
    Computes reliability scores for information based on multiple factors.

    Scoring factors:
    - Source consistency (+0.3 if internal and external agree)
    - Source credibility (+0.2 for official/authoritative docs)
    - Rerank score weight (+0.2)
    - LLM confidence (+0.2)
    - Information recency (+0.1)
    """

    def __init__(
        self,
        consistency_weight: float = 0.30,
        credibility_weight: float = 0.20,
        rerank_weight: float = 0.20,
        confidence_weight: float = 0.20,
        recency_weight: float = 0.10,
    ) -> None:
        """Initialize scorer with customizable weights."""
        self.consistency_weight = consistency_weight
        self.credibility_weight = credibility_weight
        self.rerank_weight = rerank_weight
        self.confidence_weight = confidence_weight
        self.recency_weight = recency_weight

    def compute_score(
        self,
        fact: dict[str, Any],
        source_type: SourceType,
        is_consistent: bool = False,
        rerank_score: float = 0.0,
        llm_confidence: float = 0.5,
        is_recent: bool = True,
        source_metadata: dict[str, Any] | None = None,
    ) -> ReliabilityScore:
        """
        Compute reliability score for a piece of information.

        Args:
            fact: The information/fact being scored
            source_type: Where the information comes from
            is_consistent: Whether internal and external sources agree
            rerank_score: Score from cross-encoder reranking (0-1)
            llm_confidence: LLM's self-assessed confidence (0-1)
            is_recent: Whether the information is recent
            source_metadata: Additional metadata about the source

        Returns:
            ReliabilityScore with detailed breakdown
        """
        source_metadata = source_metadata or {}

        # 1. Consistency bonus
        consistency_bonus = self.consistency_weight if is_consistent else 0.0
        if source_type == SourceType.BOTH:
            consistency_bonus = self.consistency_weight  # Confirmed by both

        # 2. Source credibility
        source_credibility = self._compute_credibility(source_metadata)

        # 3. Rerank weight (normalize to 0-1 if needed)
        normalized_rerank = min(max(rerank_score, 0.0), 1.0) * self.rerank_weight

        # 4. Confidence weight
        normalized_confidence = min(max(llm_confidence, 0.0), 1.0) * self.confidence_weight

        # 5. Recency weight
        recency_contribution = self.recency_weight if is_recent else 0.0

        # Calculate total score
        total_score = (
            consistency_bonus
            + source_credibility
            + normalized_rerank
            + normalized_confidence
            + recency_contribution
        )

        # Clamp to [0, 1]
        total_score = min(max(total_score, 0.0), 1.0)

        return ReliabilityScore(
            score=total_score,
            source_type=source_type,
            consistency_bonus=consistency_bonus,
            source_credibility=source_credibility,
            rerank_weight=normalized_rerank,
            confidence_weight=normalized_confidence,
            recency_weight=recency_contribution,
            explanation=self._generate_explanation(
                total_score, is_consistent, source_type, source_credibility
            ),
        )

    def _compute_credibility(self, metadata: dict[str, Any]) -> float:
        """Compute source credibility based on metadata."""
        credibility = 0.0
        max_credibility = self.credibility_weight

        # Check for authoritative indicators
        file_type = metadata.get("file_type", "").lower()
        file_name = metadata.get("file_name", "").lower()

        # Official document types get higher credibility
        official_extensions = {".pdf", ".docx", ".xlsx"}
        if file_type in official_extensions:
            credibility += max_credibility * 0.4

        # Named sources
        if file_name and file_name != "unknown":
            credibility += max_credibility * 0.3

        # Has structured metadata
        if metadata.get("indexed_at") or metadata.get("doc_id"):
            credibility += max_credibility * 0.3

        return min(credibility, max_credibility)

    def _generate_explanation(
        self,
        score: float,
        is_consistent: bool,
        source_type: SourceType,
        credibility: float,
    ) -> str:
        """Generate human-readable explanation for the score."""
        parts = []

        if score >= 0.8:
            parts.append("高可靠性")
        elif score >= 0.5:
            parts.append("中等可靠性")
        else:
            parts.append("低可靠性")

        if is_consistent:
            parts.append("內外部來源一致")
        elif source_type == SourceType.INTERNAL:
            parts.append("僅來自 LLM 內部知識")
        elif source_type == SourceType.EXTERNAL:
            parts.append("僅來自檢索文件")

        if credibility > 0.15:
            parts.append("來源可信度高")

        return "；".join(parts)

    def assess_conflict(
        self,
        internal_fact: str,
        external_fact: str,
    ) -> tuple[ConflictType, float]:
        """
        Assess the type and severity of conflict between facts.

        Returns:
            (ConflictType, severity 0-1)
        """
        # Simple heuristics - could be enhanced with LLM
        if not internal_fact or not external_fact:
            return ConflictType.NONE, 0.0

        # Check for exact match
        if internal_fact.strip().lower() == external_fact.strip().lower():
            return ConflictType.NONE, 0.0

        # Check for numerical differences (factual conflict)
        internal_nums = self._extract_numbers(internal_fact)
        external_nums = self._extract_numbers(external_fact)

        if internal_nums and external_nums:
            if internal_nums != external_nums:
                return ConflictType.FACTUAL, 0.8

        # If texts are different but no clear factual conflict
        # Mark as potential semantic conflict
        return ConflictType.SEMANTIC, 0.5

    def _extract_numbers(self, text: str) -> set[str]:
        """Extract numeric values from text."""
        import re

        pattern = r"\d+(?:\.\d+)?(?:%|億|萬|千|百)?"
        return set(re.findall(pattern, text))

    def filter_by_reliability(
        self,
        facts: list[dict[str, Any]],
        min_reliability: float = 0.5,
    ) -> list[dict[str, Any]]:
        """
        Filter facts by minimum reliability threshold.

        Args:
            facts: List of facts with 'reliability_score' key
            min_reliability: Minimum score to include (0-1)

        Returns:
            Filtered list of reliable facts
        """
        return [f for f in facts if f.get("reliability_score", 0) >= min_reliability]


# Singleton instance
reliability_scorer = ReliabilityScorer()
