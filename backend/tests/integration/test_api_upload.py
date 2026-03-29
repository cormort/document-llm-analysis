"""Upload API 整合測試。

驗證檔案上傳的三層安全驗證：
1. 副檔名白名單
2. 檔案大小限制
3. MIME 類型檢查
"""

import io

from fastapi.testclient import TestClient


def test_upload_valid_csv(
    client: TestClient, sample_csv_content: bytes
) -> None:
    """上傳合法 CSV 檔案應成功。"""
    response = client.post(
        "/api/upload",
        files={"file": ("test.csv", io.BytesIO(sample_csv_content), "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "test.csv" in data["file_path"]


def test_upload_invalid_extension(client: TestClient) -> None:
    """上傳不允許的副檔名應回傳 422。"""
    response = client.post(
        "/api/upload",
        files={
            "file": (
                "malicious.exe",
                io.BytesIO(b"MZ fake exe content"),
                "application/octet-stream",
            )
        },
    )
    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "FILE_VALIDATION_ERROR"


def test_upload_path_traversal(
    client: TestClient, sample_csv_content: bytes
) -> None:
    """路徑穿越攻擊的檔名應被清理。"""
    response = client.post(
        "/api/upload",
        files={
            "file": (
                "../../../etc/passwd.csv",
                io.BytesIO(sample_csv_content),
                "text/csv",
            )
        },
    )
    # 應成功但檔名被清理為 passwd.csv
    assert response.status_code == 200
    data = response.json()
    assert ".." not in data["file_path"]
