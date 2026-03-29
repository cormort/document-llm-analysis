"""
LangExtract Service
結構化資料提取服務，支援精確來源標記和互動視覺化。
整合 Google LangExtract 函式庫。
"""

import os
import textwrap
from typing import Any

import structlog

logger = structlog.get_logger()


# 預設提取範本
EXTRACTION_TEMPLATES: dict[str, dict[str, Any]] = {
    "key_facts": {
        "prompt": textwrap.dedent("""\
            從文件中提取關鍵事實和數據點。
            - 按照重要性順序排列
            - 使用原文進行提取，不要改寫
            - 為每個事實提供相關屬性（類型、數值、日期等）
        """),
        "classes": ["fact", "statistic", "date", "amount"],
    },
    "entities": {
        "prompt": textwrap.dedent("""\
            從文件中提取命名實體及其關係。
            - 識別人名、公司、地點、產品、事件
            - 標記實體之間的關係
            - 使用原文進行提取
        """),
        "classes": ["person", "organization", "location", "product", "event"],
    },
    "financial": {
        "prompt": textwrap.dedent("""\
            從文件中提取財務相關資訊。
            - 營收、利潤、成本、資產負債
            - 包含時間範圍和幣值單位
            - 標記同比/環比變化
        """),
        "classes": ["revenue", "profit", "cost", "change", "forecast"],
    },
    "contract": {
        "prompt": textwrap.dedent("""\
            從合約文件中提取重要條款。
            - 權利義務、付款條件、期限
            - 違約責任、保密條款
            - 標記條款的約束對象
        """),
        "classes": ["obligation", "right", "deadline", "payment", "penalty"],
    },
}


class LangExtractService:
    """LangExtract 結構化提取服務。

    支援多種 LLM 提供者：
    - Gemini (Google)
    - OpenAI
    - Local LLM via Ollama/LM Studio (OpenAI-compatible)
    """

    def __init__(self) -> None:
        """初始化服務。"""
        self._lx = None
        self._available = False
        self._init_langextract()

    def _init_langextract(self) -> None:
        """延遲載入 langextract 模組。"""
        try:
            import langextract as lx

            self._lx = lx
            self._available = True
            logger.info("LangExtract 模組載入成功", version=getattr(lx, "__version__", "unknown"))
        except ImportError as e:
            logger.warning("LangExtract 模組未安裝", error=str(e))
            self._available = False

    @property
    def is_available(self) -> bool:
        """檢查 langextract 是否可用。"""
        return self._available

    def get_templates(self) -> dict[str, dict[str, Any]]:
        """取得可用的提取範本。"""
        return EXTRACTION_TEMPLATES

    async def extract(
        self,
        text: str,
        extraction_type: str = "key_facts",
        provider: str = "Local (LM Studio)",
        model_name: str | None = None,
        local_url: str = "http://127.0.0.1:1234/v1",
        api_key: str | None = None,
        custom_prompt: str | None = None,
        custom_classes: list[str] | None = None,
    ) -> dict[str, Any]:
        """執行結構化資料提取。

        Args:
            text: 要提取的原始文字
            extraction_type: 提取類型 (key_facts, entities, financial, contract)
            provider: LLM 提供者
            model_name: 模型名稱
            local_url: 本地 LLM 端點
            api_key: API 金鑰 (Gemini / OpenAI)
            custom_prompt: 自訂提取提示
            custom_classes: 自訂提取類別

        Returns:
            dict: 包含 extractions, html_visualization, source_file 的結果
        """
        if not self._available:
            return {
                "success": False,
                "error": "LangExtract 未安裝。請執行: pip install langextract",
                "extractions": [],
            }

        if not text or not text.strip():
            return {
                "success": False,
                "error": "輸入文字為空",
                "extractions": [],
            }

        lx = self._lx

        # 選擇範本或使用自訂設定
        template = EXTRACTION_TEMPLATES.get(extraction_type, EXTRACTION_TEMPLATES["key_facts"])
        prompt = custom_prompt if custom_prompt else template["prompt"]
        classes = custom_classes if custom_classes else template["classes"]

        # 建立範例
        examples = self._build_examples(classes)

        # 決定模型設定
        model_id, model_url, fence_output, use_schema = self._resolve_model_config(
            provider, model_name, local_url, api_key
        )

        try:
            logger.info(
                "LangExtract 開始提取",
                provider=provider,
                model_id=model_id,
                extraction_type=extraction_type,
                text_length=len(text),
            )

            # 執行提取
            extract_kwargs: dict[str, Any] = {
                "text_or_documents": text,
                "prompt_description": prompt,
                "examples": examples,
                "model_id": model_id,
                "fence_output": fence_output,
                "use_schema_constraints": use_schema,
            }

            # 設定 API Key 或 model_url
            if model_url:
                extract_kwargs["model_url"] = model_url
            if api_key and provider in ["OpenAI", "Gemini"]:
                extract_kwargs["api_key"] = api_key

            result = lx.extract(**extract_kwargs)

            # 轉換結果
            extractions = self._format_extractions(result)

            # 產生互動視覺化 HTML
            html_content = self._generate_visualization(lx, result, text)

            return {
                "success": True,
                "extractions": extractions,
                "html_visualization": html_content,
                "total_count": len(extractions),
                "classes_found": list({e.get("class") for e in extractions if e.get("class")}),
            }

        except Exception as e:
            logger.error("LangExtract 提取失敗", error=str(e), exc_info=True)
            return {
                "success": False,
                "error": f"提取失敗: {e}",
                "extractions": [],
            }

    def _resolve_model_config(
        self,
        provider: str,
        model_name: str | None,
        local_url: str,
        api_key: str | None,
    ) -> tuple[str, str | None, bool, bool]:
        """解析模型配置。

        Returns:
            tuple: (model_id, model_url, fence_output, use_schema_constraints)
        """
        # Gemini 模型
        if provider == "Gemini" or (api_key and "gemini" in (model_name or "").lower()):
            model_id = model_name or "gemini-2.5-flash"
            return model_id, None, False, True  # Gemini 支援 schema constraints

        # OpenAI 模型
        if provider == "OpenAI":
            model_id = model_name or "gpt-4o"
            return model_id, None, True, False  # OpenAI 需要 fence_output

        # 本地 LLM (LM Studio / Ollama / etc.)
        # 使用 OpenAI-compatible 端點，但需要 fence_output
        if any(p in provider for p in ["Local", "LM Studio", "Ollama", "Osaurus", "Exo"]):
            model_id = model_name or "qwen2.5:7b"
            # 本地 LLM 通常使用 Ollama 端點格式
            model_url = local_url.replace("/v1", "").rstrip("/")
            if "11434" not in model_url and "1234" in model_url:
                # LM Studio 端點，嘗試轉換為 Ollama 格式
                model_url = "http://localhost:11434"
            return model_id, model_url, True, False

        # 預設使用 Gemini
        return "gemini-2.5-flash", None, False, True

    def _build_examples(self, classes: list[str]) -> list[Any]:
        """建立提取範例。"""
        if not self._lx:
            return []

        lx = self._lx

        # 建立通用範例（可根據 classes 客製化）
        example_text = "本季度營收達到 520 億美元，較去年同期成長 15%。"
        example_extractions = [
            lx.data.Extraction(
                extraction_class="revenue" if "revenue" in classes else classes[0],
                extraction_text="520 億美元",
                attributes={"period": "本季度", "currency": "美元"},
            ),
            lx.data.Extraction(
                extraction_class="change" if "change" in classes else classes[-1],
                extraction_text="較去年同期成長 15%",
                attributes={"type": "year_over_year", "direction": "growth"},
            ),
        ]

        return [
            lx.data.ExampleData(
                text=example_text,
                extractions=example_extractions[:len(classes)],  # 限制範例數量
            )
        ]

    def _format_extractions(self, result: Any) -> list[dict[str, Any]]:
        """格式化提取結果。"""
        extractions = []

        if hasattr(result, "extractions"):
            for ext in result.extractions:
                extractions.append(
                    {
                        "class": getattr(ext, "extraction_class", None),
                        "text": getattr(ext, "extraction_text", None),
                        "attributes": getattr(ext, "attributes", {}),
                        "start_offset": getattr(ext, "start_offset", None),
                        "end_offset": getattr(ext, "end_offset", None),
                    }
                )
        elif isinstance(result, list):
            for item in result:
                if hasattr(item, "extractions"):
                    for ext in item.extractions:
                        extractions.append(
                            {
                                "class": getattr(ext, "extraction_class", None),
                                "text": getattr(ext, "extraction_text", None),
                                "attributes": getattr(ext, "attributes", {}),
                                "start_offset": getattr(ext, "start_offset", None),
                                "end_offset": getattr(ext, "end_offset", None),
                            }
                        )

        return extractions

    def _generate_visualization(self, lx: Any, result: Any, original_text: str) -> str:
        """產生互動視覺化 HTML。"""
        try:
            # 嘗試使用 langextract 的視覺化功能
            if hasattr(lx, "visualize"):
                # 先儲存到臨時檔案
                import tempfile

                with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
                    temp_path = f.name
                    if hasattr(result, "extractions"):
                        lx.io.save_annotated_documents([result], output_name=os.path.basename(temp_path), output_dir=os.path.dirname(temp_path))

                    # 產生 HTML
                    html_content = lx.visualize(temp_path)

                    # 清理臨時檔案
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass

                    if hasattr(html_content, "data"):
                        return html_content.data
                    return str(html_content)

        except Exception as e:
            logger.warning("視覺化產生失敗，使用備用格式", error=str(e))

        # 備用：產生簡單 HTML
        return self._generate_fallback_html(result, original_text)

    def _generate_fallback_html(self, result: Any, original_text: str) -> str:
        """產生備用 HTML 視覺化。"""
        extractions = self._format_extractions(result)

        html_parts = [
            "<!DOCTYPE html>",
            "<html><head><meta charset='utf-8'>",
            "<title>LangExtract 提取結果</title>",
            "<style>",
            "body { font-family: 'Segoe UI', sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }",
            ".container { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }",
            ".panel { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }",
            ".extraction { padding: 10px; margin: 5px 0; border-radius: 4px; border-left: 4px solid; }",
            ".extraction:hover { background: #f0f0f0; }",
            ".class-revenue, .class-fact { border-color: #4CAF50; background: #E8F5E9; }",
            ".class-change, .class-statistic { border-color: #2196F3; background: #E3F2FD; }",
            ".class-date { border-color: #FF9800; background: #FFF3E0; }",
            ".class-amount, .class-cost { border-color: #9C27B0; background: #F3E5F5; }",
            ".class-person { border-color: #E91E63; background: #FCE4EC; }",
            ".class-organization { border-color: #00BCD4; background: #E0F2F1; }",
            ".text { font-weight: 500; }",
            ".attrs { font-size: 0.85em; color: #666; margin-top: 5px; }",
            "h2 { color: #333; border-bottom: 2px solid #ddd; padding-bottom: 10px; }",
            ".source { white-space: pre-wrap; font-family: monospace; font-size: 0.9em; line-height: 1.6; }",
            "mark { background: #FFEB3B; padding: 2px 4px; border-radius: 2px; }",
            "</style></head><body>",
            "<h1>🎯 LangExtract 提取結果</h1>",
            f"<p>共提取 <strong>{len(extractions)}</strong> 個項目</p>",
            "<div class='container'>",
            "<div class='panel'><h2>📋 提取項目</h2>",
        ]

        for ext in extractions:
            cls = ext.get("class", "unknown")
            text = ext.get("text", "")
            attrs = ext.get("attributes", {})
            attrs_str = ", ".join(f"{k}: {v}" for k, v in attrs.items()) if attrs else ""

            html_parts.append(
                f"<div class='extraction class-{cls}'>"
                f"<span class='badge'>{cls}</span> "
                f"<span class='text'>{text}</span>"
                + (f"<div class='attrs'>{attrs_str}</div>" if attrs_str else "")
                + "</div>"
            )

        # 標記原文中的提取項目
        highlighted_text = original_text
        for ext in sorted(extractions, key=lambda x: len(x.get("text", "")), reverse=True):
            text = ext.get("text", "")
            if text and text in highlighted_text:
                highlighted_text = highlighted_text.replace(text, f"<mark>{text}</mark>", 1)

        html_parts.extend(
            [
                "</div>",
                "<div class='panel'><h2>📄 原文標記</h2>",
                f"<div class='source'>{highlighted_text[:3000]}{'...' if len(highlighted_text) > 3000 else ''}</div>",
                "</div></div>",
                "</body></html>",
            ]
        )

        return "\n".join(html_parts)


# Singleton
langextract_service = LangExtractService()
