"""Pydantic models for Prediction Modeling API."""

from typing import Any

from pydantic import BaseModel


class LLMConfig(BaseModel):
    """LLM Configuration for AI interpretation."""

    provider: str = "gemini"
    model_name: str = "gemini-2.0-flash-exp"
    local_url: str | None = None
    api_key: str | None = None


class RegressionRequest(BaseModel):
    """Request for Linear Regression."""

    file_path: str
    feature_cols: list[str]
    target_col: str
    test_size: float = 0.2
    config: LLMConfig | None = None


class RegressionResponse(BaseModel):
    """Response from Linear Regression."""

    coefficients: dict[str, float]
    intercept: float
    r2_score: float
    rmse: float
    predictions: list[float]
    actual: list[float]
    feature_importance: list[dict[str, Any]] | None = None
    interpretation: str | None = None


class TimeSeriesRequest(BaseModel):
    """Request for Time Series analysis."""

    file_path: str
    date_col: str
    value_col: str
    forecast_periods: int = 12
    config: LLMConfig | None = None


class TimeSeriesResponse(BaseModel):
    """Response from Time Series analysis."""

    trend: list[float | None]
    seasonal: list[float | None]
    residual: list[float | None]
    dates: list[str]
    values: list[float]
    forecast: list[float] | None = None
    forecast_dates: list[str] | None = None
    interpretation: str | None = None


class ClassificationRequest(BaseModel):
    """Request for Classification (Logistic Regression)."""

    file_path: str
    feature_cols: list[str]
    target_col: str
    test_size: float = 0.2
    config: LLMConfig | None = None


class ClassificationResponse(BaseModel):
    """Response from Classification."""

    model_type: str
    classes: list[Any]
    coefficients: dict[str, float]
    metrics: dict[str, float]  # accuracy, precision, recall, f1
    confusion_matrix: list[list[int]]
    roc_curve: dict[str, Any] | None = None  # {fpr, tpr, auc}
    predictions: list[Any]
    actual: list[Any]
    feature_importance: list[dict[str, Any]] | None = None
    interpretation: str | None = None
