"""路由與認證接線的煙霧測試。

驗證 `main.py` 掛上的 `require_auth` / `get_current_admin_user` 真的生效：
開發環境可匿名（維持與現有前端相容），一旦把 `ALLOW_ANONYMOUS_ACCESS`
設為 False（production 行為），未帶 token 的請求必須被擋下。

為了在沒安裝 torch / sentence-transformers 的環境也能執行，這裡會為缺少的
重量級套件插入極簡 stub。
"""

import importlib.util
import sys
import types

import pytest
from fastapi.testclient import TestClient


def _stub_missing(module_name: str, **attrs) -> None:
    """若套件不存在，插入一個極簡 stub（只在測試環境使用）。"""
    if importlib.util.find_spec(module_name) is not None:
        return
    module = types.ModuleType(module_name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[module_name] = module


class _AnyModel:
    def __init__(self, *args, **kwargs):  # noqa: ARG002
        pass

    def encode(self, *args, **kwargs):  # noqa: ARG002
        return []

    def predict(self, *args, **kwargs):  # noqa: ARG002
        return []


# 注意：不要 stub `torch`。scipy 的 array_api_compat 會偵測 torch 是否可用，
# 假模組會讓 scipy 在 import 期間炸掉；而 torch 不存在時 RAGBase._get_device()
# 已經會自行回退 CPU。
_stub_missing(
    "sentence_transformers",
    SentenceTransformer=_AnyModel,
    CrossEncoder=_AnyModel,
)

from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def production_mode(monkeypatch):
    """模擬 production：不允許匿名。"""
    monkeypatch.setattr(settings, "ALLOW_ANONYMOUS_ACCESS", False, raising=True)
    yield
    monkeypatch.setattr(settings, "ALLOW_ANONYMOUS_ACCESS", None, raising=True)


def test_health_is_public(client):
    assert client.get("/api/health").status_code == 200


def test_metrics_public_in_development(client):
    """開發環境（允許匿名）時 /metrics 可讀取。"""
    assert client.get("/metrics").status_code == 200


def test_protected_endpoints_reject_anonymous_in_production(client, production_mode):
    """production 模式下，未帶 token 一律 401。"""
    for method, path in [
        ("GET", "/api/rag/documents"),
        ("GET", "/metrics"),
        ("GET", "/api/data-files"),
        ("POST", "/api/stats/diagnostic"),
        ("POST", "/api/query/execute"),
        ("GET", "/api/llm/models"),
        ("GET", "/api/mcp/servers"),
    ]:
        response = client.request(method, path, json={} if method == "POST" else None)
        assert response.status_code == 401, f"{method} {path} → {response.status_code}"


def test_admin_only_endpoints_require_admin_token(client):
    """破壞性維運端點需要管理員權杖（無 token 一律被拒）。

    FastAPI 的 HTTPBearer 在不同版本會回 401 或 403，兩者都代表「被擋下」。
    """
    for path in ["/api/chroma/stats", "/api/cache/stats"]:
        status_code = client.get(path).status_code
        assert status_code in (401, 403), f"{path} → {status_code}"


def test_validation_still_returns_422_when_authenticated(client):
    """認證通過後仍要正常做輸入驗證（證明不是所有請求都被擋）。"""
    response = client.post("/api/query/execute", json={})
    assert response.status_code == 422
