"""
LLM Service Package
Refactored from monolithic llm_service.py into modular components.

匯出採延遲載入（PEP 562）：`app.services.llm.service` 會拉起
google-generativeai、python-docx 等重量級依賴。若在這裡 eager import，
任何 `import app.services.llm.stream_filter` 之類的動作都會被迫載入整套
LLM 堆疊（也會讓純函式模組難以單元測試）。

`from app.services.llm import LLMService` 仍然照常運作。
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - 只給型別檢查器用
    from app.services.llm.service import LLMService, llm_service

__all__ = ["LLMService", "llm_service"]


def __getattr__(name: str) -> Any:
    if name in __all__:
        from app.services.llm import service as _service

        return getattr(_service, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
