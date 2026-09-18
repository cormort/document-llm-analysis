"""管理員專用的系統資訊端點。

前端 `/admin/settings` 原本是一個「假頁面」：儲存只做 `setTimeout + alert`，
顯示的 HS256 / bcrypt / SQLite 全是硬編碼文案，IP 開關只存在瀏覽器狀態。
這裡提供一個**唯讀**且**不含機密**的實際設定快照，讓那個頁面顯示真實值。
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.auth import User, get_current_admin_user
from app.core.config import settings

router = APIRouter()


def _redact_database_url(url: str) -> str:
    """資料庫 URL 可能含帳密，只回傳骨架。"""
    if "@" in url and "://" in url:
        scheme, rest = url.split("://", 1)
        return f"{scheme}://***@{rest.split('@', 1)[1]}"
    return url


@router.get("/system-info")
async def get_system_info(
    current_user: Annotated[User, Depends(get_current_admin_user)],
) -> dict[str, Any]:
    """回傳目前實際生效的系統設定（不含任何金鑰）。"""
    secret = settings.JWT_SECRET_KEY
    return {
        "environment": settings.ENVIRONMENT,
        "auth": {
            "anonymous_access": settings.allow_anonymous_access,
            "jwt_algorithm": settings.JWT_ALGORITHM,
            "jwt_expire_hours": settings.JWT_ACCESS_TOKEN_EXPIRE_HOURS,
            "jwt_secret_configured": bool(secret),
            "jwt_secret_source": "env" if secret else "generated",
            # 只顯示指紋，不洩漏金鑰本身
            "jwt_secret_fingerprint": (
                f"{secret[:4]}…{secret[-4:]} (len={len(secret)})" if secret else None
            ),
        },
        "security": {
            "metrics_require_auth": settings.METRICS_REQUIRE_AUTH,
            "allow_private_llm_urls": settings.ALLOW_PRIVATE_LLM_URLS,
            "allow_client_api_keys": settings.ALLOW_CLIENT_API_KEYS,
            "cors_origins": list(settings.BACKEND_CORS_ORIGINS) or "localhost defaults",
        },
        "limits": {
            "rate_limit_default": settings.RATE_LIMIT_DEFAULT,
            "max_upload_size_mb": settings.MAX_UPLOAD_SIZE_MB,
        },
        "llm_defaults": {
            "fast_provider": settings.LLM_FAST_PROVIDER,
            "fast_model": settings.LLM_FAST_MODEL,
            "smart_provider": settings.LLM_SMART_PROVIDER,
            "smart_model": settings.LLM_SMART_MODEL,
            "google_api_key_configured": bool(settings.GOOGLE_API_KEY),
            "omlx_api_key_configured": bool(settings.OMLX_API_KEY),
        },
        "database": {
            "url": _redact_database_url(settings.DATABASE_URL),
        },
    }
