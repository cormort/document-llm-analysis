"""統一例外處理單元測試。"""

from app.core.exceptions import (
    AppError,
    FileValidationError,
    RateLimitExceededError,
)


def test_app_error_attributes() -> None:
    """AppError 應正確設定所有屬性。"""
    err = AppError(
        code="TEST_ERROR",
        message="測試錯誤",
        status_code=418,
        detail={"key": "value"},
    )
    assert err.code == "TEST_ERROR"
    assert err.message == "測試錯誤"
    assert err.status_code == 418
    assert err.detail == {"key": "value"}
    assert str(err) == "測試錯誤"


def test_app_error_defaults() -> None:
    """AppError 預設值應正確。"""
    err = AppError(code="ERR", message="msg")
    assert err.status_code == 400
    assert err.detail == {}


def test_file_validation_error() -> None:
    """FileValidationError 應設定正確的 code 和 status_code。"""
    err = FileValidationError(
        message="不支援的檔案類型",
        detail={"extension": ".exe"},
    )
    assert err.code == "FILE_VALIDATION_ERROR"
    assert err.status_code == 422
    assert err.detail["extension"] == ".exe"
    assert isinstance(err, AppError)


def test_rate_limit_exceeded_error() -> None:
    """RateLimitExceededError 應設定正確的 code 和 status_code。"""
    err = RateLimitExceededError()
    assert err.code == "RATE_LIMIT_EXCEEDED"
    assert err.status_code == 429
    assert isinstance(err, AppError)
