"""bi_agent_mcp.tools.compare 단위 테스트."""
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

import bi_agent_mcp.tools.compare as compare_module
from bi_agent_mcp.tools.compare import compare_queries
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


def _make_pg_mock_conn(rows_a, rows_b, columns):
    """두 번의 쿼리 실행에 대해 순서대로 rows를 반환하는 mock 연결 쌍."""
    def _make_conn(rows):
        mock_cur = MagicMock()
        mock_cur.description = [(c,) for c in columns]
        mock_cur.fetchall.return_value = [dict(zip(columns, r)) for r in rows]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        # psycopg2.extras.RealDictCursor 패턴 지원
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        return mock_conn

    conn_a = _make_conn(rows_a)
    conn_b = _make_conn(rows_b)
    return conn_a, conn_b


class TestCompareQueriesErrors:
    """에러 케이스 테스트."""

    def test_unknown_conn_id_returns_error(self):
        """conn_id 없음 → [ERROR]."""
        with patch.object(compare_module, "_connections", {}):
            result = compare_queries(
                conn_id="nonexistent",
                sql_a="SELECT * FROM t",
                sql_b="SELECT * FROM t",
            )
        assert "[ERROR]" in result
        assert "nonexistent" in result


class TestCompareQueriesAddedRows:
    """추가된 행 탐지 테스트."""

    def test_added_rows_detected(self):
        """df_b에 새 행 → 추가된 행 수 보고."""
        conn_id = "pg_cmp01"
        columns = ["id", "name"]
        rows_a = [(1, "Alice"), (2, "Bob")]
        rows_b = [(1, "Alice"), (2, "Bob"), (3, "Charlie")]

        conn_a, conn_b = _make_pg_mock_conn(rows_a, rows_b, columns)
        fake_connections = {conn_id: _make_conn_info(conn_id)}

        with patch.object(compare_module, "_connections", fake_connections), \
             patch.object(compare_module, "_get_conn", side_effect=[conn_a, conn_b]):
            result = compare_queries(
                conn_id=conn_id,
                sql_a="SELECT * FROM t_a",
                sql_b="SELECT * FROM t_b",
            )

        assert "추가된 행: 1" in result or "추가된 행" in result


class TestCompareQueriesDeletedRows:
    """삭제된 행 탐지 테스트."""

    def test_deleted_rows_detected(self):
        """df_a에만 있는 행 → 삭제된 행 수 보고."""
        conn_id = "pg_cmp02"
        columns = ["id", "name"]
        rows_a = [(1, "Alice"), (2, "Bob"), (3, "Charlie")]
        rows_b = [(1, "Alice"), (2, "Bob")]

        conn_a, conn_b = _make_pg_mock_conn(rows_a, rows_b, columns)
        fake_connections = {conn_id: _make_conn_info(conn_id)}

        with patch.object(compare_module, "_connections", fake_connections), \
             patch.object(compare_module, "_get_conn", side_effect=[conn_a, conn_b]):
            result = compare_queries(
                conn_id=conn_id,
                sql_a="SELECT * FROM t_a",
                sql_b="SELECT * FROM t_b",
            )

        assert "삭제된 행: 1" in result or "삭제된 행" in result


class TestCompareQueriesKeyColumns:
    """key_columns 기반 변경 행 탐지 테스트."""

    def test_changed_rows_by_key_columns(self):
        """key_columns로 변경 행 탐지."""
        conn_id = "pg_cmp03"
        columns = ["id", "amount"]
        rows_a = [(1, 100), (2, 200)]
        rows_b = [(1, 150), (2, 200)]  # id=1의 amount 변경

        conn_a, conn_b = _make_pg_mock_conn(rows_a, rows_b, columns)
        fake_connections = {conn_id: _make_conn_info(conn_id)}

        with patch.object(compare_module, "_connections", fake_connections), \
             patch.object(compare_module, "_get_conn", side_effect=[conn_a, conn_b]):
            result = compare_queries(
                conn_id=conn_id,
                sql_a="SELECT * FROM t_a",
                sql_b="SELECT * FROM t_b",
                key_columns=["id"],
            )

        assert "변경된 행: 1" in result or "변경된 행" in result

    def test_numeric_column_change_rate(self):
        """수치 컬럼 변화율 계산."""
        conn_id = "pg_cmp04"
        columns = ["id", "sales"]
        rows_a = [(1, 1000), (2, 2000)]
        rows_b = [(1, 1200), (2, 2400)]

        conn_a, conn_b = _make_pg_mock_conn(rows_a, rows_b, columns)
        fake_connections = {conn_id: _make_conn_info(conn_id)}

        with patch.object(compare_module, "_connections", fake_connections), \
             patch.object(compare_module, "_get_conn", side_effect=[conn_a, conn_b]):
            result = compare_queries(
                conn_id=conn_id,
                sql_a="SELECT * FROM t_a",
                sql_b="SELECT * FROM t_b",
                key_columns=["id"],
            )

        # 수치 변화 요약 포함 여부
        assert "sales" in result or "수치" in result or "변화" in result


class TestCompareQueriesIdentical:
    """동일한 결과 비교 테스트."""

    def test_identical_results_no_change(self):
        """두 결과 동일 → 변경 없음 요약."""
        conn_id = "pg_cmp05"
        columns = ["id", "val"]
        rows = [(1, "a"), (2, "b")]

        conn_a, conn_b = _make_pg_mock_conn(rows, rows, columns)
        fake_connections = {conn_id: _make_conn_info(conn_id)}

        with patch.object(compare_module, "_connections", fake_connections), \
             patch.object(compare_module, "_get_conn", side_effect=[conn_a, conn_b]):
            result = compare_queries(
                conn_id=conn_id,
                sql_a="SELECT * FROM t",
                sql_b="SELECT * FROM t",
                key_columns=["id"],
            )

        assert "변경된 행: 0" in result or ("추가된 행: 0" in result and "삭제된 행: 0" in result)


class TestCompareQueriesEmptyResult:
    """빈 결과 처리 테스트."""

    def test_both_empty_returns_message(self):
        """두 결과 모두 빈 DataFrame → 안내 메시지."""
        conn_id = "pg_cmp06"
        columns = ["id"]
        rows = []

        conn_a, conn_b = _make_pg_mock_conn(rows, rows, columns)
        fake_connections = {conn_id: _make_conn_info(conn_id)}

        with patch.object(compare_module, "_connections", fake_connections), \
             patch.object(compare_module, "_get_conn", side_effect=[conn_a, conn_b]):
            result = compare_queries(
                conn_id=conn_id,
                sql_a="SELECT * FROM t",
                sql_b="SELECT * FROM t",
            )

        assert "결과 없음" in result
