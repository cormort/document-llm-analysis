"""應用程式核心設定。

從環境變數與 .env 檔案讀取設定，
提供 CORS、LLM 路由、Rate Limiting 等參數。
"""

import os
import secrets
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全域設定，自動從環境變數或 .env 載入。"""

    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Document LLM Analysis"

    # CORS（以逗號分隔的 URL 清單，如 http://localhost:3000,http://localhost:8501）
    BACKEND_CORS_ORIGINS: list[str] = []

    # API Keys
    GOOGLE_API_KEY: str = ""

    # Rate Limiting（slowapi 格式，如 "30/minute"）
    RATE_LIMIT_DEFAULT: str = "30/minute"

    # LLM Routing (Triage) Defaults
    LLM_FAST_PROVIDER: str = "Gemini"
    LLM_FAST_MODEL: str = "gemini-1.5-flash"
    LLM_FAST_URL: str = "http://localhost:11434/v1"

    LLM_SMART_PROVIDER: str = "Gemini"
    LLM_SMART_MODEL: str = "gemini-1.5-pro"
    LLM_SMART_URL: str = "http://localhost:1234/v1"

    # Upload
    MAX_UPLOAD_SIZE_MB: int = 50

    # Database
    DATABASE_URL: str = "sqlite:///./data/users.db"

    # JWT Settings
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_HOURS: int = 24

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.JWT_SECRET_KEY:
            self.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
            if not self.JWT_SECRET_KEY:
                self.JWT_SECRET_KEY = secrets.token_urlsafe(32)
                import warnings

                warnings.warn(
                    "JWT_SECRET_KEY not set. Using random key. "
                    "Set JWT_SECRET_KEY environment variable for production.",
                    UserWarning,
                )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        """支援逗號分隔字串或 JSON 陣列格式。"""
        if isinstance(v, str):
            if not v.strip():
                return []
            return [i.strip() for i in v.split(",")]
        return list(v)

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
