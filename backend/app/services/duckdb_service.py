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
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)


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
            # Sanitize filename for SQL table name
            table_name = path.stem.replace("-", "_").replace(" ", "_").lower()
            # Ensure it starts with a letter
            if table_name[0].isdigit():
                table_name = f"t_{table_name}"

        suffix = path.suffix.lower()
        try:
            if suffix == ".csv":
                self.conn.execute(
                    f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_csv_auto(?)",
                    [str(path)],
                )
            elif suffix in [".xlsx", ".xls"]:
                # DuckDB can read Excel via spatial extension or we load via pandas
                df = pd.read_excel(path)
                self.conn.execute(
                    f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df"
                )
            elif suffix == ".json":
                self.conn.execute(
                    f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_json_auto(?)",
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

    def execute_sql(self, sql: str) -> pd.DataFrame:
        """
        Execute a SQL query and return results as DataFrame.

        Args:
            sql: SQL query string

        Returns:
            Query results as pandas DataFrame
        """
        try:
            result = self.conn.execute(sql).fetchdf()
            logger.debug(f"Executed SQL: {sql[:100]}...")
            return result
        except Exception as e:
            logger.error(f"SQL execution error: {e}")
            raise

    def get_table_schema(self, table_name: str) -> list[dict[str, Any]]:
        """
        Get schema information for a table.

        Args:
            table_name: Name of the table

        Returns:
            List of column info dicts with 'name', 'type', 'nullable'
        """
        try:
            result = self.conn.execute(
                f"DESCRIBE {table_name}"
            ).fetchdf()
            return result.to_dict(orient="records")
        except Exception as e:
            logger.error(f"Failed to get schema for {table_name}: {e}")
            raise

    def get_table_sample(self, table_name: str, limit: int = 5) -> pd.DataFrame:
        """Get sample rows from a table."""
        return self.execute_sql(f"SELECT * FROM {table_name} LIMIT {limit}")

    def get_table_stats(self, table_name: str) -> dict[str, Any]:
        """Get basic statistics for a table."""
        row_count = self.conn.execute(
            f"SELECT COUNT(*) as cnt FROM {table_name}"
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
