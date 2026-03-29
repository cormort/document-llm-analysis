"""統一例外處理模組。

提供 AppException 基礎類別及全域 exception handler 註冊函式，
確保所有 API 回傳一致的錯誤回應格式。
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """應用程式統一例外類別。

    Args:
        code: 機器可讀的錯誤代碼（如 FILE_TOO_LARGE）。
        message: 人類可讀的錯誤訊息。
        status_code: HTTP 狀態碼，預設 400。
        detail: 額外錯誤細節。
    """

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(message)


class FileValidationError(AppError):
    """檔案驗證失敗。"""

    def __init__(self, message: str, detail: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="FILE_VALIDATION_ERROR",
            message=message,
            status_code=422,
            detail=detail,
        )


class RateLimitExceededError(AppError):
    """請求頻率超過限制。"""

    def __init__(self) -> None:
        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            message="請求頻率過高，請稍後再試。",
            status_code=429,
        )


def register_exception_handlers(app: FastAPI) -> None:
    """註冊全域例外處理器到 FastAPI app。"""

    @app.exception_handler(AppError)
    async def app_exception_handler(
        request: Request, exc: AppError
    ) -> JSONResponse:
        logger.warning(
            "AppException: code=%s message=%s path=%s",
            exc.code,
            exc.message,
            request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "detail": exc.detail,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception(
            "Unhandled exception: path=%s", request.url.path
        )
        return JSONResponse(
            status_code=500,
            content={
                "code": "INTERNAL_ERROR",
                "message": "伺服器內部錯誤，請聯繫管理員。",
                "detail": {},
            },
        )
