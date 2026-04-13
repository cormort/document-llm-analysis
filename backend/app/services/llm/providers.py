"""
LLM Provider Implementations
Unified interface for Gemini, OpenAI, and Local LLM providers.
"""

import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
from typing import AsyncGenerator

import google.generativeai as genai
import requests
import structlog
from app.core.metrics import LLM_TOKEN_USAGE_TOTAL

logger = structlog.get_logger()


class LLMProviders:
    """Handles all LLM provider communications."""

    def __init__(
        self, executor: ThreadPoolExecutor, default_api_key: str | None = None
    ):
        self._executor = executor
        self._default_api_key = default_api_key

    async def run_sync(self, func, *args, **kwargs):
        """Run sync function in thread pool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, lambda: func(*args, **kwargs))

    async def call(
        self,
        provider: str,
        model_name: str,
        local_url: str | None,
        api_key_input: str | None,
        system_prompt: str,
        user_prompt: str,
        **kwargs,
    ) -> str:
        """Unified async LLM call."""
        logger.info("LLM Request", provider=provider, model=model_name)

        if provider == "Gemini":
            return await self._call_gemini(
                model_name, api_key_input, system_prompt, user_prompt
            )

        result = await self.run_sync(
            self._call_sync,
            provider,
            model_name,
            local_url,
            api_key_input,
            system_prompt,
            user_prompt,
            **kwargs,
        )
        logger.info(
            "LLM Response Received",
            length=len(result) if result else 0,
            result_preview=result[:100] if result else "None",
        )
        return result

    async def stream_call(
        self,
        provider: str,
        model_name: str,
        local_url: str | None,
        api_key_input: str | None,
        system_prompt: str,
        user_prompt: str,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Unified async LLM streaming call."""
        logger.info("LLM Streaming Request", provider=provider, model=model_name)

        if provider == "Gemini":
            async for chunk in self._stream_gemini(
                model_name, api_key_input, system_prompt, user_prompt
            ):
                yield chunk
            return

        # For OpenAI-compatible providers
        async for chunk in self._stream_openai_compatible(
            provider, model_name, local_url, api_key_input, system_prompt, user_prompt, **kwargs
        ):
            yield chunk

    async def _call_gemini(
        self,
        model_name: str,
        api_key_input: str | None,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Native async Gemini call."""
        if not api_key_input:
            api_key_input = self._default_api_key
        if not api_key_input:
            return "⚠️ 未設定 Google API Key"

        try:
            genai.configure(api_key=api_key_input)

            clean_model_name = model_name
            if clean_model_name and clean_model_name.startswith("models/"):
                clean_model_name = clean_model_name.replace("models/", "")

            logger.info("Gemini Model Init", model=clean_model_name)
            model = genai.GenerativeModel(
                clean_model_name, system_instruction=system_prompt
            )

            logger.info("Gemini Generating...", input_len=len(user_prompt))
            response = await model.generate_content_async(user_prompt)
            logger.info("Gemini Response Recv")

            if not response.candidates:
                return "Gemini Error: No candidates returned."

            if hasattr(response, "usage_metadata") and response.usage_metadata:
                tokens = getattr(response.usage_metadata, "total_token_count", 0)
                if tokens > 0:
                    LLM_TOKEN_USAGE_TOTAL.labels(
                        provider="Gemini", model=clean_model_name
                    ).inc(tokens)

            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                return response.text

            if candidate.finish_reason == 1:
                return ""

            return f"Gemini Error: Finish Reason {candidate.finish_reason}"

        except Exception as e:
            logger.error("Gemini Error", error=str(e), traceback=True)
            return f"Gemini Error: {e}"

    def _call_sync(
        self,
        provider: str,
        model_name: str,
        local_url: str | None,
        api_key_input: str | None,
        system_prompt: str,
        user_prompt: str,
        **kwargs,
    ) -> str:
        """Sync implementation for requests-based providers."""
        if provider == "OpenAI":
            return self._call_openai(
                model_name, api_key_input, system_prompt, user_prompt, **kwargs
            )

        if any(
            p in provider
            for p in ["Local", "LM Studio", "Osaurus", "Ollama", "Exo", "omlx"]
        ):
            return self._call_local(
                provider,
                model_name,
                local_url,
                api_key_input,
                system_prompt,
                user_prompt,
                **kwargs,
            )

        return f"Unknown Provider: {provider}"

    def _call_openai(
        self,
        model_name: str,
        api_key_input: str | None,
        system_prompt: str,
        user_prompt: str,
        **kwargs,
    ) -> str:
        """OpenAI API call."""
        if not api_key_input:
            return "⚠️ 未設定 OpenAI API Key"

        endpoint = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key_input}",
        }
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": kwargs.get("temperature", 0.3),
        }

        try:
            response = requests.post(
                endpoint, headers=headers, json=payload, timeout=60
            )
            response.raise_for_status()
            data = response.json()
            usage = data.get("usage", {})
            tokens = usage.get("total_tokens", 0)
            if tokens > 0:
                LLM_TOKEN_USAGE_TOTAL.labels(provider="OpenAI", model=model_name).inc(
                    tokens
                )
            content = data["choices"][0]["message"]["content"]
            # If content is a list of parts, filter out thinking and concatenate text.
            if isinstance(content, list):
                text_parts = []
                for part in content:
                    if isinstance(part, dict):
                        if part.get("type") == "thinking":
                            continue
                        text_parts.append(part.get("text", ""))
                    else:
                        text_parts.append(str(part))
                content = "".join(text_parts)
            return content
        except Exception as e:
            return f"OpenAI Error: {e}"

    def _call_local(
        self,
        provider: str,
        model_name: str,
        local_url: str | None,
        api_key_input: str | None,
        system_prompt: str,
        user_prompt: str,
        **kwargs,
    ) -> str:
        """Local LLM API call (OpenAI-compatible)."""
        # Normalize provider name to handle case/whitespace variations
        normalized_provider = provider.strip().lower()
        base_url = (local_url or "").rstrip("/")
        endpoint = f"{base_url}/chat/completions"

        headers = {"Content-Type": "application/json", "Connection": "close"}

        effective_key = api_key_input
        # omlx: always prefer env-configured key (frontend may send stale cloud keys)
        if normalized_provider == "omlx":
            from app.core.config import settings as cfg

            effective_key = cfg.OMLX_API_KEY or api_key_input or None

        # omlx requires API key authentication
        if normalized_provider == "omlx" and effective_key:
            headers["Authorization"] = f"Bearer {effective_key}"
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": kwargs.get("temperature", 0.7),
        }

        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                logger.info(
                    "Local LLM Request",
                    attempt=attempt + 1,
                    provider=provider,
                    model=model_name,
                    endpoint=endpoint,
                )
                response = requests.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=kwargs.get("timeout", 900),
                )
                response.raise_for_status()
                data = response.json()
                usage = data.get("usage", {})
                tokens = usage.get("total_tokens", 0)
                if tokens > 0:
                    LLM_TOKEN_USAGE_TOTAL.labels(
                        provider=provider, model=model_name
                    ).inc(tokens)
                content = data["choices"][0]["message"]["content"]
                # If content is a list of parts, filter out thinking and concatenate text.
                if isinstance(content, list):
                    text_parts = []
                    for part in content:
                        if isinstance(part, dict):
                            if part.get("type") == "thinking":
                                continue
                            text_parts.append(part.get("text", ""))
                        else:
                            text_parts.append(str(part))
                    content = "".join(text_parts)
                return content
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.ChunkedEncodingError,
            ) as e:
                last_error = e
                logger.warn(
                    "Local LLM Connection Abandoned, Retrying...",
                    attempt=attempt + 1,
                    error=str(e),
                )
                time.sleep(1)
            except requests.exceptions.HTTPError as e:
                return f"{provider} HTTP Error: {e} - Details: {response.text}"
            except Exception as e:
                return f"{provider} Unexpected Error: {e}"

        return (
            f"{provider} Error: Connection failed after {max_retries} attempts. "
            f"Last error: {last_error}"
        )

    async def list_models(
        self,
        provider: str = "Local (LM Studio)",
        local_url: str = "http://127.0.0.1:1234/v1",
        api_key_input: str | None = None,
    ) -> list[str]:
        """List available models from the provider."""
        return await self.run_sync(
            self._list_models_sync, provider, local_url, api_key_input
        )

    def _list_models_sync(
        self,
        provider: str,
        local_url: str,
        api_key_input: str | None,
    ) -> list[str]:
        """Sync implementation to list models."""
        if provider == "Gemini":
            return self._list_gemini_models(api_key_input)

        if any(
            p in provider
            for p in [
                "Local",
                "LM Studio",
                "Osaurus",
                "Ollama",
                "Exo",
                "OpenAI",
                "omlx",
            ]
        ):
            return self._list_openai_compatible_models(
                provider, local_url, api_key_input
            )

        return []

    async def _stream_gemini(
        self,
        model_name: str,
        api_key_input: str | None,
        system_prompt: str,
        user_prompt: str,
    ) -> AsyncGenerator[str, None]:
        """Native async Gemini streaming call."""
        if not api_key_input:
            api_key_input = self._default_api_key
        if not api_key_input:
            yield "⚠️ 未設定 Google API Key"
            return

        try:
            genai.configure(api_key=api_key_input)
            clean_model_name = model_name
            if clean_model_name and clean_model_name.startswith("models/"):
                clean_model_name = clean_model_name.replace("models/", "")

            model = genai.GenerativeModel(
                clean_model_name, system_instruction=system_prompt
            )
            response = await model.generate_content_async(user_prompt, stream=True)
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            logger.error("Gemini Streaming Error", error=str(e))
            yield f"Gemini Error: {e}"

    async def _stream_openai_compatible(
        self,
        provider: str,
        model_name: str,
        local_url: str | None,
        api_key_input: str | None,
        system_prompt: str,
        user_prompt: str,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Streaming implementation for OpenAI-compatible providers."""
        normalized_provider = provider.strip().lower()
        base_url = (local_url or "").rstrip("/")
        endpoint = f"{base_url}/chat/completions"

        headers = {"Content-Type": "application/json"}
        effective_key = api_key_input
        if normalized_provider == "omlx":
            from app.core.config import settings as cfg
            effective_key = cfg.OMLX_API_KEY or api_key_input or None
        
        if effective_key:
            headers["Authorization"] = f"Bearer {effective_key}"

        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": kwargs.get("temperature", 0.7),
            "stream": True
        }

        try:
            # We use a non-blocking way to call requests.post with stream=True
            # For brevity, using run_sync to wrap the generator source
            response = await self.run_sync(
                requests.post,
                endpoint,
                headers=headers,
                json=payload,
                stream=True,
                timeout=kwargs.get("timeout", 900)
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    line_str = line.decode("utf-8")
                    if line_str.startswith("data: "):
                        data_str = line_str[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            content = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if content:
                                yield content
                        except Exception:
                            continue
        except Exception as e:
            logger.error(f"{provider} Streaming Error", error=str(e))
            yield f"{provider} Error: {e}"

    def _list_gemini_models(self, api_key_input: str | None) -> list[str]:
        """List Gemini models."""
        if not api_key_input:
            api_key_input = self._default_api_key
        if not api_key_input:
            return ["⚠️ 未設定 API Key"]

        try:
            genai.configure(api_key=api_key_input)
            models = genai.list_models()
            return [
                m.name.replace("models/", "")
                for m in models
                if "generateContent" in m.supported_generation_methods
            ]
        except Exception as e:
            logger.error("Gemini List Models Error", error=str(e))
            return []

    def _list_openai_compatible_models(
        self,
        provider: str,
        local_url: str,
        api_key_input: str | None,
    ) -> list[str]:
        """List models from OpenAI-compatible endpoints."""
        if provider == "OpenAI":
            base_url = "https://api.openai.com/v1"
            headers = {"Authorization": f"Bearer {api_key_input}"}
        else:
            base_url = local_url.rstrip("/")
            headers = {}

            effective_key = api_key_input
            if provider == "omlx":
                from app.core.config import settings as cfg

                effective_key = cfg.OMLX_API_KEY or api_key_input or None

            # omlx requires API key authentication
            if provider == "omlx" and effective_key:
                headers["Authorization"] = f"Bearer {effective_key}"

        endpoint = f"{base_url}/models"
        try:
            logger.info("Fetching Models", endpoint=endpoint)
            response = requests.get(endpoint, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            return [model["id"] for model in data.get("data", [])]
        except Exception as e:
            logger.error("List Models Error", provider=provider, error=str(e))
            return []
