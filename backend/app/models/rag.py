"""Pydantic models for RAG API requests and responses."""

from typing import Any

from app.models.llm import LLMConfig
from pydantic import BaseModel, Field


class RAGQueryRequest(BaseModel):
    """Request for RAG query."""

    question: str = Field(..., description="User question")
    collection_names: list[str] = Field(..., description="Document collections to search")
    n_results: int = Field(default=5, description="Number of results to retrieve")
    use_rerank: bool = Field(default=True, description="Enable reranking")
    use_hybrid: bool = Field(default=True, description="Enable hybrid search (vector + keyword)")
    use_query_expansion: bool = Field(default=False, description="Enable LLM-based query expansion")
    use_compression: bool = Field(default=False, description="Enable context compression")
    compression_method: str = Field(default="extractive", description="Compression method: extractive or summary")
    use_web_search: bool = Field(default=False, description="Enable web search verification")
    use_strategy: bool = Field(default=False, description="Apply business strategy framework")
    config: LLMConfig = Field(default_factory=LLMConfig)
    fast_config: LLMConfig | None = Field(default=None, description="Optional config for fast/background tasks")


class RAGIndexRequest(BaseModel):
    """Request to index a document."""

    file_path: str = Field(..., description="Path to file to index")
    chunking_strategy: str = Field(default="semantic", description="Chunking strategy: semantic or fixed")


class DocumentInfo(BaseModel):
    """Information about an indexed document."""

    collection_name: str = Field(..., description="Collection identifier")
    file_name: str = Field(..., description="Original file name")
    chunk_count: int = Field(..., description="Number of chunks")
    indexed_at: str = Field(..., description="Indexing timestamp")


class RAGIndexResponse(BaseModel):
    """Response from document indexing."""

    success: bool = Field(..., description="Whether indexing succeeded")
    collection_name: str | None = Field(default=None, description="Created collection name")
    message: str = Field(..., description="Status message")


class RAGQueryResponse(BaseModel):
    """Response from RAG query."""

    answer: str = Field(..., description="Generated answer")
    sources: list[dict[str, Any]] = Field(default_factory=list, description="Retrieved source chunks")


# ========== Astute RAG Models ==========


class AstuteRAGQueryRequest(BaseModel):
    """Request for Astute RAG query with internal knowledge elicitation."""

    question: str = Field(..., description="User question")
    collection_names: list[str] = Field(default_factory=list, description="Document collections to search (optional)")
    n_results: int = Field(default=5, description="Number of results to retrieve")
    use_hybrid: bool = Field(default=True, description="Enable hybrid search")
    use_rerank: bool = Field(default=True, description="Enable reranking")
    force_retrieval: bool = Field(default=False, description="Always perform retrieval even if LLM is confident")
    config: LLMConfig = Field(default_factory=LLMConfig)


class InternalKnowledgeResponse(BaseModel):
    """Response from internal knowledge elicitation."""

    internal_answer: str = Field(..., description="LLM's preliminary answer")
    confidence: float = Field(..., ge=0, le=1, description="Self-assessed confidence (0-1)")
    key_facts: list[str] = Field(default_factory=list, description="Extracted key facts")
    knowledge_gaps: list[str] = Field(default_factory=list, description="Identified knowledge gaps")
    needs_retrieval: bool = Field(..., description="Whether retrieval is recommended")


class ConflictInfo(BaseModel):
    """Information about a knowledge conflict."""

    conflict_type: str = Field(..., description="Type of conflict: factual, semantic, scope")
    description: str = Field(default="", description="Description of the conflict")
    internal: str = Field(default="", description="Internal knowledge claim")
    external: str = Field(default="", description="External document claim")


class SourceInfo(BaseModel):
    """Information about a source used in the answer."""

    text: str = Field(..., description="Source text excerpt")
    source_type: str = Field(..., description="Type: consistent, external, internal")
    reliability: float = Field(..., ge=0, le=1, description="Reliability score")


class ReliabilityDistribution(BaseModel):
    """Distribution of reliability scores."""

    high: int = Field(default=0, description="Count of high reliability facts (>=0.7)")
    medium: int = Field(default=0, description="Count of medium reliability facts (0.4-0.7)")
    low: int = Field(default=0, description="Count of low reliability facts (<0.4)")


class AstuteRAGQueryResponse(BaseModel):
    """Response from Astute RAG query with reliability information."""

    answer: str = Field(..., description="Generated answer")
    confidence: float = Field(..., ge=0, le=1, description="Overall confidence in the answer")
    sources_used: list[SourceInfo] = Field(default_factory=list, description="Sources used in the answer")
    conflicts_noted: list[ConflictInfo] = Field(default_factory=list, description="Knowledge conflicts detected")
    knowledge_type: str = Field(..., description="Primary knowledge source: internal, external, hybrid")
    query_decision: str = Field(..., description="Decision on query handling")
    internal_confidence: float = Field(..., description="LLM's initial confidence")
    retrieval_performed: bool = Field(..., description="Whether retrieval was performed")
    consolidation_summary: str = Field(default="", description="Summary of knowledge consolidation")
    reliability_distribution: ReliabilityDistribution = Field(
        default_factory=ReliabilityDistribution,
        description="Distribution of reliability scores"
    )


class VerifyAnswerRequest(BaseModel):
    """Request to verify an existing answer against documents."""

    answer: str = Field(..., description="Answer to verify")
    question: str = Field(..., description="Original question")
    collection_names: list[str] = Field(..., description="Document collections to verify against")
    config: LLMConfig = Field(default_factory=LLMConfig)


class VerifyAnswerResponse(BaseModel):
    """Response from answer verification."""

    is_verified: bool = Field(..., description="Whether the answer is verified")
    confidence: float = Field(..., ge=0, le=1, description="Verification confidence")
    supporting_facts: list[str] = Field(default_factory=list, description="Facts supporting the answer")
    contradicting_facts: list[str] = Field(default_factory=list, description="Facts contradicting the answer")
    summary: str = Field(..., description="Verification summary")

