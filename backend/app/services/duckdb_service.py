"""
DuckDB Service for efficient SQL-based data analysis.

This module provides a DuckDB-powered query engine for executing SQL queries
on local data files (CSV, Excel, JSON). It offers superior performance for
analytical queries compared to pure Pandas operations.

Features:
- Load local files into DuckDB tables
- Execute SQL queries with parameterized safety
- Natural language to SQL conversion
- Schema introspection
"""

import logging
import re
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)

# DuckDB 識別字（表名/欄名）只允許英數與底線；
# 檔名可能含 `;`、`(`、空白等字元，直接內插會造成 SQL injection。
_IDENTIFIER_UNSAFE = re.compile(r"[^0-9A-Za-z_]")

# 使用者／LLM 提供的 SQL 只允許讀取，禁止 DDL、檔案存取與多語句
_FORBIDDEN_SQL_KEYWORDS = re.compile(
    r"\b(attach|detach|copy|install|load|pragma|create|drop|alter|insert|update|"
    r"delete|truncate|export|import|call|set|reset|vacuum|begin|commit|rollback)\b",
    re.IGNORECASE,
)


def sanitize_identifier(name: str) -> str:
    """把任意字串轉成安全的 SQL 識別字。

    `my data;DROP TABLE x` → `my_data_DROP_TABLE_x`
    """
    cleaned = _IDENTIFIER_UNSAFE.sub("_", name).strip("_")
    if not cleaned:
        cleaned = "table"
    if cleaned[0].isdigit():
        cleaned = f"t_{cleaned}"
    return cleaned


def quote_identifier(name: str) -> str:
    """以雙引號包裹（已 sanitize 的）識別字。"""
    return f'"{sanitize_identifier(name)}"'



class DuckDBService:
    """Service for DuckDB-based data operations."""

    def __init__(self) -> None:
        """Initialize DuckDB service with in-memory database."""
        self._conn: duckdb.DuckDBPyConnection | None = None
        self._loaded_tables: dict[str, str] = {}  # table_name -> file_path

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        """Get or create DuckDB connection (lazy initialization)."""
        if self._conn is None:
            self._conn = duckdb.connect(":memory:")
            logger.info("Initialized in-memory DuckDB connection")
        return self._conn

    def load_file(self, file_path: str, table_name: str | None = None) -> str:
        """
        Load a file into DuckDB as a table.

        Args:
            file_path: Path to the data file (CSV, Excel, JSON)
            table_name: Optional table name, defaults to sanitized filename

        Returns:
            The table name used

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is unsupported
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Generate table name from filename if not provided
        if table_name is None:
            table_name = sanitize_identifier(path.stem)
        else:
            # 即使是呼叫端提供的表名也一律 sanitize，避免 SQL injection
            table_name = sanitize_identifier(table_name)

        identifier = quote_identifier(table_name)
        suffix = path.suffix.lower()
        try:
            if suffix == ".csv":
                self.conn.execute(
                    f"CREATE OR REPLACE TABLE {identifier} "
                    f"AS SELECT * FROM read_csv_auto(?)",
                    [str(path)],
                )
            elif suffix in [".xlsx", ".xls"]:
                # DuckDB can read Excel via spatial extension or we load via pandas
                df = pd.read_excel(path)
                self.conn.register("_excel_df", df)
                try:
                    self.conn.execute(
                        f"CREATE OR REPLACE TABLE {identifier} AS SELECT * FROM _excel_df"
                    )
                finally:
                    self.conn.unregister("_excel_df")
            elif suffix == ".json":
                self.conn.execute(
                    f"CREATE OR REPLACE TABLE {identifier} "
                    f"AS SELECT * FROM read_json_auto(?)",
                    [str(path)],
                )
            else:
                raise ValueError(f"Unsupported file format: {suffix}")

            self._loaded_tables[table_name] = str(path)
            logger.info(f"Loaded {file_path} as table '{table_name}'")
            return table_name

        except Exception as e:
            logger.error(f"Failed to load {file_path}: {e}")
            raise

    def execute_sql(self, sql: str, *, read_only: bool = True) -> pd.DataFrame:
        """
        Execute a SQL query and return results as DataFrame.

        Args:
            sql: SQL query string
            read_only: 拒絕 DDL/DML、檔案存取與多語句（預設 True）。
                只有在內部已知安全的載入流程才應設為 False。

        Returns:
            Query results as pandas DataFrame
        """
        if read_only:
            self._assert_read_only_sql(sql)
        try:
            result = self.conn.execute(sql).fetchdf()
            logger.debug(f"Executed SQL: {sql[:100]}...")
            return result
        except Exception as e:
            logger.error(f"SQL execution error: {e}")
            raise

    @staticmethod
    def _assert_read_only_sql(sql: str) -> None:
        """粗略阻擋會改寫資料或存取檔案的 SQL。

        DuckDB 允許 `COPY ... TO`、`read_csv('/etc/passwd')`、`ATTACH` 等，
        對外開放的端點不能讓使用者直接送出這些語句。
        """
        if not sql or not sql.strip():
            raise ValueError("SQL 不可為空")
        # 多語句（`;` 分隔）一律拒絕
        if ";" in sql.rstrip().rstrip(";"):
            raise ValueError("不允許多個 SQL 語句")
        if _FORBIDDEN_SQL_KEYWORDS.search(sql):
            raise ValueError("查詢包含不允許的 SQL 關鍵字")
        if "read_" in sql.lower() or "glob(" in sql.lower():
            raise ValueError("查詢不可直接存取外部檔案")


    def get_table_schema(self, table_name: str) -> list[dict[str, Any]]:
        """
        Get schema information for a table.

        Args:
            table_name: Name of the table

        Returns:
            List of column info dicts with 'name', 'type', 'nullable'
        """
        try:
            result = self.conn.execute(f"DESCRIBE {quote_identifier(table_name)}").fetchdf()
            return result.to_dict(orient="records")
        except Exception as e:
            logger.error(f"Failed to get schema for {table_name}: {e}")
            raise

    def get_table_sample(self, table_name: str, limit: int = 5) -> pd.DataFrame:
        """Get sample rows from a table."""
        safe_limit = max(1, min(int(limit), 1000))
        return self.execute_sql(
            f"SELECT * FROM {quote_identifier(table_name)} LIMIT {safe_limit}",
            read_only=False,
        )

    def get_table_stats(self, table_name: str) -> dict[str, Any]:
        """Get basic statistics for a table."""
        row_count = self.conn.execute(
            f"SELECT COUNT(*) as cnt FROM {quote_identifier(table_name)}"
        ).fetchone()[0]

        schema = self.get_table_schema(table_name)

        return {
            "table_name": table_name,
            "row_count": row_count,
            "column_count": len(schema),
            "columns": schema,
        }

    def list_tables(self) -> list[str]:
        """List all loaded tables."""
        result = self.conn.execute("SHOW TABLES").fetchdf()
        return result["name"].tolist() if not result.empty else []

    def generate_schema_description(self, table_name: str) -> str:
        """
        Generate a human-readable schema description for LLM prompts.

        Args:
            table_name: Name of the table

        Returns:
            Formatted schema description string
        """
        stats = self.get_table_stats(table_name)
        sample = self.get_table_sample(table_name, 3)

        lines = [
            f"Table: {table_name}",
            f"Rows: {stats['row_count']}",
            f"Columns ({stats['column_count']}):",
        ]

        for col in stats["columns"]:
            lines.append(f"  - {col['column_name']}: {col['column_type']}")

        lines.append("\nSample Data:")
        lines.append(sample.to_markdown(index=False))

        return "\n".join(lines)

    def close(self) -> None:
        """Close the DuckDB connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            self._loaded_tables.clear()
            logger.info("Closed DuckDB connection")


# Singleton instance
duckdb_service = DuckDBService()
