"""統一檔案路徑解析工具。

解決多個 API 檔案中重複的檔案路徑搜尋邏輯。
"""

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

_THIS_FILE = Path(__file__).resolve()
_BACKEND_ROOT = _THIS_FILE.parents[2]  # backend/

DATA_DIR = Path("data")
UPLOAD_DIR = DATA_DIR / "uploads"
BACKEND_DATA_DIR = Path("backend/data")
BACKEND_UPLOAD_DIR = BACKEND_DATA_DIR / "uploads"
ABS_UPLOAD_DIR = _BACKEND_ROOT / "data" / "uploads"
ABS_DATA_DIR = _BACKEND_ROOT / "data"

SEARCH_PATHS = [
    ABS_UPLOAD_DIR,
    ABS_DATA_DIR,
    DATA_DIR,
    UPLOAD_DIR,
    BACKEND_DATA_DIR,
    BACKEND_UPLOAD_DIR,
]


def resolve_data_file(file_path_str: str) -> Path | None:
    """解析資料檔案路徑。

    搜尋多個可能目錄，回傳存在的檔案路徑。

    Args:
        file_path_str: 檔案路徑字串

    Returns:
        Path 物件，如果找不到則回傳 None
    """
    file_path = Path(file_path_str)

    if file_path.is_absolute() and file_path.exists():
        return file_path

    for search_dir in SEARCH_PATHS:
        candidate = search_dir / file_path_str
        if candidate.exists():
            return candidate

    if file_path.exists():
        return file_path

    return None


def load_dataframe(file_path_str: str) -> pd.DataFrame | None:
    """載入資料檔案為 DataFrame。

    Args:
        file_path_str: 檔案路徑字串

    Returns:
        DataFrame，如果載入失敗則回傳 None
    """
    file_path = resolve_data_file(file_path_str)
    if file_path is None:
        return None

    suffix = file_path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(file_path)
    elif suffix in [".xlsx", ".xls"]:
        from app.utils.excel_processor import smart_read_excel

        return smart_read_excel(str(file_path))
    elif suffix == ".json":
        return pd.read_json(file_path)
    elif suffix == ".parquet":
        return pd.read_parquet(file_path)

    return None


def convert_numpy_types(obj: Any) -> Any:
    """轉換 numpy 類型為 Python 原生類型。

    用於 JSON 序列化前的資料轉換。

    Args:
        obj: 要轉換的物件

    Returns:
        轉換後的物件
    """
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif pd.isna(obj):
        return None
    return obj


def get_dataframe_info(df: pd.DataFrame) -> dict[str, Any]:
    """取得 DataFrame 基本資訊。

    Args:
        df: Pandas DataFrame

    Returns:
        包含 shape, columns, dtypes 的字典
    """
    return {
        "shape": df.shape,
        "columns": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "memory_usage": df.memory_usage(deep=True).sum(),
    }
