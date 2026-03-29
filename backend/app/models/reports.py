"""Pydantic models for Report API requests and responses."""

from app.models.llm import LLMConfig
from pydantic import BaseModel, Field


class SkillInfo(BaseModel):
    """Information about an expert skill."""

    id: str
    name: str
    description: str
    category: str
    prompt_fragment: str


class ReportGenerateRequest(BaseModel):
    """Request for report generation."""

    template_name: str = Field(..., description="Name of the report template")
    selected_skills: list[str] = Field(default_factory=list, description="IDs of selected agent skills")
    file_path: str | None = Field(default=None, description="Source file path for the report")
    user_instruction: str = Field(default="", description="Optional customization instructions")
    config: LLMConfig = Field(default_factory=LLMConfig)
    use_fact_checker: bool = Field(default=False, description="Enable AI fact checking")


class ReportResponse(BaseModel):
    """Response from report generation."""

    report_id: str
    content: str
    docx_path: str | None = None
    fact_check_results: list[dict] | None = None
