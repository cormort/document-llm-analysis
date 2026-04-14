"""Pydantic models for Statistics API."""

from typing import Any

from app.models.llm import LLMConfig
from pydantic import BaseModel, Field


class DiagnosticRequest(BaseModel):
    file_path: str
    config: LLMConfig = Field(default_factory=LLMConfig)

class DataQualityItem(BaseModel):
    column: str
    dtype: str
    missing_count: int
    missing_percentage: float
    unique_count: int
    sample_values: list[Any]

class DiagnosticResponse(BaseModel):
    summary_stats: dict[str, Any]
    quality_report: list[DataQualityItem]
    interpretation: str | None = None

class EDARequest(BaseModel):
    file_path: str
    analysis_type: str = Field(..., description="correlation, groupby, trend, pivot")
    params: dict[str, Any] = Field(default_factory=dict)
    config: LLMConfig = Field(default_factory=LLMConfig)
    skip_interpretation: bool = False

class EDAResponse(BaseModel):
    result_data: Any
    interpretation: str | None = None

class StatTestRequest(BaseModel):
    file_path: str
    test_type: str = Field(..., description="ttest, anova, shapiro, outliers, chi_square, mann_whitney, kruskal, wilcoxon")
    target_columns: list[str]
    group_column: str | None = None
    config: LLMConfig = Field(default_factory=LLMConfig)

class StatTestResponse(BaseModel):
    test_results: dict[str, Any]
    interpretation: str | None = None
    suggestion: dict[str, Any] | None = None

class MultivariateRequest(BaseModel):
    file_path: str
    analysis_type: str = Field(..., description="pca, kmeans")
    features: list[str] = Field(..., description="List of feature column names")
    n_components: int = Field(2, description="Number of components for PCA")
    n_clusters: int = Field(3, description="Number of clusters for KMeans")
    config: LLMConfig = Field(default_factory=LLMConfig)

class MultivariateResponse(BaseModel):
    analysis_type: str
    data: list[dict[str, Any]]
    components_variance: list[float] | None = None
    feature_weights: dict[str, list[float]] | None = None
    cluster_centers: dict[str, dict[str, float]] | None = None
    interpretation: str | None = None

class InterpretStatsRequest(BaseModel):
    context: str
    data_summary: str
    test_type: str
    config: LLMConfig = Field(default_factory=LLMConfig)

class InterpretStatsResponse(BaseModel):
    interpretation: str

class TransformRequest(BaseModel):
    file_path: str
    new_column: str
    expression: str
    config: LLMConfig = Field(default_factory=LLMConfig)

class TransformResponse(BaseModel):
    success: bool
    new_column: str
    values: list[Any]
    preview: list[dict[str, Any]]

class GetDataRequest(BaseModel):
    file_path: str
    columns: list[str]

class FieldAnalysisRequest(BaseModel):
    field_name: str
    stats: dict[str, Any]
    sample_values: list[Any]
    config: LLMConfig = Field(default_factory=LLMConfig)

class FieldAnalysisResponse(BaseModel):
    interpretation: str

class FeatureSuggestionsRequest(BaseModel):
    schema_info: str
    config: LLMConfig = Field(default_factory=LLMConfig)

class FeatureSuggestionsResponse(BaseModel):
    suggestions: str


class DatasetAnalysisRequest(BaseModel):
    summary_text: str
    config: LLMConfig = Field(default_factory=LLMConfig)


class DatasetAnalysisResponse(BaseModel):
    interpretation: str



# Data Prep Models
class ImputeRequest(BaseModel):
    file_path: str
    column: str
    method: str = Field(..., description="mean, median, mode, constant")
    fill_value: Any = None

class EncodeRequest(BaseModel):
    file_path: str
    column: str
    method: str = Field(..., description="label, onehot")

class DataPrepResponse(BaseModel):
    success: bool
    message: str
    new_columns: list[str] = []
    preview: list[dict[str, Any]]

# DuckDB SQL Query Models
class SQLQueryRequest(BaseModel):
    """Request model for DuckDB SQL queries."""
    file_path: str
    sql: str
    config: LLMConfig = Field(default_factory=LLMConfig)


class SQLQueryResponse(BaseModel):
    """Response model for DuckDB SQL query results."""
    success: bool
    data: list[dict[str, Any]] | None = None
    summary: str | None = None
    error: str | None = None
    execution_time_ms: float | None = None


class NLToSQLRequest(BaseModel):
    """Request model for natural language to SQL conversion."""
    file_path: str
    question: str
    config: LLMConfig = Field(default_factory=LLMConfig)


class NLToSQLResponse(BaseModel):
    """Response model with generated SQL and results."""
    sql: str
    success: bool
    data: list[dict[str, Any]] | None = None
    summary: str | None = None
    interpretation: str | None = None
    error: str | None = None
