"""LLM API endpoints with SSE streaming support."""

import asyncio
import io
import logging
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.api.auth import get_current_user
from app.models.llm import (
    AnalyzeFileRequest,
    AnalyzeRequest,
    FileQueryRequest,
    LLMResponse,
    QueryFixRequest,
    QueryRequest,
    TokenEstimationRequest,
    TokenEstimationResponse,
)
from app.models.user import User
from app.services.llm_queue import acquire_llm, release_llm
from app.services.llm_service import llm_service

router = APIRouter()


async def stream_response(content: str) -> AsyncGenerator[dict[str, str], None]:
    """Stream response content word by word for SSE."""
    words = content.split()
    buffer = ""
    for i, word in enumerate(words):
        buffer += word + " "
        # Yield every few words for smoother streaming
        if i % 3 == 0 or i == len(words) - 1:
            yield {"event": "message", "data": buffer}
            buffer = ""
        await asyncio.sleep(0.02)  # Small delay for visual effect
    yield {"event": "done", "data": "[DONE]"}


async def stream_response_with_queue(
    content: str,
    queue_position: int | None = None,
    wait_time: float | None = None,
) -> AsyncGenerator[dict[str, str], None]:
    """Stream response with queue status."""
    if queue_position is not None:
        yield {
            "event": "queue_status",
            "data": f"queue_position:{queue_position},estimated_wait:{wait_time or 0}",
        }
    async for chunk in stream_response(content):
        yield chunk


@router.get("/queue/status")
async def get_queue_status(
    current_user: Annotated[User | None, Depends(get_current_user)] = None,
) -> dict:
    """取得 LLM 佇列狀態。"""
    from app.services.llm_queue import llm_queue

    status = llm_queue.get_status()
    user_position = None

    if current_user:
        user_info = llm_queue.get_user_position(current_user.id)
        if user_info:
            user_position = user_info["position"]

    return {
        "queue_length": status["queue_length"],
        "active_count": status["active_count"],
        "your_position": user_position,
        "is_available": status["active_count"] < status["max_concurrent"]
        and status["queue_length"] == 0,
    }


@router.post("/analyze", response_model=LLMResponse)
async def analyze_text(
    request: AnalyzeRequest,
    current_user: Annotated[User | None, Depends(get_current_user)] = None,
) -> LLMResponse:
    """Analyze text content using LLM with queue management."""
    user_id = current_user.id if current_user else None
    queue_item = await acquire_llm("analyze", user_id=user_id)

    try:
        result = await llm_service.analyze_text(
            text_content=request.content,
            user_instruction=request.instruction,
            provider=request.config.provider,
            model_name=request.config.model_name,
            local_url=request.config.local_url,
            context_window=request.config.context_window,
            financial_skepticism=request.financial_skepticism,
            api_key=request.config.api_key,
        )
        return LLMResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        await release_llm(queue_item)


@router.post("/analyze/stream")
async def analyze_text_stream(
    request: AnalyzeRequest,
    current_user: Annotated[User | None, Depends(get_current_user)] = None,
) -> EventSourceResponse:
    """Analyze text with SSE streaming response and queue management."""
    user_id = current_user.id if current_user else None
    queue_item = await acquire_llm("analyze_stream", user_id=user_id)

    try:
        result = await llm_service.analyze_text(
            text_content=request.content,
            user_instruction=request.instruction,
            provider=request.config.provider,
            model_name=request.config.model_name,
            local_url=request.config.local_url,
            context_window=request.config.context_window,
            financial_skepticism=request.financial_skepticism,
            api_key=request.config.api_key,
        )
        return EventSourceResponse(
            stream_response_with_queue(
                result,
                queue_position=queue_item.position
                if queue_item.status.value == "waiting"
                else None,
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        await release_llm(queue_item)


@router.post("/analyze-file", response_model=LLMResponse)
async def analyze_file(request: AnalyzeFileRequest) -> LLMResponse:
    """Analyze file content using LLM."""
    try:
        result = await llm_service.analyze_file(
            file_path=request.file_path,
            user_instruction=request.instruction,
            provider=request.config.provider,
            model_name=request.config.model_name,
            local_url=request.config.local_url,
            context_window=request.config.context_window,
            financial_skepticism=request.financial_skepticism,
            api_key=request.config.api_key,
        )
        return LLMResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/analyze-file/stream")
async def analyze_file_stream(request: AnalyzeFileRequest) -> EventSourceResponse:
    """Analyze file with SSE streaming response."""
    try:
        result = await llm_service.analyze_file(
            file_path=request.file_path,
            user_instruction=request.instruction,
            provider=request.config.provider,
            model_name=request.config.model_name,
            local_url=request.config.local_url,
            context_window=request.config.context_window,
            financial_skepticism=request.financial_skepticism,
            api_key=request.config.api_key,
        )
        return EventSourceResponse(stream_response(result))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/query", response_model=LLMResponse)
async def generate_query(request: QueryRequest | FileQueryRequest) -> LLMResponse:
    """Generate pandas query from natural language."""
    try:
        columns_info = ""
        sample_data = ""

        # Handle File Query
        if isinstance(request, FileQueryRequest) or hasattr(request, "file_path"):
            import os

            import pandas as pd

            from app.utils.excel_processor import smart_read_excel

            file_path = request.file_path
            ext = os.path.splitext(file_path)[1].lower()
            df = None

            if ext == ".csv":
                df = pd.read_csv(file_path)
            elif ext in [".xlsx", ".xls"]:
                df = smart_read_excel(file_path)
            elif ext == ".json":
                df = pd.read_json(file_path)

            if df is not None:
                # Prepare Schema Info
                buffer = io.StringIO()
                df.info(buf=buffer)
                columns_info = buffer.getvalue()

                # Prepare Sample Data (Top 5 rows as markdown)
                sample_data = df.head(5).to_markdown(index=False)
        else:
            # Handle standard QueryRequest
            columns_info = request.columns_info
            sample_data = request.sample_data

        result = await llm_service.generate_pandas_query(
            question=request.question,
            df_info={"columns": columns_info, "sample": sample_data},
            provider=request.config.provider,
            model_name=request.config.model_name,
            local_url=request.config.local_url,
            context_window=request.config.context_window,
            api_key=request.config.api_key,
        )
        return LLMResponse(content=result)
    except Exception as e:
        logging.exception("Query generation failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/query/fix", response_model=LLMResponse)
async def fix_query(request: QueryFixRequest) -> LLMResponse:
    """Fix pandas query errors using LLM."""
    try:
        result = await llm_service.analyze_text(
            text_content="",
            user_instruction=(
                f"Fix this query: {request.original_code}"
                f"\nError: {request.error_message}"
            ),
            provider=request.config.provider,
            model_name=request.config.model_name,
            local_url=request.config.local_url,
            context_window=request.config.context_window,
            api_key=request.config.api_key,
        )
        return LLMResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e



class InterpretRequest(BaseModel):
    question: str
    results_summary: str
    unit: str = "元"
    provider: str = "ollama"
    model_name: str = "llama3.2"
    local_url: str = "http://localhost:11434"
    api_key: str | None = None
    context_window: int = 16384


class ModelsRequest(BaseModel):
    provider: str = "Local (LM Studio)"
    local_url: str = "http://localhost:1234/v1"
    api_key: str | None = None


@router.post("/interpret", response_model=LLMResponse)
async def interpret_results(request: InterpretRequest) -> LLMResponse:
    """Interpret analysis results using LLM."""
    try:
        result = await llm_service.analyze_text(
            text_content="",
            user_instruction=f"目標：{request.question}\n摘要：{request.results_summary}\n單位：{request.unit}",
            provider=request.provider,
            model_name=request.model_name,
            local_url=request.local_url,
            context_window=request.context_window,
            api_key=request.api_key,
        )
        return LLMResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/models", response_model=list[str])
async def list_models(request: ModelsRequest) -> list[str]:
    """List available models from the specified provider."""
    try:
        models = await llm_service.list_models(
            provider=request.provider,
            local_url=request.local_url,
            api_key_input=request.api_key,
        )
        return models
    except Exception as e:
        import logging

        logging.exception("Failed to list models")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/models", response_model=list[str])
async def list_models_get(
    provider: str = "Local (LM Studio)",
    local_url: str = "http://localhost:1234/v1",
    api_key: str | None = None,
) -> list[str]:
    """List available models from the specified provider (GET)."""
    try:
        models = await llm_service.list_models(
            provider=provider, local_url=local_url, api_key_input=api_key
        )
        return models
    except Exception as e:
        logging.exception("Failed to list models (GET)")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/estimate-tokens", response_model=TokenEstimationResponse)
async def estimate_tokens(request: TokenEstimationRequest) -> TokenEstimationResponse:
    """Estimate token usage before running analysis.

    Returns a breakdown of:
    - system_prompt_tokens: tokens in the system prompt
    - content_tokens: tokens in just the file/text content
    - user_prompt_tokens: tokens in the full user prompt (instruction + content)
    - total_tokens: system + user prompt tokens
    - fits_in_context: whether total fits in the configured context window
    """
    try:
        result = await llm_service.estimate_analysis_tokens(
            file_path=request.file_path,
            text_content=request.text_content,
            instruction=request.instruction,
            context_window=request.config.context_window,
            financial_skepticism=request.financial_skepticism,
        )
        return TokenEstimationResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
