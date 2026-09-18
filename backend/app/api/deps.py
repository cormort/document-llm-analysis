"""共用 API 依賴：可選認證 / 強制認證。

背景：專案多數 router（stats、rag、reports、query、mcp…）原本完全沒有認證，
任何人都能呼叫，包含「執行任意程式碼」「刪除向量資料庫」「呼叫 LLM 花錢」
等級的端點。

為了不破壞既有前端（前端只有部分請求帶 Authorization），這裡採取可漸進的
策略：

- 開發環境（ENVIRONMENT != production）：允許匿名，行為與舊版相同。
- 生產環境：一律要求有效的 Bearer token，否則回 401。

前端遷移完成（所有請求都帶 token）後，可將 `ALLOW_ANONYMOUS_ACCESS` 設為
false，在任何環境都強制認證。
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

optional_bearer = HTTPBearer(auto_error=False)


def get_optional_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(optional_bearer)
    ] = None,
    db: Annotated[Session, Depends(get_db)] = None,  # type: ignore[assignment]
) -> User | None:
    """回傳目前登入的使用者；沒有帶 token 或 token 無效時回傳 None。"""
    if credentials is None or not credentials.credentials:
        return None
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        return None
    username = payload.get("sub")
    if not username:
        return None
    user = db.execute(
        select(User).where(User.username == username)
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        return None
    return user


def require_auth(
    user: Annotated[User | None, Depends(get_optional_current_user)],
) -> User | None:
    """需要認證的端點依賴（生產環境強制，開發環境可匿名）。"""
    if user is not None:
        return user
    if settings.allow_anonymous_access:
        return None
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="需要登入才能使用此功能",
        headers={"WWW-Authenticate": "Bearer"},
    )
