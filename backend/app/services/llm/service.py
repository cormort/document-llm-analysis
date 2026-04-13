"""
LLM Service - Main Integration Module
Consolidated AI service supporting multiple providers and advanced analysis tasks.
"""

import asyncio
import datetime
import hashlib
from concurrent.futures import ThreadPoolExecutor
from typing import Any, AsyncGenerator

import google.generativeai as genai
import structlog

from app.core.config import settings
from app.services.document_service import document_service
from app.services.llm.analysis import AnalysisPrompts
from app.services.llm.providers import LLMProviders
from app.services.llm.token_utils import estimate_tokens_heuristic

logger = structlog.get_logger()

try:
    from app.services.cache_service import semantic_cache

    CACHE_ENABLED = True
except ImportError:
    semantic_cache = None
    CACHE_ENABLED = False
    logger.warning("Semantic cache not available")


class LLMService:
    """
    Unified LLM Service with provider abstraction and caching.

    Refactored from monolithic service into modular components:
    - providers.py: LLM provider implementations
    - analysis.py: Analysis prompts and processing
    - token_utils.py: Token estimation utilities
    """

    def __init__(self) -> None:
        self.api_key: str | None = settings.GOOGLE_API_KEY
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self._executor = ThreadPoolExecutor(max_workers=5)
        self._providers = LLMProviders(self._executor, self.api_key)

    # ==========================================
    # Token Estimation (delegated)
    # ==========================================
    @staticmethod
    def estimate_tokens_heuristic(text: str) -> int:
        """Estimate token count using character-based heuristics."""
        return estimate_tokens_heuristic(text)

    # ==========================================
    # Analysis Prompts (delegated)
    # ==========================================
    @staticmethod
    def build_analysis_prompts(
        user_instruction: str,
        file_name: str = "",
        content: str = "",
        financial_skepticism: bool = False,
    ) -> tuple[str, str]:
        """Build system and user prompts for analysis."""
        return AnalysisPrompts.build(
            user_instruction, file_name, content, financial_skepticism
        )

    async def estimate_analysis_tokens(
        self,
        file_path: str | None = None,
        text_content: str | None = None,
        instruction: str = "",
        context_window: int = 4096,
        financial_skepticism: bool = False,
    ) -> dict[str, Any]:
        """Estimate token counts for an analysis request."""
        return await AnalysisPrompts.estimate_tokens(
            file_path=file_path,
            text_content=text_content,
            instruction=instruction,
            context_window=context_window,
            financial_skepticism=financial_skepticism,
        )

    # ==========================================
    # Provider Logic & Routing
    # ==========================================
    def _get_api_key_for_provider(self, provider: str) -> str | None:
        """Return the appropriate API key for a given provider."""
        if provider == "Gemini":
            return self.api_key
        if provider == "omlx":
            return settings.OMLX_API_KEY or None
        return None

    def get_routing_config(self, task_type: str = "fast") -> dict[str, Any]:
        """Get optimal LLM configuration based on task type from global settings."""
        if task_type == "fast":
            provider = settings.LLM_FAST_PROVIDER
            local_url = (
                settings.LLM_OMLX_URL if provider == "omlx" else settings.LLM_FAST_URL
            )
            return {
                "provider": provider,
                "model_name": settings.LLM_FAST_MODEL,
                "local_url": local_url,
                "api_key_input": self._get_api_key_for_provider(provider),
            }
        elif task_type == "smart":
            provider = settings.LLM_SMART_PROVIDER
            local_url = (
                settings.LLM_OMLX_URL if provider == "omlx" else settings.LLM_SMART_URL
            )
            return {
                "provider": provider,
                "model_name": settings.LLM_SMART_MODEL,
                "local_url": local_url,
                "api_key_input": self._get_api_key_for_provider(provider),
            }

        provider = settings.LLM_SMART_PROVIDER
        local_url = (
            settings.LLM_OMLX_URL if provider == "omlx" else settings.LLM_SMART_URL
        )
        return {
            "provider": provider,
            "model_name": settings.LLM_SMART_MODEL,
            "local_url": local_url,
            "api_key_input": self._get_api_key_for_provider(provider),
        }

    # ==========================================
    # Core Generation Methods
    # ==========================================
    async def generate_text(
        self,
        prompt: str,
        provider=None,
        model_name=None,
        local_url=None,
        system_prompt="你是一位專業的助手。",
        use_cache: bool = True,
        **kwargs,
    ):
        """General purpose text generation with optional routing."""
        if not provider:
            config = self.get_routing_config("fast")
            provider = config["provider"]
            model_name = config["model_name"]
            local_url = config.get("local_url")

        model_key = f"{provider}:{model_name}"

        if use_cache and CACHE_ENABLED and semantic_cache:
            cached = semantic_cache.get(prompt, system_prompt, model_key)
            if cached:
                logger.info(
                    "LLM Cache Hit",
                    similarity=cached.get("similarity", 1.0),
                    match_type=cached.get("match_type", "exact"),
                )
                return cached["response"]

        response = await self._providers.call(
            provider,
            model_name,
            local_url,
            self.api_key,
            system_prompt,
            prompt,
            **kwargs,
        )

        if use_cache and CACHE_ENABLED and semantic_cache and response:
            semantic_cache.set(prompt, response, system_prompt, model_key)

        return response

    async def _call_provider(
        self,
        provider,
        model_name,
        local_url,
        api_key_input,
        system_prompt,
        user_prompt,
        **kwargs,
    ):
        """Unified async LLM call - delegates to providers module."""
        return await self._providers.call(
            provider,
            model_name,
            local_url,
            api_key_input,
            system_prompt,
            user_prompt,
            **kwargs,
        )

    async def list_models(
        self,
        provider="Local (LM Studio)",
        local_url="http://127.0.0.1:1234/v1",
        api_key_input=None,
    ) -> list[str]:
        """List available models from the provider."""
        return await self._providers.list_models(provider, local_url, api_key_input)

    # ==========================================
    # High-Level Analysis Tasks
    # ==========================================
    async def analyze_file(
        self,
        file_path,
        user_instruction,
        provider=None,
        model_name=None,
        local_url=None,
        start_page=1,
        end_page=None,
        **kwargs,
    ):
        content = await document_service.extract_text(file_path, start_page, end_page)
        return await self.analyze_text(
            content, user_instruction, provider, model_name, local_url, **kwargs
        )

    async def analyze_text(
        self,
        text_content: str | None = None,
        user_instruction: str = "",
        provider=None,
        model_name=None,
        local_url=None,
        financial_skepticism=False,
        role=None,
        api_key=None,
        **kwargs,
    ):
        import os

        # Backward compatibility for 'text' parameter
        if text_content is None:
            text_content = kwargs.get("text", "")

        if not provider:
            config = self.get_routing_config("smart")
            provider = config["provider"]
            model_name = config["model_name"]
            local_url = config.get("local_url")

        context_window = kwargs.get("context_window", 32000)
        reserved_tokens = 2000
        available_tokens = max(context_window - reserved_tokens, 1000)
        max_chars = int(available_tokens * 1.5)

        file_name = "text_input"
        truncated = False

        if len(text_content) > max_chars:
            truncated = True
            text_content = (
                text_content[:max_chars]
                + f"\n\n...(內容已截斷至 {max_chars} 字元以符合模型限制)..."
            )

        system_prompt, user_prompt = self.build_analysis_prompts(
            user_instruction=user_instruction,
            file_name=file_name,
            content=text_content,
            financial_skepticism=financial_skepticism,
        )

        api_key_input = api_key or self.api_key

        return await self._call_provider(
            provider,
            model_name,
            local_url,
            api_key_input,
            system_prompt,
            user_prompt,
            **kwargs,
        )

    async def translate_text(
        self,
        text,
        target_language="英文",
        provider=None,
        model_name=None,
        local_url=None,
        **kwargs,
    ):
        if not provider:
            config = self.get_routing_config("fast")
            provider = config["provider"]
            model_name = config["model_name"]
            local_url = config.get("local_url")

        system_prompt = f"你是一位專業翻譯員。請將以下文字翻譯成{target_language}，保持原文的語氣和格式。"
        user_prompt = text

        return await self._call_provider(
            provider,
            model_name,
            local_url,
            self.api_key,
            system_prompt,
            user_prompt,
            **kwargs,
        )

    async def summarize_text(
        self,
        text,
        max_length=500,
        provider=None,
        model_name=None,
        local_url=None,
        **kwargs,
    ):
        if not provider:
            config = self.get_routing_config("fast")
            provider = config["provider"]
            model_name = config["model_name"]
            local_url = config.get("local_url")

        system_prompt = (
            f"你是一位專業摘要員。請將以下文字摘要成不超過{max_length}字的精簡版本。"
        )
        user_prompt = text

        return await self._call_provider(
            provider,
            model_name,
            local_url,
            self.api_key,
            system_prompt,
            user_prompt,
            **kwargs,
        )

    async def extract_info(
        self,
        text,
        extraction_type="日期、人名、金額",
        provider=None,
        model_name=None,
        local_url=None,
        **kwargs,
    ):
        if not provider:
            config = self.get_routing_config("fast")
            provider = config["provider"]
            model_name = config["model_name"]
            local_url = config.get("local_url")

        system_prompt = f"你是一位資訊萃取專家。請從以下文字中萃取{extraction_type}，以結構化格式輸出。"
        user_prompt = text

        return await self._call_provider(
            provider,
            model_name,
            local_url,
            self.api_key,
            system_prompt,
            user_prompt,
            **kwargs,
        )

    async def extract_entities(
        self,
        text,
        entity_types=None,
        provider=None,
        model_name=None,
        local_url=None,
        **kwargs,
    ):
        if entity_types is None:
            entity_types = ["人名", "組織", "地點", "日期", "金額"]

        if not provider:
            config = self.get_routing_config("fast")
            provider = config["provider"]
            model_name = config["model_name"]
            local_url = config.get("local_url")

        system_prompt = f"""你是一位命名實體識別專家。請從文字中識別並標註以下類型的實體：{", ".join(entity_types)}。
請務必以 JSON 格式輸出，結構必須包含 'entities' 陣列與 'relations' 陣列：
{{
    "entities": [
        {{"name": "實體名稱", "type": "實體類型", "description": "描述"}}
    ],
    "relations": [
        {{"subject": "主體", "object": "受體", "relation": "關係"}}
    ]
}}
如果沒有找到，請回傳空的陣列。不要輸出任何其他說明文字。"""
        user_prompt = text

        response = await self._call_provider(
            provider,
            model_name,
            local_url,
            self.api_key,
            system_prompt,
            user_prompt,
            **kwargs,
        )

        import json
        import re

        try:
            if "```json" in response:
                match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
                if match:
                    response = match.group(1)
            elif "```" in response:
                match = re.search(r"```\s*(.*?)\s*```", response, re.DOTALL)
                if match:
                    response = match.group(1)

            # Remove any leading text that isn't part of JSON
            response = response.strip()
            if not response.startswith("{"):
                match = re.search(r"\{.*\}", response, re.DOTALL)
                if match:
                    response = match.group(0)

            return json.loads(response)
        except Exception as e:
            logger.warning("Failed to parse extract_entities JSON", error=str(e))
            return {"entities": [], "relations": []}

    # ==========================================
    # Report Generation
    # ==========================================
    async def generate_report(
        self,
        content,
        report_type="分析報告",
        provider=None,
        model_name=None,
        local_url=None,
        **kwargs,
    ):
        if not provider:
            config = self.get_routing_config("smart")
            provider = config["provider"]
            model_name = config["model_name"]
            local_url = config.get("local_url")

        system_prompt = f"你是一位專業報告撰寫員。請根據以下內容生成一份{report_type}，使用 Markdown 格式。"
        user_prompt = content

        return await self._call_provider(
            provider,
            model_name,
            local_url,
            self.api_key,
            system_prompt,
            user_prompt,
            **kwargs,
        )

    async def generate_chart(
        self,
        data_description,
        chart_type=None,
        provider=None,
        model_name=None,
        local_url=None,
        **kwargs,
    ):
        if not provider:
            config = self.get_routing_config("fast")
            provider = config["provider"]
            model_name = config["model_name"]
            local_url = config.get("local_url")

        system_prompt = (
            "你是一位數據視覺化專家。請根據數據描述，生成適合的圖表配置（JSON格式）。"
        )
        user_prompt = f"數據描述：{data_description}"
        if chart_type:
            user_prompt += f"\n建議圖表類型：{chart_type}"

        return await self._call_provider(
            provider,
            model_name,
            local_url,
            self.api_key,
            system_prompt,
            user_prompt,
            **kwargs,
        )

    async def generate_pandas_query(
        self,
        question: str,
        df_info: dict,
        provider=None,
        model_name=None,
        local_url=None,
        **kwargs,
    ):
        if not provider:
            config = self.get_routing_config("fast")
            provider = config["provider"]
            model_name = config["model_name"]
            local_url = config.get("local_url")

        system_prompt = """你是一位 Pandas 資料分析專家。請根據使用者的問題和資料資訊，生成正確的 Pandas 程式碼。
輸出格式：
1. 只輸出可執行的 Python 程式碼
2. 不要包含解釋或註解
3. 結果必須賦值給變數 `result`"""

        user_prompt = f"""問題：{question}

資料資訊：
- 欄位：{df_info.get("columns", [])}
- 資料筆數：{df_info.get("shape", ["未知"])[0]}
- 欄位類型：{df_info.get("dtypes", {})}

請生成 Pandas 程式碼："""

        return await self._call_provider(
            provider,
            model_name,
            local_url,
            self.api_key,
            system_prompt,
            user_prompt,
            **kwargs,
        )

    # ==========================================
    # RAG Integration
    # ==========================================
    async def rag_answer(
        self,
        question: str,
        context: str,
        provider=None,
        model_name=None,
        local_url=None,
        api_key=None,
        **kwargs,
    ):
        if not provider:
            config = self.get_routing_config("smart")
            provider = config["provider"]
            model_name = config["model_name"]
            local_url = config.get("local_url")

        api_key_input = api_key or self.api_key

        system_prompt = """你是一位專業的文件分析助手。請根據提供的上下文內容回答問題。

**核心規則：**
1. **直接回答**：直接開始回答內容，絕對禁止重複列出使用者的指令內容、限制條件或數據塊清單（例如禁止出現 "Task:", "Chunk 1:", "Constraint:" 等字眼）。
2. **格式優雅**：請務必使用 Markdown 格式，適當使用 `###` 標題、粗體與列表來增加可讀性，嚴禁輸出一整塊密集的文字。
3. **忠於真實**：只使用上下文中的資訊回答。如果上下文中沒有相關資訊，請明確告知。
4. **標註來源**：引用具體數據或論點時，請簡要標註來源，如 `[資料來源1]`。
5. **禁止思考內容**：不要在回覆中加入 `<thought>` 標記、思考過程或任何非最終答案的訊息。"""

        user_prompt = f"""請精簡、專業地摘要或回答以下問題：

【上下文內容】：
{context}

【使用者問題】：{question}

請直接開始您的專業回答："""

        return await self._call_provider(
            provider,
            model_name,
            local_url,
            api_key_input,
            system_prompt,
            user_prompt,
            **kwargs,
        )

    async def rag_answer_stream(
        self,
        question: str,
        context: str,
        provider=None,
        model_name=None,
        local_url=None,
        api_key=None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Streaming version of RAG answer."""
        if not provider:
            config = self.get_routing_config("smart")
            provider = config["provider"]
            model_name = config["model_name"]
            local_url = config.get("local_url")

        api_key_input = api_key or self.api_key

        system_prompt = """你是一位專業的文件分析助手。請根據提供的上下文內容回答問題。

**核心規則：**
1. **直接回答**：直接開始回答內容，絕對禁止重複列出使用者的指令內容、限制條件或數據塊清單（例如禁止出現 "Task:", "Chunk 1:", "Constraint:" 等字眼）。
2. **格式優雅**：請務必使用 Markdown 格式，適當使用 `###` 標題、粗體與列表來增加可讀性，嚴禁輸出一整塊密集的文字。
3. **忠於真實**：只使用上下文中的資訊回答。如果上下文中沒有相關資訊，請明確告知。
4. **標註來源**：引用具體數據或論點時，請簡要標註來源。
5. **禁止思考內容**：不要在回覆中加入思考過程或任何非最終答案的訊息。"""

        user_prompt = f"""請精簡、專業地摘要或回答以下問題：

【上下文內容】：
{context}

【使用者問題】：{question}

請直接開始您的專業回答："""

        async for chunk in self._providers.stream_call(
            provider,
            model_name,
            local_url,
            api_key_input,
            system_prompt,
            user_prompt,
            **kwargs,
        ):
            yield chunk

    # ==========================================
    # Excel AI Tasks
    # ==========================================
    async def ai_detect_table_range(self, content, provider, model, url, **kwargs):
        system_prompt = "你是 Excel 表格分析專家。請分析內容並偵測表格範圍。"
        return await self._call_provider(
            provider, model, url, self.api_key, system_prompt, str(content), **kwargs
        )

    async def ai_find_semantic_keywords(self, content, provider, model, url, **kwargs):
        system_prompt = "你是語意分析專家。請從內容中找出關鍵詞。"
        return await self._call_provider(
            provider, model, url, self.api_key, system_prompt, str(content), **kwargs
        )

    async def ai_infer_formula_structure(self, content, provider, model, url, **kwargs):
        system_prompt = "你是 Excel 公式推論專家。請推論公式結構。"
        return await self._call_provider(
            provider, model, url, self.api_key, system_prompt, str(content), **kwargs
        )

    async def ai_match_template(self, content, provider, model, url, **kwargs):
        system_prompt = "你是文件模板比對專家。請比對並匹配模板。"
        return await self._call_provider(
            provider, model, url, self.api_key, system_prompt, str(content), **kwargs
        )

    async def ai_diagnose_validation_errors(
        self, content, provider, model, url, **kwargs
    ):
        system_prompt = "你是資料驗證診斷專家。請診斷驗證錯誤原因。"
        return await self._call_provider(
            provider, model, url, self.api_key, system_prompt, str(content), **kwargs
        )


# Singleton instance
llm_service = LLMService()
