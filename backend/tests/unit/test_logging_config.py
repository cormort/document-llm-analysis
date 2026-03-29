"""敏感資訊 Log 過濾器單元測試。"""

import logging

from app.core.logging_config import SensitiveDataFilter


def test_filter_google_api_key() -> None:
    """Google API Key 格式應被遮蔽。"""
    filter_ = SensitiveDataFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="API key is AIzaSyA1234567890abcdefghijklmnopqrstuv",
        args=None,
        exc_info=None,
    )
    filter_.filter(record)
    assert "AIzaSy" not in record.msg
    assert "[REDACTED]" in record.msg


def test_filter_openai_api_key() -> None:
    """OpenAI API Key 格式應被遮蔽。"""
    filter_ = SensitiveDataFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="sk-abcdef1234567890abcdef1234567890abcdef1234567890ab",
        args=None,
        exc_info=None,
    )
    filter_.filter(record)
    assert "sk-" not in record.msg
    assert "[REDACTED]" in record.msg


def test_filter_key_value_pattern() -> None:
    """key=value 格式的敏感資訊應被遮蔽。"""
    filter_ = SensitiveDataFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Connecting with api_key=my_secret_key_123",
        args=None,
        exc_info=None,
    )
    filter_.filter(record)
    assert "my_secret_key_123" not in record.msg
    assert "[REDACTED]" in record.msg


def test_filter_preserves_normal_message() -> None:
    """一般訊息不應被修改。"""
    filter_ = SensitiveDataFilter()
    msg = "Processing 100 documents successfully"
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg=msg,
        args=None,
        exc_info=None,
    )
    filter_.filter(record)
    assert record.msg == msg
