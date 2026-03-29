"""Pydantic models for Data Query API requests and responses."""

from pydantic import BaseModel, Field


class QueryExecuteRequest(BaseModel):
    """Request to execute generated Pandas query."""

    file_path: str = Field(..., description="Path to the CSV/Excel file")
    pandas_code: str = Field(..., description="Pandas code to execute")


class QueryExecuteResponse(BaseModel):
    """Response from query execution."""

    success: bool
    data: list[dict] | None = None
    summary: str | None = None
    error: str | None = None


class QueryFixRequest(BaseModel):
    """Request to fix a failed Pandas query."""

    file_path: str
    original_question: str
    failed_code: str
    error_message: str
