"""Health API 測試。"""

from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient) -> None:
    """GET /api/health 應回傳 200。"""
    response = client.get("/api/health")
    assert response.status_code == 200
