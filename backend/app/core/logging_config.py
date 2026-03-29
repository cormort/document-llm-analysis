"""日誌配置模組。

提供敏感資訊過濾器與結構化日誌設定，
確保 API Key、密碼等不會被寫入 log。
"""

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path


class SensitiveDataFilter(logging.Filter):
    """過濾 log 中的敏感資訊。

    自動偵測並遮蔽 API key、密碼、token 等敏感字串。
    """

    # 匹配常見敏感參數的 key=value 模式
    _PATTERNS: list[re.Pattern[str]] = [
        re.compile(
            r"(api[_-]?key|password|token|secret|authorization)"
            r"[\s]*[=:]\s*['\"]?([^\s'\",:}{]+)",
            re.IGNORECASE,
        ),
        # 匹配看起來像 API key 的長字串 (20+ 字元的英數混合)
        re.compile(
            r"\b(AIza[0-9A-Za-z_-]{35})\b"  # Google API Key 格式
        ),
        re.compile(
            r"(sk-[a-zA-Z0-9]{20,})"  # OpenAI API Key 格式
        ),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """過濾並遮蔽敏感資訊。"""
        if record.args:
            record.msg = record.msg % record.args
            record.args = None

        msg = record.getMessage()
        for pattern in self._PATTERNS:
            msg = pattern.sub(
                lambda m: f"{m.group(1)}=[REDACTED]"
                if m.lastindex and m.lastindex >= 2
                else "[REDACTED]",
                msg,
            )
        record.msg = msg
        return True


def setup_logging(
    log_dir: str = "logs",
    level: int = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> None:
    """設定應用程式日誌。

    Args:
        log_dir: 日誌檔案目錄。
        level: 日誌等級。
        max_bytes: 單一日誌檔案最大大小。
        backup_count: 保留的備份檔案數量。
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    sensitive_filter = SensitiveDataFilter()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(sensitive_filter)

    # File handler（RotatingFileHandler 避免 log 過大）
    file_handler = RotatingFileHandler(
        log_path / "app.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(sensitive_filter)

    # Error-only file handler
    error_handler = RotatingFileHandler(
        log_path / "error.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    error_handler.addFilter(sensitive_filter)

    # 設定根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    # 清除預設 handler 避免重複
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
