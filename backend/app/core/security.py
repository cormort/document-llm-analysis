"""安全相關工具：密碼雜湊與 JWT 處理。"""

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_HOURS = settings.JWT_ACCESS_TOKEN_EXPIRE_HOURS

# bcrypt 只使用前 72 bytes，超過的部分會被截斷。
# 若不在輸入端擋掉，長度 > 72 bytes 的密碼會有多個等價字串。
BCRYPT_MAX_PASSWORD_BYTES = 72


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """驗證密碼。

    雜湊格式錯誤（例如舊資料、空字串）時回傳 False，不讓例外往外洩。
    """
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False


def get_password_hash(password: str) -> str:
    """產生密碼雜湊。"""
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError(
            f"密碼長度不可超過 {BCRYPT_MAX_PASSWORD_BYTES} bytes（UTF-8 編碼後）"
        )
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def create_access_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    """建立 JWT access token。"""
    now = datetime.now(UTC)
    to_encode = data.copy()
    to_encode.setdefault("iat", now)
    to_encode["exp"] = now + (
        expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    )
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """解碼 JWT token，失敗回傳 None。

    強制要求 token 帶有 `exp` 與 `sub`，避免偽造出永不過期 / 無主體的 token。
    """
    if not token:
        return None
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require_exp": True, "require_sub": True},
        )
    except JWTError:
        return None
