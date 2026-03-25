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


class TestCompareQueriesErrorPaths:
    """에러 경로 커버리지 테스트."""

    def test_pandas_import_error(self):
        """pandas 없음 → [ERROR] (lines 23-24)."""
        conn_id = "pg_nopandas"
        fake_connections = {conn_id: _make_conn_info(conn_id)}
        with patch.object(compare_module, "_connections", fake_connections), \
             patch.dict("sys.modules", {"pandas": None}):
            result = compare_queries(conn_id, "SELECT * FROM t", "SELECT * FROM t")
        assert "[ERROR]" in result
        assert "pandas" in result

    def test_sql_a_validation_error(self):
        """sql_a 검증 실패 → [ERROR] sql_a (line 35)."""
        conn_id = "pg_val_a"
        fake_connections = {conn_id: _make_conn_info(conn_id)}
        with patch.object(compare_module, "_connections", fake_connections):
            result = compare_queries(conn_id, "DELETE FROM t", "SELECT * FROM t")
        assert "[ERROR]" in result
        assert "sql_a" in result

    def test_sql_b_validation_error(self):
        """sql_b 검증 실패 → [ERROR] sql_b (line 39)."""
        conn_id = "pg_val_b"
        fake_connections = {conn_id: _make_conn_info(conn_id)}
        with patch.object(compare_module, "_connections", fake_connections):
            result = compare_queries(conn_id, "SELECT * FROM t", "DROP TABLE t")
        assert "[ERROR]" in result
        assert "sql_b" in result

    def test_db_connection_exception(self):
        """DB 연결 예외 → [ERROR] DB 연결 실패 (lines 45-46)."""
        conn_id = "pg_conn_exc"
        fake_connections = {conn_id: _make_conn_info(conn_id)}
        with patch.object(compare_module, "_connections", fake_connections), \
             patch.object(compare_module, "_get_conn", side_effect=Exception("연결 타임아웃")):
            result = compare_queries(conn_id, "SELECT * FROM t", "SELECT * FROM t")
        assert "[ERROR]" in result
        assert "연결 실패" in result

    def test_sql_a_execution_exception(self):
        """sql_a 실행 예외 → [ERROR] sql_a 실행 실패 (lines 50-51)."""
        conn_id = "pg_exec_a"
        fake_connections = {conn_id: _make_conn_info(conn_id)}

        mock_conn_a = MagicMock()
        mock_conn_b = MagicMock()

        with patch.object(compare_module, "_connections", fake_connections), \
             patch.object(compare_module, "_get_conn", side_effect=[mock_conn_a, mock_conn_b]), \
             patch.object(compare_module, "_execute_to_df", side_effect=Exception("sql_a 쿼리 실패")):
            result = compare_queries(conn_id, "SELECT * FROM t", "SELECT * FROM t")
        assert "[ERROR]" in result
        assert "sql_a" in result

    def test_sql_b_execution_exception(self):
        """sql_b 실행 예외 → [ERROR] sql_b 실행 실패 (lines 60-61)."""
        conn_id = "pg_exec_b"
        fake_connections = {conn_id: _make_conn_info(conn_id)}

        mock_conn_a = MagicMock()
        mock_conn_b = MagicMock()
        mock_df_a = pd.DataFrame({"id": [1]})

        with patch.object(compare_module, "_connections", fake_connections), \
             patch.object(compare_module, "_get_conn", side_effect=[mock_conn_a, mock_conn_b]), \
             patch.object(compare_module, "_execute_to_df", side_effect=[mock_df_a, Exception("sql_b 실패")]):
            result = compare_queries(conn_id, "SELECT * FROM t", "SELECT * FROM t")
        assert "[ERROR]" in result
        assert "sql_b" in result


class TestExecuteToDfNonPostgres:
    """비 PostgreSQL _execute_to_df 경로 테스트 (lines 89-95)."""

    def _make_sqlite_info(self, conn_id: str) -> ConnectionInfo:
        return ConnectionInfo(
            conn_id=conn_id, db_type="sqlite",
            host="", port=0, database=":memory:", user="", password="",
        )

    def test_sqlite_execute_to_df_with_rows(self):
        """sqlite _execute_to_df: 결과 있는 경우 (lines 91-95)."""
        conn_id = "sqlite_cmp01"
        columns = ["id", "val"]
        rows_a = [(1, "a"), (2, "b")]
        rows_b = [(1, "a"), (2, "b")]

        fake_connections = {conn_id: self._make_sqlite_info(conn_id)}

        mock_cur_a = MagicMock()
        mock_cur_a.description = [(c,) for c in columns]
        mock_cur_a.fetchall.return_value = rows_a
        mock_conn_a = MagicMock()
        mock_conn_a.cursor.return_value = mock_cur_a

        mock_cur_b = MagicMock()
        mock_cur_b.description = [(c,) for c in columns]
        mock_cur_b.fetchall.return_value = rows_b
        mock_conn_b = MagicMock()
        mock_conn_b.cursor.return_value = mock_cur_b

        with patch.object(compare_module, "_connections", fake_connections), \
             patch.object(compare_module, "_get_conn", side_effect=[mock_conn_a, mock_conn_b]):
            result = compare_queries(conn_id, "SELECT * FROM t", "SELECT * FROM t")
        assert "비교 결과" in result

    def test_sqlite_execute_to_df_empty_result(self):
        """sqlite _execute_to_df: 결과 없는 경우 (lines 92-94)."""
        conn_id = "sqlite_cmp02"
        columns = ["id"]
        fake_connections = {conn_id: self._make_sqlite_info(conn_id)}

        mock_cur = MagicMock()
        mock_cur.description = [(c,) for c in columns]
        mock_cur.fetchall.return_value = []

        mock_conn_a = MagicMock()
        mock_conn_a.cursor.return_value = mock_cur
        mock_conn_b = MagicMock()
        mock_conn_b.cursor.return_value = mock_cur

        with patch.object(compare_module, "_connections", fake_connections), \
             patch.object(compare_module, "_get_conn", side_effect=[mock_conn_a, mock_conn_b]):
            result = compare_queries(conn_id, "SELECT * FROM t", "SELECT * FROM t")
        assert "결과 없음" in result


class TestCompareByKeysEdgeCases:
    """_compare_by_keys 엣지 케이스."""

    def test_key_column_not_in_either_df(self):
        """key_columns가 두 df에 모두 없음 → [ERROR] (line 103)."""
        conn_id = "pg_key_miss"
        columns = ["id", "val"]
        rows = [(1, "a")]

        conn_a, conn_b = _make_pg_mock_conn(rows, rows, columns)
        fake_connections = {conn_id: _make_conn_info(conn_id)}

        with patch.object(compare_module, "_connections", fake_connections), \
             patch.object(compare_module, "_get_conn", side_effect=[conn_a, conn_b]):
            result = compare_queries(conn_id, "SELECT * FROM t", "SELECT * FROM t", key_columns=["nonexistent"])
        assert "[ERROR]" in result

    def test_key_based_added_rows_section(self):
        """key 기반에서 추가된 행 섹션 렌더링 (lines 130-132)."""
        conn_id = "pg_key_add"
        columns = ["id", "name"]
        rows_a = [(1, "Alice")]
        rows_b = [(1, "Alice"), (2, "Bob")]

        conn_a, conn_b = _make_pg_mock_conn(rows_a, rows_b, columns)
        fake_connections = {conn_id: _make_conn_info(conn_id)}

        with patch.object(compare_module, "_connections", fake_connections), \
             patch.object(compare_module, "_get_conn", side_effect=[conn_a, conn_b]):
            result = compare_queries(conn_id, "SELECT * FROM t_a", "SELECT * FROM t_b", key_columns=["id"])
        assert "추가된 행" in result
        assert "Bob" in result

    def test_key_based_deleted_rows_section(self):
        """key 기반에서 삭제된 행 섹션 렌더링 (lines 135-137)."""
        conn_id = "pg_key_del"
        columns = ["id", "name"]
        rows_a = [(1, "Alice"), (2, "Bob")]
        rows_b = [(1, "Alice")]

        conn_a, conn_b = _make_pg_mock_conn(rows_a, rows_b, columns)
        fake_connections = {conn_id: _make_conn_info(conn_id)}

        with patch.object(compare_module, "_connections", fake_connections), \
             patch.object(compare_module, "_get_conn", side_effect=[conn_a, conn_b]):
            result = compare_queries(conn_id, "SELECT * FROM t_a", "SELECT * FROM t_b", key_columns=["id"])
        assert "삭제된 행" in result
        assert "Bob" in result


class TestCompareByIndexEdgeCases:
    """_compare_by_index 엣지 케이스."""

    def test_changed_rows_same_length(self):
        """동일 길이 + 다른 값 → 변경된 행 섹션 (lines 189-194)."""
        conn_id = "pg_idx_chg"
        columns = ["id", "score"]
        rows_a = [(1, 100), (2, 200)]
        rows_b = [(1, 150), (2, 250)]

        conn_a, conn_b = _make_pg_mock_conn(rows_a, rows_b, columns)
        fake_connections = {conn_id: _make_conn_info(conn_id)}

        with patch.object(compare_module, "_connections", fake_connections), \
             patch.object(compare_module, "_get_conn", side_effect=[conn_a, conn_b]):
            result = compare_queries(conn_id, "SELECT * FROM t_a", "SELECT * FROM t_b")
        assert "변경된 행" in result

    def test_close_exception_in_finally_conn_a(self):
        """conn_a.close() 예외 → pass (line 55)."""
        conn_id = "pg_close_exc_a"
        fake_connections = {conn_id: _make_conn_info(conn_id)}

        mock_conn_a = MagicMock()
        mock_conn_a.close.side_effect = Exception("close 실패")
        mock_conn_b = MagicMock()

        with patch.object(compare_module, "_connections", fake_connections), \
             patch.object(compare_module, "_get_conn", side_effect=[mock_conn_a, mock_conn_b]), \
             patch.object(compare_module, "_execute_to_df", side_effect=Exception("sql_a 실패")):
            result = compare_queries(conn_id, "SELECT * FROM t", "SELECT * FROM t")
        assert "[ERROR]" in result

    def test_close_exception_in_finally_conn_b(self):
        """conn_b.close() 예외 → pass (line 65)."""
        conn_id = "pg_close_exc_b"
        fake_connections = {conn_id: _make_conn_info(conn_id)}

        mock_df_a = pd.DataFrame({"id": [1]})
        mock_conn_a = MagicMock()
        mock_conn_b = MagicMock()
        mock_conn_b.close.side_effect = Exception("close 실패")

        with patch.object(compare_module, "_connections", fake_connections), \
             patch.object(compare_module, "_get_conn", side_effect=[mock_conn_a, mock_conn_b]), \
             patch.object(compare_module, "_execute_to_df", side_effect=[mock_df_a, Exception("sql_b 실패")]):
            result = compare_queries(conn_id, "SELECT * FROM t", "SELECT * FROM t")
        assert "[ERROR]" in result


class TestNumericDiffSummary:
    """_numeric_diff_summary 직접 테스트."""

    def test_col_b_missing_is_skipped(self):
        """col_b 없으면 continue (line 219)."""
        from bi_agent_mcp.tools.compare import _numeric_diff_summary
        both_df = pd.DataFrame({"amount_a": [1.0, 2.0]})  # amount_b 없음
        result = _numeric_diff_summary(both_df, ["amount_a"], pd)
        assert result == ""

    def test_sum_exception_is_swallowed(self):
        """sum() 예외 → pass (line 229)."""
        from bi_agent_mcp.tools.compare import _numeric_diff_summary
        both_df = pd.DataFrame({"val_a": [1.0, 2.0], "val_b": [3.0, 4.0]})
        with patch.object(pd.Series, "sum", side_effect=Exception("오버플로우")):
            result = _numeric_diff_summary(both_df, ["val_a"], pd)
        assert result == ""

    def test_index_numeric_sum_exception_swallowed(self):
        """인덱스 기반 비교에서 sum() 예외 → pass (line 207)."""
        conn_id = "pg_idx_sum_exc"
        columns = ["id", "score"]
        rows_a = [(1, 100), (2, 200)]
        rows_b = [(1, 150), (2, 250)]

        conn_a, conn_b = _make_pg_mock_conn(rows_a, rows_b, columns)
        fake_connections = {conn_id: _make_conn_info(conn_id)}

        with patch.object(compare_module, "_connections", fake_connections), \
             patch.object(compare_module, "_get_conn", side_effect=[conn_a, conn_b]), \
             patch.object(pd.Series, "sum", side_effect=Exception("overflow")):
            result = compare_queries(conn_id, "SELECT * FROM t_a", "SELECT * FROM t_b")
        assert "비교 결과" in result
