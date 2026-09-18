"""Tests for file resolver utilities."""


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

    def test_resolve_with_absolute_path_outside_data_dir_is_denied(self, tmp_path):
        """資料目錄以外的絕對路徑預設必須被拒絕（任意檔案讀取防護）。"""
        test_file = tmp_path / "test.csv"
        test_file.write_text("a,b\n1,2")

        assert resolve_data_file(str(test_file)) is None

    def test_resolve_absolute_path_with_explicit_opt_in(self, tmp_path):
        """需要讀外部檔案時，呼叫端必須明確 opt-in。"""
        test_file = tmp_path / "test.csv"
        test_file.write_text("a,b\n1,2")

        result = resolve_data_file(str(test_file), allow_outside_allowed_roots=True)
        assert result == test_file

    def test_resolve_rejects_path_traversal(self):
        """`../../etc/passwd` 之類的相對路徑穿越必須被拒絕。"""
        assert resolve_data_file("../../../../../../etc/passwd") is None

    def test_resolve_rejects_absolute_system_file(self):
        assert resolve_data_file("/etc/passwd") is None

    def test_resolve_allows_file_inside_data_dir(self, tmp_path, monkeypatch):
        """資料目錄底下的檔案仍然可以正常解析。"""
        from app.utils import file_resolver

        data_dir = tmp_path / "data" / "uploads"
        data_dir.mkdir(parents=True)
        target = data_dir / "ok.csv"
        target.write_text("a,b\n1,2")

        monkeypatch.setattr(
            file_resolver, "ALLOWED_ROOTS", (tmp_path / "data",), raising=True
        )
        monkeypatch.setattr(
            file_resolver, "SEARCH_PATHS", [data_dir], raising=True
        )

        assert file_resolver.resolve_data_file("ok.csv") == target


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
