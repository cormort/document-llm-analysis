"""數據檔案管理端點。

列出、刪除 uploads 目錄中的純數據檔案（CSV/Excel/JSON），
與 RAG 文件索引完全分離。
"""

from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from app.utils.file_resolver import ABS_UPLOAD_DIR

router = APIRouter()

DATA_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json"}


class DataFileInfo(BaseModel):
    file_name: str
    file_path: str
    size_bytes: int
    modified_at: str


class DataFileListResponse(BaseModel):
    files: list[DataFileInfo]


@router.get("", response_model=DataFileListResponse)
async def list_data_files() -> DataFileListResponse:
    """列出 uploads 目錄中所有數據檔案。"""
    files: list[DataFileInfo] = []
    if ABS_UPLOAD_DIR.exists():
        for f in sorted(ABS_UPLOAD_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if f.is_file() and f.suffix.lower() in DATA_EXTENSIONS:
                stat = f.stat()
                files.append(DataFileInfo(
                    file_name=f.name,
                    file_path=str(f),
                    size_bytes=stat.st_size,
                    modified_at=str(int(stat.st_mtime)),
                ))
    return DataFileListResponse(files=files)


@router.delete("/{file_name}")
async def delete_data_file(file_name: str) -> dict:
    """刪除指定的數據檔案。"""
    safe_name = Path(file_name).name  # 防止路徑穿越
    target = ABS_UPLOAD_DIR / safe_name
    if not target.exists() or target.suffix.lower() not in DATA_EXTENSIONS:
        return {"success": False, "message": "檔案不存在"}
    target.unlink()
    return {"success": True, "message": f"{safe_name} 已刪除"}
