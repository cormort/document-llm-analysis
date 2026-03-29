"""Pydantic models for LLM API requests and responses."""

from typing import Literal

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """LLM configuration for API calls."""

    provider: str = Field(default="ollama", description="LLM provider")
    model_name: str = Field(default="llama3.2", description="Model name")
    local_url: str = Field(default="http://localhost:11434", description="Local LLM URL")
    api_key: str | None = Field(default=None, description="API key for cloud providers")
    context_window: int = Field(default=16384, description="Context window size")


class AnalyzeRequest(BaseModel):
    """Request for text/file analysis."""

    content: str = Field(..., description="Text content to analyze")
    instruction: str = Field(..., description="Analysis instruction")
    config: LLMConfig = Field(default_factory=LLMConfig)
    financial_skepticism: bool = Field(default=False, description="Enable financial audit mode")


class AnalyzeFileRequest(BaseModel):
    """Request for file analysis."""

    file_path: str = Field(..., description="Path to file")
    instruction: str = Field(..., description="Analysis instruction")
    config: LLMConfig = Field(default_factory=LLMConfig)
    financial_skepticism: bool = Field(default=False, description="Enable financial audit mode")


class ChatMessage(BaseModel):
    """Chat message."""

    role: Literal["user", "assistant", "system"] = Field(..., description="Message role")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request for chat completion."""

    messages: list[ChatMessage] = Field(..., description="Chat history")
    config: LLMConfig = Field(default_factory=LLMConfig)


class QueryRequest(BaseModel):
    """Request for pandas query generation."""

    question: str = Field(..., description="Natural language question")
    columns_info: str = Field(..., description="DataFrame column information")
    sample_data: str = Field(..., description="Sample data as markdown")
    unit: str = Field(default="元", description="Currency unit")
    config: LLMConfig = Field(default_factory=LLMConfig)


class FileQueryRequest(BaseModel):
    """Request for pandas query generation from file."""

    file_path: str = Field(..., description="Path to file")
    question: str = Field(..., description="Natural language question")
    config: LLMConfig = Field(default_factory=LLMConfig)


class QueryFixRequest(BaseModel):
    """Request for fixing pandas query errors."""

    original_code: str = Field(..., description="Original code that failed")
    error_message: str = Field(..., description="Error message")
    question: str = Field(..., description="Original question")
    columns_info: str = Field(..., description="DataFrame column info")
    config: LLMConfig = Field(default_factory=LLMConfig)


class TokenEstimationRequest(BaseModel):
    """Request for token estimation before analysis."""

    file_path: str | None = Field(default=None, description="Path to file to analyze")
    text_content: str | None = Field(default=None, description="Text content to analyze")
    instruction: str = Field(default="", description="User instruction")
    config: LLMConfig = Field(default_factory=LLMConfig)
    financial_skepticism: bool = Field(
        default=False, description="Enable financial audit mode"
    )


class TokenEstimationResponse(BaseModel):
    """Response with token estimation breakdown."""

    system_prompt_tokens: int = Field(
        ..., description="Estimated tokens for the system prompt"
    )
    content_tokens: int = Field(
        ..., description="Estimated tokens for the uploaded content"
    )
    user_prompt_tokens: int = Field(
        ..., description="Estimated tokens for the full user prompt"
    )
    total_tokens: int = Field(
        ..., description="Total estimated tokens (system + user)"
    )
    context_window: int = Field(..., description="Model context window size")
    fits_in_context: bool = Field(
        ..., description="Whether total tokens fit within context window"
    )
    content_chars: int = Field(
        default=0, description="Character count of the extracted content"
    )
    truncated: bool = Field(
        default=False, description="Whether content was truncated"
    )


class LLMResponse(BaseModel):
    """Standard LLM response."""

    content: str = Field(..., description="Generated content")
    tokens_used: int | None = Field(default=None, description="Tokens consumed")
