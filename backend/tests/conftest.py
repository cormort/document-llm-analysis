"""共用測試 fixtures。

提供 FastAPI TestClient、測試用 mock service 等共用設定，
供所有測試模組使用。
"""

import os
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def set_test_env():
    os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only")
    os.environ.setdefault("DATABASE_URL", "sqlite:///./test_db.db")
    yield


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    """提供 FastAPI TestClient fixture。"""
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def sample_csv_content() -> bytes:
    """提供測試用 CSV 檔案內容。"""
    return b"name,age,score\nAlice,30,85.5\nBob,25,92.3\nCharlie,35,78.1"


@pytest.fixture()
def sample_json_content() -> bytes:
    """提供測試用 JSON 檔案內容。"""
    import json

    data = [
        {"name": "Alice", "age": 30, "score": 85.5},
        {"name": "Bob", "age": 25, "score": 92.3},
    ]
    return json.dumps(data).encode("utf-8")


@pytest.fixture()
def mock_llm_service():
    """Mock LLM service for testing."""
    mock = MagicMock()
    mock.generate = AsyncMock(return_value="Test response")
    mock.generate_stream = AsyncMock()
    return mock


@pytest.fixture()
def mock_rag_service():
    """Mock RAG service for testing."""
    mock = MagicMock()
    mock.query = AsyncMock(return_value={"answer": "Test answer", "sources": []})
    mock.index_document = AsyncMock(return_value=True)
    return mock
