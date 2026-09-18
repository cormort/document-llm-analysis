"""檔案上傳端點。

提供檔案上傳 API，包含檔案大小限制、MIME 類型驗證（Magic Number）
及副檔名白名單檢查。
"""

import logging
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.exceptions import FileValidationError

logger = logging.getLogger(__name__)

router = APIRouter()

# 上傳設定
UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "uploads",
)
# 大小上限改由設定檔統一控制（settings.MAX_UPLOAD_SIZE_MB）
MAX_UPLOAD_SIZE = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
CHUNK_SIZE = 1024 * 1024  # 1MB

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
    # 注意："application/octet-stream" 刻意不在白名單內 —— 它會匹配幾乎所有
    # 二進位檔，等於讓內容檢查失效。若確實需要上傳無法辨識格式的檔案，
    # 應改為安裝 libmagic（Dockerfile.backend 已加入 libmagic1）。
}

# 即使 magic bytes 落在白名單，也明確拒絕的可執行檔類型
BLOCKED_MIME_TYPES: set[str] = {
    "application/x-dosexec",
    "application/x-executable",
    "application/x-mach-binary",
    "application/x-sharedlib",
    "application/x-msdownload",
    "application/x-java-archive",
    "application/x-shellscript",
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

    以分塊讀取方式累計大小，超過上限立即中止，
    避免惡意客戶端用超過限制的檔案吃光記憶體。

    Returns:
        檔案完整內容 bytes。

    Raises:
        FileValidationError: 檔案超過大小限制。
    """
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_UPLOAD_SIZE:
            raise FileValidationError(
                message=(f"檔案大小超過限制 ({settings.MAX_UPLOAD_SIZE_MB}MB)"),
                detail={
                    "file_size_bytes": total,
                    "max_size_bytes": MAX_UPLOAD_SIZE,
                },
            )
        chunks.append(chunk)
    return b"".join(chunks)


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

    if mime_type in BLOCKED_MIME_TYPES:
        raise FileValidationError(
            message=f"不允許上傳可執行檔: {mime_type}",
            detail={"detected_mime_type": mime_type, "filename": filename},
        )

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
    2. 檔案大小限制（settings.MAX_UPLOAD_SIZE_MB）
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
    # 加上唯一前綴，避免同名上傳互相覆蓋（也避免覆蓋他人的檔案）
    stored_filename = f"{uuid.uuid4().hex[:8]}_{safe_filename}"
    file_path = os.path.join(UPLOAD_DIR, stored_filename)

    # 檔案寫入是阻塞式 IO，放到 threadpool 以免卡住 event loop
    def _write() -> None:
        with open(file_path, "wb") as buffer:
            buffer.write(content)

    await run_in_threadpool(_write)

    logger.info("檔案上傳成功: %s (%d bytes)", stored_filename, len(content))

    return UploadResponse(
        success=True,
        file_path=file_path,
        message=f"成功上傳 {safe_filename}",
    )
