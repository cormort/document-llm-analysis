"""應用程式核心設定。

從環境變數與 .env 檔案讀取設定，
提供 CORS、LLM 路由、Rate Limiting 等參數。
"""

import logging
import os
import secrets
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_DEV_SECRET_FILE = _BACKEND_ROOT / "data" / ".jwt_secret"


class Settings(BaseSettings):
    """全域設定，自動從環境變數或 .env 載入。"""

    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Document LLM Analysis"

    # 執行環境：development / staging / production
    ENVIRONMENT: str = "development"

    # 是否允許匿名存取受保護的 API。
    # 預設 False（安全預設）：所有需要認證的端點都必須帶 Bearer token。
    # 本機開發若想省去登入流程，可明確設為 true，
    # 但請勿在對外開放的環境使用。
    ALLOW_ANONYMOUS_ACCESS: bool = False

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

    # omlx
    LLM_OMLX_URL: str = "http://127.0.0.1:8000/v1"
    OMLX_API_KEY: str = ""

    # Upload
    MAX_UPLOAD_SIZE_MB: int = 50

    # 是否接受前端傳來的 API Key。
    # 設為 false 時只使用伺服器端設定（GOOGLE_API_KEY / OMLX_API_KEY），
    # 適合單一組織內部部署，避免金鑰在瀏覽器與網路間流動。
    ALLOW_CLIENT_API_KEYS: bool = True

    # /metrics 是否要求認證（Prometheus 需帶 token；純內網可設 false）
    METRICS_REQUIRE_AUTH: bool = True

    # 是否允許 LLM/MCP 的 URL 指向私有網段（本機 Ollama / LM Studio 需要）。
    # 雲端 metadata 與 link-local 位址永遠禁止，不受此設定影響。
    ALLOW_PRIVATE_LLM_URLS: bool = True

    # Database
    DATABASE_URL: str = "sqlite:///./data/users.db"

    # JWT Settings
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_HOURS: int = 24

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.JWT_SECRET_KEY:
            self.JWT_SECRET_KEY = self._resolve_jwt_secret()

    @property
    def is_production(self) -> bool:
        """是否為生產環境。"""
        return self.ENVIRONMENT.lower() in {"production", "prod"}

    @property
    def allow_anonymous_access(self) -> bool:
        """是否允許匿名呼叫需要認證的端點。

        安全預設為 False（一律要求 token）。開發時若確定只在 localhost 使用，
        可以設 `ALLOW_ANONYMOUS_ACCESS=true` 換取方便；此時啟動會印出警告。
        """
        return bool(self.ALLOW_ANONYMOUS_ACCESS)

    def _resolve_jwt_secret(self) -> str:
        """決定 JWT 簽章金鑰。

        - production：沒有設定 JWT_SECRET_KEY 就直接啟動失敗（fail fast），
          避免用隨機金鑰產生「重啟即失效 / 多 worker 互不承認」的 token。
        - 其他環境：把隨機產生的金鑰持久化到 data/.jwt_secret（權限 600），
          讓重啟後既有 token 仍然有效，也讓多個 worker 共用同一把金鑰。
        """
        env_secret = os.getenv("JWT_SECRET_KEY", "")
        if env_secret:
            return env_secret

        if self.is_production:
            raise RuntimeError(
                "JWT_SECRET_KEY 未設定。生產環境必須設定固定的 JWT_SECRET_KEY，"
                "否則 token 會在重啟後全部失效。"
            )

        try:
            if _DEV_SECRET_FILE.exists():
                stored = _DEV_SECRET_FILE.read_text(encoding="utf-8").strip()
                if stored:
                    return stored
            _DEV_SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
            generated = secrets.token_urlsafe(32)
            _DEV_SECRET_FILE.write_text(generated, encoding="utf-8")
            _DEV_SECRET_FILE.chmod(0o600)
            logger.warning(
                "JWT_SECRET_KEY 未設定，已於 %s 產生開發用金鑰。"
                "生產環境請改以環境變數設定。",
                _DEV_SECRET_FILE,
            )
            return generated
        except OSError:
            # 無法寫入檔案時退回隨機金鑰（行為與舊版相同，但會記錄警告）
            logger.warning(
                "JWT_SECRET_KEY 未設定且無法寫入 %s，改用本次啟動的隨機金鑰；"
                "重啟後既有 token 將失效。",
                _DEV_SECRET_FILE,
            )
            return secrets.token_urlsafe(32)

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
        env_file=str(Path(__file__).resolve().parents[3] / ".env"),
        extra="ignore",
    )


settings = Settings()
