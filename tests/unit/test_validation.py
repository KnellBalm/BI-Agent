"""bi_agent_mcp.tools.validation 단위 테스트."""
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import pytest

import bi_agent_mcp.tools.validation as _vmod
from bi_agent_mcp.tools.validation import validate_data, validate_query_result
from bi_agent_mcp.tools.db import ConnectionInfo


def _fake_conn_info(conn_id: str) -> ConnectionInfo:
    return ConnectionInfo(
        conn_id=conn_id,
        db_type="postgresql",
        host="localhost",
        port=5432,
        database="testdb",
        user="user",
        password="pass",
    )


def _patch_fetch(conn_id: str, columns: list, rows: list):
    """_connections에 conn_id를 등록하고 _fetch_rows를 mock으로 교체하는 context manager 반환."""
    from contextlib import contextmanager

    @contextmanager
    def _ctx():
        fake_connections = {conn_id: _fake_conn_info(conn_id)}
        with patch.object(_vmod, "_connections", fake_connections), \
             patch.object(_vmod, "_fetch_rows", return_value=(None, columns, rows)):
            yield

    return _ctx()


# ─── validate_data: conn_id 없을 때 ─────────────────────────────────────────

class TestValidateDataConnId:
    def test_unknown_conn_id_returns_error(self):
        with patch.object(_vmod, "_connections", {}):
            result = validate_data("unknown_conn", "some_table", [])
        assert "[ERROR]" in result
        assert "unknown_conn" in result

    def test_invalid_table_name_blocked(self):
        conn_id = "conn_sqli"
        fake_connections = {conn_id: _fake_conn_info(conn_id)}
        with patch.object(_vmod, "_connections", fake_connections):
            result = validate_data(conn_id, "t; DROP TABLE t--", [])
        assert "[ERROR]" in result


# ─── not_null ────────────────────────────────────────────────────────────────

class TestValidateDataNotNull:
    def test_not_null_with_nulls_fails(self):
        conn_id = "conn_nn"
        columns = ["id", "val"]
        rows = [(1, "a"), (2, None)]
        with _patch_fetch(conn_id, columns, rows):
            result = validate_data(conn_id, "t", [{"column": "val", "check": "not_null"}])
        assert "FAIL" in result

    def test_not_null_without_nulls_passes(self):
        conn_id = "conn_nn2"
        columns = ["id", "val"]
        rows = [(1, "a"), (2, "b")]
        with _patch_fetch(conn_id, columns, rows):
            result = validate_data(conn_id, "t", [{"column": "val", "check": "not_null"}])
        assert "PASS" in result


# ─── range ───────────────────────────────────────────────────────────────────

class TestValidateDataRange:
    def test_range_violation_fails(self):
        conn_id = "conn_range"
        columns = ["age"]
        rows = [(25,), (200,)]
        with _patch_fetch(conn_id, columns, rows):
            result = validate_data(conn_id, "t", [{"column": "age", "check": "range", "min": 0, "max": 150}])
        assert "FAIL" in result

    def test_range_all_valid_passes(self):
        conn_id = "conn_range2"
        columns = ["age"]
        rows = [(25,), (30,)]
        with _patch_fetch(conn_id, columns, rows):
            result = validate_data(conn_id, "t", [{"column": "age", "check": "range", "min": 0, "max": 150}])
        assert "PASS" in result


# ─── regex ───────────────────────────────────────────────────────────────────

class TestValidateDataRegex:
    def test_regex_mismatch_fails(self):
        conn_id = "conn_regex"
        columns = ["email"]
        rows = [("user@example.com",), ("not-an-email",)]
        with _patch_fetch(conn_id, columns, rows):
            result = validate_data(conn_id, "t", [{"column": "email", "check": "regex", "pattern": r".*@.*"}])
        assert "FAIL" in result

    def test_regex_all_match_passes(self):
        conn_id = "conn_regex2"
        columns = ["email"]
        rows = [("a@b.com",), ("x@y.org",)]
        with _patch_fetch(conn_id, columns, rows):
            result = validate_data(conn_id, "t", [{"column": "email", "check": "regex", "pattern": r".*@.*"}])
        assert "PASS" in result


# ─── enum ────────────────────────────────────────────────────────────────────

class TestValidateDataEnum:
    def test_enum_invalid_value_fails(self):
        conn_id = "conn_enum"
        columns = ["status"]
        rows = [("active",), ("deleted",)]
        with _patch_fetch(conn_id, columns, rows):
            result = validate_data(conn_id, "t", [{"column": "status", "check": "enum", "values": ["active", "inactive"]}])
        assert "FAIL" in result

    def test_enum_all_valid_passes(self):
        conn_id = "conn_enum2"
        columns = ["status"]
        rows = [("active",), ("inactive",)]
        with _patch_fetch(conn_id, columns, rows):
            result = validate_data(conn_id, "t", [{"column": "status", "check": "enum", "values": ["active", "inactive"]}])
        assert "PASS" in result


# ─── unique ──────────────────────────────────────────────────────────────────

class TestValidateDataUnique:
    def test_unique_duplicates_fails(self):
        conn_id = "conn_uniq"
        columns = ["id"]
        rows = [(1,), (1,), (2,)]
        with _patch_fetch(conn_id, columns, rows):
            result = validate_data(conn_id, "t", [{"column": "id", "check": "unique"}])
        assert "FAIL" in result

    def test_unique_no_duplicates_passes(self):
        conn_id = "conn_uniq2"
        columns = ["id"]
        rows = [(1,), (2,), (3,)]
        with _patch_fetch(conn_id, columns, rows):
            result = validate_data(conn_id, "t", [{"column": "id", "check": "unique"}])
        assert "PASS" in result


# ─── freshness ───────────────────────────────────────────────────────────────

class TestValidateDataFreshness:
    def test_freshness_old_timestamp_fails(self):
        conn_id = "conn_fresh"
        columns = ["created_at"]
        old_ts = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        rows = [(old_ts,)]
        with _patch_fetch(conn_id, columns, rows):
            result = validate_data(conn_id, "t", [{"column": "created_at", "check": "freshness", "max_age_hours": 24}])
        assert "FAIL" in result

    def test_freshness_recent_timestamp_passes(self):
        conn_id = "conn_fresh2"
        columns = ["created_at"]
        recent_ts = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        rows = [(recent_ts,)]
        with _patch_fetch(conn_id, columns, rows):
            result = validate_data(conn_id, "t", [{"column": "created_at", "check": "freshness", "max_age_hours": 24}])
        assert "PASS" in result


# ─── 빈 rules ────────────────────────────────────────────────────────────────

class TestValidateDataEmptyRules:
    def test_empty_rules_returns_header(self):
        conn_id = "conn_empty"
        columns = ["id"]
        rows = [(1,)]
        with _patch_fetch(conn_id, columns, rows):
            result = validate_data(conn_id, "t", [])
        assert "검증 결과" in result


# ─── validate_query_result ───────────────────────────────────────────────────

class TestValidateQueryResult:
    def test_unknown_conn_id_returns_error(self):
        with patch.object(_vmod, "_connections", {}):
            result = validate_query_result("no_conn", "SELECT 1", [])
        assert "[ERROR]" in result

    def test_sql_result_rules_applied_fail(self):
        conn_id = "conn_qr"
        columns = ["amount"]
        rows = [(100,), (-5,)]
        fake_connections = {conn_id: _fake_conn_info(conn_id)}
        with patch.object(_vmod, "_connections", fake_connections), \
             patch.object(_vmod, "_fetch_rows", return_value=(None, columns, rows)):
            result = validate_query_result(
                conn_id,
                "SELECT amount FROM orders",
                [{"column": "amount", "check": "range", "min": 0, "max": 10000}],
            )
        assert "FAIL" in result

    def test_sql_result_rules_applied_pass(self):
        conn_id = "conn_qr2"
        columns = ["amount"]
        rows = [(100,), (200,)]
        fake_connections = {conn_id: _fake_conn_info(conn_id)}
        with patch.object(_vmod, "_connections", fake_connections), \
             patch.object(_vmod, "_fetch_rows", return_value=(None, columns, rows)):
            result = validate_query_result(
                conn_id,
                "SELECT amount FROM orders",
                [{"column": "amount", "check": "range", "min": 0, "max": 10000}],
            )
        assert "PASS" in result

    def test_fetch_error_returns_error(self):
        conn_id = "conn_qr_err"
        fake_connections = {conn_id: _fake_conn_info(conn_id)}
        with patch.object(_vmod, "_connections", fake_connections), \
             patch.object(_vmod, "_fetch_rows", return_value=("DB 오류 발생", None, None)):
            result = validate_query_result(conn_id, "SELECT 1", [])
        assert "[ERROR]" in result


# ─── _fetch_rows 직접 테스트 ─────────────────────────────────────────────────

class TestFetchRowsDirect:
    """_fetch_rows 함수 직접 테스트 (lines 12-26)."""

    def test_unknown_conn_id_returns_error(self):
        """conn_id 없음 → error 문자열 반환."""
        from bi_agent_mcp.tools.validation import _fetch_rows
        with patch.object(_vmod, "_connections", {}):
            err, cols, rows = _fetch_rows("no_conn", "SELECT 1")
        assert err is not None
        assert "no_conn" in err
        assert cols is None
        assert rows is None

    def test_successful_execution(self):
        """정상 실행 → (None, columns, rows) 반환."""
        from bi_agent_mcp.tools.validation import _fetch_rows
        conn_id = "conn_fetch_ok"
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = [(1, "a"), (2, "b")]
        mock_cur.description = [("id",), ("name",)]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        fake_connections = {conn_id: _fake_conn_info(conn_id)}
        with patch.object(_vmod, "_connections", fake_connections), \
             patch.object(_vmod, "_get_conn", return_value=mock_conn):
            err, cols, rows = _fetch_rows(conn_id, "SELECT id, name FROM t")
        assert err is None
        assert cols == ["id", "name"]
        assert len(rows) == 2

    def test_execution_exception_returns_error(self):
        """실행 중 예외 → error 문자열 반환 (lines 25-26)."""
        from bi_agent_mcp.tools.validation import _fetch_rows
        conn_id = "conn_fetch_exc"
        mock_conn = MagicMock()
        mock_conn.cursor.side_effect = Exception("쿼리 오류")

        fake_connections = {conn_id: _fake_conn_info(conn_id)}
        with patch.object(_vmod, "_connections", fake_connections), \
             patch.object(_vmod, "_get_conn", return_value=mock_conn):
            err, cols, rows = _fetch_rows(conn_id, "SELECT 1")
        assert err == "쿼리 오류"
        assert cols is None


# ─── _apply_rules 엣지 케이스 ─────────────────────────────────────────────────

class TestApplyRulesEdgeCases:
    """_apply_rules 미커버 케이스."""

    def test_unknown_column_skip(self):
        """존재하지 않는 컬럼 → SKIP (lines 43-44)."""
        conn_id = "conn_skip_col"
        columns = ["id"]
        rows = [(1,)]
        with _patch_fetch(conn_id, columns, rows):
            result = validate_data(conn_id, "t", [{"column": "nonexistent", "check": "not_null"}])
        assert "SKIP" in result
        assert "컬럼 없음" in result

    def test_unknown_check_type_skip(self):
        """알 수 없는 check 타입 → SKIP (lines 117-118)."""
        conn_id = "conn_skip_check"
        columns = ["val"]
        rows = [(1,)]
        with _patch_fetch(conn_id, columns, rows):
            result = validate_data(conn_id, "t", [{"column": "val", "check": "unknown_check"}])
        assert "SKIP" in result

    def test_range_with_none_value_skipped(self):
        """range 체크에서 None 값 → skip (line 61)."""
        conn_id = "conn_range_none"
        columns = ["age"]
        rows = [(None,), (25,)]
        with _patch_fetch(conn_id, columns, rows):
            result = validate_data(conn_id, "t", [{"column": "age", "check": "range", "min": 0, "max": 150}])
        assert "PASS" in result  # None은 skip, 25는 유효

    def test_range_with_non_numeric_value(self):
        """range 체크에서 비수치 값 → 위반 (lines 66-67)."""
        conn_id = "conn_range_str"
        columns = ["age"]
        rows = [("not_a_number",)]
        with _patch_fetch(conn_id, columns, rows):
            result = validate_data(conn_id, "t", [{"column": "age", "check": "range", "min": 0, "max": 150}])
        assert "FAIL" in result

    def test_regex_with_none_value(self):
        """regex 체크에서 None 값 → 위반 (line 75)."""
        conn_id = "conn_regex_none"
        columns = ["email"]
        rows = [(None,)]
        with _patch_fetch(conn_id, columns, rows):
            result = validate_data(conn_id, "t", [{"column": "email", "check": "regex", "pattern": r".*@.*"}])
        assert "FAIL" in result

    def test_freshness_with_none_value(self):
        """freshness 체크에서 None 값 → 위반 (lines 92-93)."""
        conn_id = "conn_fresh_none"
        columns = ["created_at"]
        rows = [(None,)]
        with _patch_fetch(conn_id, columns, rows):
            result = validate_data(conn_id, "t", [{"column": "created_at", "check": "freshness", "max_age_hours": 24}])
        assert "FAIL" in result

    def test_freshness_with_timezone_aware_datetime(self):
        """freshness 체크: tzinfo 있는 datetime 객체 (line 96)."""
        from datetime import datetime, timezone, timedelta
        conn_id = "conn_fresh_tz"
        columns = ["created_at"]
        recent = datetime.now(timezone.utc) - timedelta(hours=1)
        rows = [(recent,)]
        with _patch_fetch(conn_id, columns, rows):
            result = validate_data(conn_id, "t", [{"column": "created_at", "check": "freshness", "max_age_hours": 24}])
        assert "PASS" in result

    def test_freshness_with_naive_isoformat(self):
        """freshness 체크: naive isoformat 문자열 (line 100)."""
        from datetime import datetime, timedelta
        conn_id = "conn_fresh_naive"
        columns = ["created_at"]
        recent = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        rows = [(recent,)]
        with _patch_fetch(conn_id, columns, rows):
            result = validate_data(conn_id, "t", [{"column": "created_at", "check": "freshness", "max_age_hours": 24}])
        assert "PASS" in result

    def test_freshness_with_invalid_value(self):
        """freshness 체크: 파싱 불가 값 → 위반 (lines 103-104)."""
        conn_id = "conn_fresh_invalid"
        columns = ["created_at"]
        rows = [("not-a-date",)]
        with _patch_fetch(conn_id, columns, rows):
            result = validate_data(conn_id, "t", [{"column": "created_at", "check": "freshness", "max_age_hours": 24}])
        assert "FAIL" in result

    def test_unique_with_none_values(self):
        """unique 체크에서 None 값 처리 (lines 110-114)."""
        conn_id = "conn_uniq_none"
        columns = ["id"]
        rows = [(None,), (None,), (1,)]
        with _patch_fetch(conn_id, columns, rows):
            result = validate_data(conn_id, "t", [{"column": "id", "check": "unique"}])
        assert "FAIL" in result  # None이 두 번 → 중복

    def test_validate_data_fetch_error(self):
        """validate_data에서 _fetch_rows 오류 반환 (line 169)."""
        conn_id = "conn_data_fetch_err"
        mock_conn = MagicMock()
        mock_conn.cursor.side_effect = Exception("DB 접속 불가")

        fake_connections = {conn_id: _fake_conn_info(conn_id)}
        with patch.object(_vmod, "_connections", fake_connections), \
             patch.object(_vmod, "_get_conn", return_value=mock_conn):
            result = validate_data(conn_id, "orders", [{"column": "id", "check": "not_null"}])
        assert "[ERROR]" in result
