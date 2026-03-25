"""bi_agent_mcp.tools.cross_source 단위 테스트."""
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

import bi_agent_mcp.tools.cross_source as cs_module
from bi_agent_mcp.tools.cross_source import cross_query
from bi_agent_mcp.tools.db import ConnectionInfo


def _make_conn_info(conn_id: str) -> ConnectionInfo:
    return ConnectionInfo(
        conn_id=conn_id,
        db_type="postgresql",
        host="localhost",
        port=5432,
        database="testdb",
        user="user",
        password="pass",
    )


def _make_mock_conn(df: pd.DataFrame):
    """pd.read_sql을 mock으로 대체하기 위한 mock 연결 객체."""
    mock_conn = MagicMock()
    return mock_conn


class TestCrossQueryDbSource:
    """DB 소스 cross_query 테스트."""

    def test_db_source_postgresql_join(self):
        """DB 소스(postgresql) mock + DuckDB 인메모리 조인."""
        conn_id = "pg_cross01"
        df_orders = pd.DataFrame({"order_id": [1, 2], "product_id": [10, 20], "amount": [100, 200]})

        fake_connections = {conn_id: _make_conn_info(conn_id)}
        mock_conn = MagicMock()

        sources = [{"type": "db", "conn_id": conn_id, "table": "orders", "alias": "orders"}]
        sql = "SELECT order_id, amount FROM orders"

        with patch.object(cs_module, "_connections", fake_connections), \
             patch.object(cs_module, "_get_conn", return_value=mock_conn), \
             patch("pandas.read_sql", return_value=df_orders):
            result = cross_query(sources, sql)

        assert "[ERROR]" not in result
        assert "order_id" in result or "2건" in result or "건 반환" in result

    def test_file_source_join(self):
        """파일 소스 mock + DuckDB 인메모리 조인."""
        file_id = "excel_cross01"
        df_products = pd.DataFrame({"product_id": [10, 20], "name": ["A", "B"]})

        fake_files = {file_id: {"df": df_products}}

        sources = [{"type": "file", "file_id": file_id, "alias": "products"}]
        sql = "SELECT product_id, name FROM products"

        with patch.object(cs_module, "_files", fake_files):
            result = cross_query(sources, sql)

        assert "[ERROR]" not in result
        assert "건 반환" in result


class TestCrossQueryErrors:
    """cross_query 에러 케이스 테스트."""

    def test_db_source_missing_conn_id(self):
        """DB 소스에 conn_id 없음 → [ERROR]."""
        sources = [{"type": "db", "table": "orders", "alias": "orders"}]
        result = cross_query(sources, "SELECT * FROM orders")
        assert "[ERROR]" in result
        assert "conn_id" in result

    def test_file_source_missing_file_id(self):
        """파일 소스에 file_id 없음 → [ERROR]."""
        sources = [{"type": "file", "alias": "products"}]
        result = cross_query(sources, "SELECT * FROM products")
        assert "[ERROR]" in result
        assert "file_id" in result

    def test_select_only_validation_insert_rejected(self):
        """INSERT SQL 시도 → [ERROR] (SELECT-only 검증)."""
        sources = [{"type": "file", "file_id": "some_file", "alias": "t"}]
        result = cross_query(sources, "INSERT INTO t VALUES (1)")
        assert "[ERROR]" in result

    def test_db_conn_id_not_found(self):
        """등록되지 않은 conn_id → [ERROR]."""
        sources = [{"type": "db", "conn_id": "nonexistent", "table": "orders", "alias": "orders"}]
        with patch.object(cs_module, "_connections", {}):
            result = cross_query(sources, "SELECT * FROM orders")
        assert "[ERROR]" in result
        assert "nonexistent" in result

    def test_file_id_not_found(self):
        """등록되지 않은 file_id → [ERROR]."""
        sources = [{"type": "file", "file_id": "nonexistent_file", "alias": "products"}]
        with patch.object(cs_module, "_files", {}):
            result = cross_query(sources, "SELECT * FROM products")
        assert "[ERROR]" in result
        assert "nonexistent_file" in result


class TestCrossQueryEmptyResult:
    """빈 결과 처리 테스트."""

    def test_empty_result_returns_no_result_message(self):
        """쿼리 결과가 빈 DataFrame → '결과 없음' 반환."""
        file_id = "empty_file"
        df_empty = pd.DataFrame({"id": pd.Series([], dtype=int), "val": pd.Series([], dtype=str)})

        fake_files = {file_id: {"df": df_empty}}
        sources = [{"type": "file", "file_id": file_id, "alias": "t"}]
        sql = "SELECT id, val FROM t WHERE 1=0"

        with patch.object(cs_module, "_files", fake_files):
            result = cross_query(sources, sql)

        assert "결과 없음" in result
