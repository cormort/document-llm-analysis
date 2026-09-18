"""安全強化修正的回歸測試。

涵蓋：
- `validate_code_safety`（/api/query/execute 的 AST 白名單）
- `sanitize_identifier` / `quote_identifier`（DuckDB SQL injection）
- `Settings` 的 JWT 金鑰與匿名存取策略
"""

import pytest

from app.core.config import Settings
from app.services.duckdb_service import quote_identifier, sanitize_identifier
from app.utils.code_safety import validate_code_safety


class TestValidateCodeSafety:
    @pytest.mark.parametrize(
        "code",
        [
            "import os",
            "from os import system",
            "__import__('os').system('id')",
            "df.__class__.__mro__",
            "pd.io.common.os.system('id')",
            "open('/etc/passwd').read()",
            "eval('1+1')",
            "exec('x=1')",
            "getattr(df, 'to_csv')('/tmp/x')",
            "df.to_pickle('/tmp/x.pkl')",
            "result = df.to_csv('/tmp/leak.csv')",
            "df.query('a > 1', inplace=True)\nimport os",
            "result = pd.read_pickle('/tmp/x.pkl')",
            "result = df.to_parquet('/tmp/x.parquet')",
        ],
    )
    def test_rejects_dangerous_code(self, code):
        is_safe, _ = validate_code_safety(code)
        assert is_safe is False

    @pytest.mark.parametrize(
        "code",
        [
            'result = df[df["age"] > 30]',
            'result = df.groupby("dept")["salary"].sum().reset_index()',
            'result = df.assign(total=df["a"] + df["b"])',
            "result = len(df)",
            'result = df["a"].round(2)',
            'result = df.sort_values("a", ascending=False).head(10)',
        ],
    )
    def test_allows_typical_pandas_code(self, code):
        is_safe, error = validate_code_safety(code)
        assert is_safe is True, error

    def test_rejects_oversized_code(self):
        is_safe, _ = validate_code_safety("x = 1\n" * 2000)
        assert is_safe is False


class TestDuckDBSanitizer:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("sales", "sales"),
            ("my data;DROP TABLE users", "my_data_DROP_TABLE_users"),
            ("2024-report", "t_2024_report"),
            ("", "table"),
            ("...", "table"),
        ],
    )
    def test_sanitize_identifier(self, raw, expected):
        assert sanitize_identifier(raw) == expected

    def test_quote_identifier_neutralises_quotes(self):
        quoted = quote_identifier('a"b')
        assert '"' not in quoted[1:-1] or '""' in quoted
        assert quoted.startswith('"') and quoted.endswith('"')

    def test_forbidden_sql_is_rejected(self):
        from app.services.duckdb_service import DuckDBService

        service = DuckDBService()
        for sql in [
            "COPY (SELECT 1) TO '/tmp/x.csv'",
            "CREATE TABLE x AS SELECT 1",
            "SELECT * FROM read_csv('/etc/passwd')",
            "SELECT 1; DROP TABLE t",
            "ATTACH '/tmp/x.db'",
        ]:
            with pytest.raises(ValueError):
                service._assert_read_only_sql(sql)


class TestSettingsHardening:
    def test_production_requires_jwt_secret(self, monkeypatch):
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        with pytest.raises(RuntimeError):
            Settings(ENVIRONMENT="production", JWT_SECRET_KEY="")

    def test_development_gets_persistent_secret(self, monkeypatch, tmp_path):
        from app.core import config as config_module

        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        monkeypatch.setattr(
            config_module, "_DEV_SECRET_FILE", tmp_path / ".jwt_secret"
        )
        first = Settings(ENVIRONMENT="development")
        second = Settings(ENVIRONMENT="development")
        assert first.JWT_SECRET_KEY
        assert first.JWT_SECRET_KEY == second.JWT_SECRET_KEY
        assert (tmp_path / ".jwt_secret").exists()

    def test_anonymous_access_defaults(self):
        assert Settings(ENVIRONMENT="development").allow_anonymous_access is True
        assert (
            Settings(
                ENVIRONMENT="production", JWT_SECRET_KEY="x" * 32
            ).allow_anonymous_access
            is False
        )
        assert (
            Settings(
                ENVIRONMENT="production",
                JWT_SECRET_KEY="x" * 32,
                ALLOW_ANONYMOUS_ACCESS=True,
            ).allow_anonymous_access
            is True
        )
