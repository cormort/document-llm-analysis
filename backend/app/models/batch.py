"""Pydantic models for Batch Analysis API."""

from app.models.llm import LLMConfig
from pydantic import BaseModel, Field


class BatchAnalyzeRequest(BaseModel):
    """Request for batch analysis of dataframes."""

    file_path: str = Field(..., description="Path to the data file")
    group_by_cols: list[str] = Field(..., description="Columns to group by")
    metric_cols: list[str] = Field(..., description="Columns to analyze")
    analysis_mode: str = Field(default="pairwise", description="'pairwise' or 'consolidated'")
    currency_unit: str = Field(default="TWD", description="Currency unit for analysis")
    config: LLMConfig = Field(default_factory=LLMConfig)


class BatchAnalyzeResult(BaseModel):
    """Single item in batch analysis results."""

    group_value: str
    analysis_text: str
    data_summary: dict | None = None


class BatchAnalyzeResponse(BaseModel):
    """Complete response from batch analysis."""

    results: list[BatchAnalyzeResult]
    consolidated_report: str | None = None
    execution_time: float
