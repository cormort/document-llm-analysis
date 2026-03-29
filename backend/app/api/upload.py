"""檔案上傳端點。

提供檔案上傳 API，包含檔案大小限制、MIME 類型驗證（Magic Number）
及副檔名白名單檢查。
"""

import logging
import os
from pathlib import Path

from app.core.exceptions import FileValidationError
from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# 上傳設定
UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "uploads",
)
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB

# 允許的副檔名白名單
ALLOWED_EXTENSIONS: set[str] = {
    ".pdf",
    ".docx",
    ".doc",
    ".txt",
    ".csv",
    ".xlsx",
    ".xls",
    ".json",
    ".md",
}

# 允許的 MIME 類型（基於檔案內容 magic bytes 驗證）
ALLOWED_MIME_PREFIXES: set[str] = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument",
    "application/vnd.ms-excel",
    "application/msword",
    "text/",
    "application/json",
    "application/zip",  # .docx/.xlsx 實際上是 zip 格式
    "application/octet-stream",  # 某些檔案的 fallback
}


class UploadResponse(BaseModel):
    """上傳回應模型。"""

    success: bool
    file_path: str
    message: str


def _validate_extension(filename: str) -> None:
    """驗證檔案副檔名是否在白名單中。"""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise FileValidationError(
            message=f"不支援的檔案類型: {ext}",
            detail={
                "extension": ext,
                "allowed": sorted(ALLOWED_EXTENSIONS),
            },
        )


async def _validate_file_size(file: UploadFile) -> bytes:
    """驗證檔案大小並讀取完整內容。

    Returns:
        檔案完整內容 bytes。

    Raises:
        FileValidationError: 檔案超過大小限制。
    """
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise FileValidationError(
            message=f"檔案大小超過限制 ({MAX_UPLOAD_SIZE // (1024 * 1024)}MB)",
            detail={
                "file_size_bytes": len(content),
                "max_size_bytes": MAX_UPLOAD_SIZE,
            },
        )
    return content


def _validate_content_type(content: bytes, filename: str) -> None:
    """基於檔案內容驗證 MIME 類型。

    嘗試使用 python-magic，若未安裝則退回副檔名推斷。
    """
    try:
        import magic

        mime_type = magic.from_buffer(content[:2048], mime=True)
    except ImportError:
        # python-magic 未安裝，使用 mimetypes 進行基本檢查
        import mimetypes

        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type is None:
            mime_type = "application/octet-stream"

    is_allowed = any(mime_type.startswith(prefix) for prefix in ALLOWED_MIME_PREFIXES)
    if not is_allowed:
        raise FileValidationError(
            message=f"不允許的檔案內容類型: {mime_type}",
            detail={"detected_mime_type": mime_type, "filename": filename},
        )


@router.post("", response_model=UploadResponse)
async def upload_file(file: UploadFile = File()) -> UploadResponse:  # noqa: B008
    """上傳檔案至伺服器。

    包含三層驗證：
    1. 副檔名白名單檢查
    2. 檔案大小限制（50MB）
    3. 檔案內容 MIME 類型驗證
    """
    filename = file.filename or "unnamed_file"

    # 1. 副檔名驗證
    _validate_extension(filename)

    # 2. 大小驗證（同時讀取內容）
    content = await _validate_file_size(file)

    # 3. 內容類型驗證
    _validate_content_type(content, filename)

    # 儲存檔案
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    # 使用安全的檔名，防止路徑穿越攻擊
    safe_filename = Path(filename).name
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as buffer:
        buffer.write(content)

    logger.info("檔案上傳成功: %s (%d bytes)", safe_filename, len(content))

    return UploadResponse(
        success=True,
        file_path=file_path,
        message=f"成功上傳 {safe_filename}",
    )
