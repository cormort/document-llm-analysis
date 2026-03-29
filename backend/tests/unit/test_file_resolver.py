"""Tests for file resolver utilities."""

import pytest

from app.utils.file_resolver import (
    convert_numpy_types,
    get_dataframe_info,
    load_dataframe,
    resolve_data_file,
)


class TestResolveDataFile:
    def test_resolve_nonexistent_file(self):
        result = resolve_data_file("nonexistent_file.csv")
        assert result is None

    def test_resolve_with_absolute_path(self, tmp_path):
        test_file = tmp_path / "test.csv"
        test_file.write_text("a,b\n1,2")

        result = resolve_data_file(str(test_file))
        assert result == test_file


class TestLoadDataFrame:
    def test_load_nonexistent_file(self):
        result = load_dataframe("nonexistent_file.csv")
        assert result is None


class TestConvertNumpyTypes:
    def test_convert_int(self):
        import numpy as np

        result = convert_numpy_types(np.int64(42))
        assert result == 42
        assert isinstance(result, int)

    def test_convert_float(self):
        import numpy as np

        result = convert_numpy_types(np.float64(3.14))
        assert result == 3.14
        assert isinstance(result, float)

    def test_convert_array(self):
        import numpy as np

        result = convert_numpy_types(np.array([1, 2, 3]))
        assert result == [1, 2, 3]
        assert isinstance(result, list)

    def test_convert_dict(self):
        import numpy as np

        data = {"a": np.int64(1), "b": np.float64(2.0)}
        result = convert_numpy_types(data)
        assert result == {"a": 1, "b": 2.0}

    def test_convert_nested(self):
        import numpy as np

        data = {"values": np.array([1, 2, 3]), "count": np.int64(3)}
        result = convert_numpy_types(data)
        assert result == {"values": [1, 2, 3], "count": 3}


class TestGetDataFrameInfo:
    def test_basic_dataframe(self):
        import pandas as pd

        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        info = get_dataframe_info(df)

        assert info["shape"] == (3, 2)
        assert "a" in info["columns"]
        assert "b" in info["columns"]
        assert "dtypes" in info
        assert info["dtypes"]["a"] == "int64"
        assert "object" in info["dtypes"]["b"] or "str" in info["dtypes"]["b"]
