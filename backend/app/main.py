"""FastAPI Backend for Document LLM Analysis.

Provides REST API endpoints with SSE streaming for LLM and RAG services.
Includes CORS, rate limiting, exception handling, and secure logging.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from prometheus_fastapi_instrumentator import Instrumentator

from app.api import (
    agent,
    analytics,
    auth,
    batch,
    data_files,
    health,
    ip_control,
    llm,
    llm_queue,
    mcp_tools,
    modeling,
    query,
    rag,
    reports,
    stats,
    upload,
    users,
)
from app.api.auth import get_current_admin_user
from app.api.cache_maintenance import router as cache_router
from app.api.chroma_maintenance import router as chroma_router
from app.api.deps import require_auth
from app.core.config import settings
from app.core.database import init_db
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    init_db()
    yield


app = FastAPI(
    title="Document LLM Analysis API",
    description="REST API with SSE streaming for document analysis",
    version="1.0.0",
    lifespan=lifespan,
)

register_exception_handlers(app)

Instrumentator().instrument(app)


_metrics_dependencies = (
    [Depends(require_auth)] if settings.METRICS_REQUIRE_AUTH else []
)


@app.get("/metrics", include_in_schema=False, dependencies=_metrics_dependencies)
def metrics_endpoint() -> Response:
    """Prometheus 指標。

    原本這個端點完全公開；在 production 下預設要求認證
    （可透過 METRICS_REQUIRE_AUTH=false 讓內網 scraper 免認證）。
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

cors_origins: list[str] = (
    [str(origin) for origin in settings.BACKEND_CORS_ORIGINS]
    if settings.BACKEND_CORS_ORIGINS
    else [
        "http://localhost:3000",
        "http://localhost:8501",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8501",
    ]
)

# `allow_origins=["*"]` 搭配 `allow_credentials=True` 是無效組合：
# 瀏覽器會直接拒絕帶 credentials 的萬用字元回應，而且等於對所有網站開放。
# 設了萬用字元就自動關閉 credentials，並明確警告。
_allow_credentials = True
if "*" in cors_origins:
    _allow_credentials = False
    logger.warning(
        "BACKEND_CORS_ORIGINS 設為 '*'，已自動關閉 allow_credentials。"
        "請改為列出實際的前端來源。"
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin"],
)

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    from slowapi.util import get_remote_address

    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[settings.RATE_LIMIT_DEFAULT],
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    # 只建立 Limiter 並不會套用 default_limits，必須加上 middleware，
    # 否則 RATE_LIMIT_DEFAULT 完全是裝飾品。
    app.add_middleware(SlowAPIMiddleware)
except ImportError:
    pass

# 這些 router 的端點在舊版完全沒有認證（任何人可呼叫，包含執行程式碼、
# 刪除向量庫、觸發 LLM 花費）。dependencies 會在生產環境強制認證，
# 開發環境維持可匿名（見 app/api/deps.py 的說明）。
_needs_auth = [Depends(require_auth)]

app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(
    llm.router, prefix="/api/llm", tags=["LLM"], dependencies=_needs_auth
)
app.include_router(llm_queue.router, prefix="/api/llm/queue", tags=["LLM Queue"])

app.include_router(
    rag.router, prefix="/api/rag", tags=["RAG"], dependencies=_needs_auth
)
app.include_router(
    reports.router, prefix="/api/reports", tags=["Reports"], dependencies=_needs_auth
)
app.include_router(
    query.router, prefix="/api/query", tags=["Query"], dependencies=_needs_auth
)
app.include_router(
    batch.router, prefix="/api/batch", tags=["Batch"], dependencies=_needs_auth
)
app.include_router(
    stats.router, prefix="/api/stats", tags=["Statistics"], dependencies=_needs_auth
)
app.include_router(
    upload.router, prefix="/api/upload", tags=["Upload"], dependencies=_needs_auth
)
app.include_router(
    data_files.router,
    prefix="/api/data-files",
    tags=["Data Files"],
    dependencies=_needs_auth,
)
app.include_router(
    modeling.router, prefix="/api/modeling", tags=["Modeling"], dependencies=_needs_auth
)
app.include_router(
    agent.router, prefix="/api/agent", tags=["Agent"], dependencies=_needs_auth
)
app.include_router(
    mcp_tools.router, prefix="/api", tags=["MCP Tools"], dependencies=_needs_auth
)
# 這兩個是「破壞性維運」端點（清除向量庫 / 清快取），只允許管理員。
app.include_router(
    chroma_router,
    prefix="/api",
    tags=["ChromaDB Maintenance"],
    dependencies=[Depends(get_current_admin_user)],
)
app.include_router(
    cache_router,
    prefix="/api",
    tags=["Cache Maintenance"],
    dependencies=[Depends(get_current_admin_user)],
)
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(ip_control.router, prefix="/api/admin/ip", tags=["IP Control"])
