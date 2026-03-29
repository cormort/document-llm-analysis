"""FastAPI Backend for Document LLM Analysis.

Provides REST API endpoints with SSE streaming for LLM and RAG services.
Includes CORS, rate limiting, exception handling, and secure logging.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    agent,
    auth,
    batch,
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
    analytics,
)
from app.api.chroma_maintenance import router as chroma_router
from app.api.cache_maintenance import router as cache_router
from app.core.config import settings
from app.core.database import init_db
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import setup_logging


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

from prometheus_fastapi_instrumentator import Instrumentator

register_exception_handlers(app)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address

    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[settings.RATE_LIMIT_DEFAULT],
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
except ImportError:
    pass

app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(llm.router, prefix="/api/llm", tags=["LLM"])
app.include_router(llm_queue.router, prefix="/api/llm/queue", tags=["LLM Queue"])
app.include_router(rag.router, prefix="/api/rag", tags=["RAG"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(query.router, prefix="/api/query", tags=["Query"])
app.include_router(batch.router, prefix="/api/batch", tags=["Batch"])
app.include_router(stats.router, prefix="/api/stats", tags=["Statistics"])
app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
app.include_router(modeling.router, prefix="/api/modeling", tags=["Modeling"])
app.include_router(agent.router, prefix="/api/agent", tags=["Agent"])
app.include_router(mcp_tools.router, prefix="/api", tags=["MCP Tools"])
app.include_router(chroma_router, prefix="/api", tags=["ChromaDB Maintenance"])
app.include_router(cache_router, prefix="/api", tags=["Cache Maintenance"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(ip_control.router, prefix="/api/admin/ip", tags=["IP Control"])
