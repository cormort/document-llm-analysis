"""
LLM Service - Backward Compatibility Layer
This module re-exports from the refactored llm package for backward compatibility.
All imports should use: from app.services.llm_service import llm_service
"""

from app.services.llm.service import LLMService, llm_service

__all__ = ["LLMService", "llm_service"]
