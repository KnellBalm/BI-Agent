"""bi_agent_mcp.tools.validation 단위 테스트."""
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
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
        assert "오류" in result
        assert "unknown_conn" in result

    def test_invalid_table_name_blocked(self):
        conn_id = "conn_sqli"
        fake_connections = {conn_id: _fake_conn_info(conn_id)}
        with patch.object(_vmod, "_connections", fake_connections):
            result = validate_data(conn_id, "t; DROP TABLE t--", [])
        assert "오류" in result


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
        assert "오류" in result

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
        assert "오류" in result
