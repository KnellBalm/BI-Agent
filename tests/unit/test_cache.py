"""bi_agent_mcp.tools.db 캐시 로직 단위 테스트."""
import hashlib
import time
import pytest
from unittest.mock import patch, MagicMock

import bi_agent_mcp.tools.db as db_module
from bi_agent_mcp.tools.db import (
    run_query,
    clear_cache,
    _connections,
    ConnectionInfo,
)


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


def _seed_cache(conn_id: str, sql: str, result: str = "| a |\n| 1 |"):
    key = (conn_id, hashlib.md5(sql.encode()).hexdigest())
    db_module._query_cache[key] = {
        "result": result,
        "expires": time.time() + 300,
        "hits": 0,
    }
    return key


def _make_mock_conn(rows=None):
    """mock DB 연결 + cursor 반환. postgresql RealDictCursor 패턴으로 dict rows."""
    rows = rows or [{"n": 1}, {"n": 2}]
    mock_cur = MagicMock()
    mock_cur.description = [("n",)]
    mock_cur.fetchall.return_value = rows
    mock_cur.rowcount = len(rows)
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    return mock_conn, mock_cur


class TestRunQueryCache:
    """run_query 캐시 히트/미스 테스트."""

    def setup_method(self):
        db_module._query_cache = {}
        db_module._cache_hits = 0
        db_module._cache_misses = 0

    def test_cache_hit_second_call(self):
        """동일 (conn_id, sql)로 2번 호출 → 두 번째 결과에 캐시 메시지 포함."""
        conn_id = "conn_cache01"
        sql = "SELECT * FROM nums"
        _connections[conn_id] = _make_conn_info(conn_id)
        mock_conn, _ = _make_mock_conn()

        try:
            with patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
                result1 = run_query(conn_id, sql)
                result2 = run_query(conn_id, sql)
            assert "[ERROR]" not in result1
            assert "캐시에서 반환됨" in result2
        finally:
            _connections.pop(conn_id, None)

    def test_cache_miss_different_sql(self):
        """다른 sql → 별도 실행 (캐시 미스)."""
        conn_id = "conn_cache02"
        _connections[conn_id] = _make_conn_info(conn_id)
        mock_conn, _ = _make_mock_conn()

        try:
            with patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
                run_query(conn_id, "SELECT * FROM nums")
                result2 = run_query(conn_id, "SELECT n FROM nums WHERE n = 1")
            assert "캐시에서 반환됨" not in result2
        finally:
            _connections.pop(conn_id, None)

    def test_cache_ttl_expiry(self):
        """TTL 만료 시뮬레이션 → 캐시 미스로 새로 실행."""
        conn_id = "conn_cache03"
        sql = "SELECT * FROM nums"
        _connections[conn_id] = _make_conn_info(conn_id)
        mock_conn, _ = _make_mock_conn()

        try:
            with patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
                run_query(conn_id, sql)
                # TTL 만료 조작
                for key in list(db_module._query_cache.keys()):
                    db_module._query_cache[key]["expires"] = time.time() - 1
                result2 = run_query(conn_id, sql)
            assert "캐시에서 반환됨" not in result2
        finally:
            _connections.pop(conn_id, None)

    def test_non_select_not_cached(self):
        """SELECT 아닌 쿼리는 캐시 안 함 (에러 반환 or 캐시 미저장)."""
        conn_id = "conn_cache04"
        _connections[conn_id] = _make_conn_info(conn_id)
        cache_before = len(db_module._query_cache)
        result = run_query(conn_id, "INSERT INTO log VALUES ('hello')")
        assert len(db_module._query_cache) == cache_before or "[ERROR]" in result
        _connections.pop(conn_id, None)


class TestClearCache:
    """clear_cache 함수 테스트."""

    def setup_method(self):
        db_module._query_cache = {}
        db_module._cache_hits = 0
        db_module._cache_misses = 0

    def test_clear_specific_conn(self):
        """특정 conn_id 캐시만 삭제."""
        _seed_cache("conn_a", "SELECT 1")
        _seed_cache("conn_b", "SELECT 2")
        result = clear_cache("conn_a")
        assert "1개 캐시 항목이 삭제되었습니다" in result
        remaining = list(db_module._query_cache.keys())
        assert all(k[0] != "conn_a" for k in remaining)
        assert any(k[0] == "conn_b" for k in remaining)

    def test_clear_all_cache(self):
        """conn_id 없이 호출 → 전체 캐시 삭제."""
        _seed_cache("conn_x", "SELECT 1")
        _seed_cache("conn_y", "SELECT 2")
        _seed_cache("conn_z", "SELECT 3")
        result = clear_cache()
        assert "3개 캐시 항목이 삭제되었습니다" in result
        assert len(db_module._query_cache) == 0

    def test_clear_nonexistent_conn(self):
        """존재하지 않는 conn_id → 0개 삭제."""
        _seed_cache("conn_only", "SELECT 1")
        result = clear_cache("conn_missing")
        assert "0개 캐시 항목이 삭제되었습니다" in result
        assert len(db_module._query_cache) == 1

    def test_clear_empty_cache(self):
        """빈 캐시에 clear_cache() → 오류 없이 처리."""
        result = clear_cache()
        assert "0개 캐시 항목이 삭제되었습니다" in result

    def test_cache_hit_rate_reported(self):
        """히트율 정보가 결과에 포함됨."""
        db_module._cache_hits = 3
        db_module._cache_misses = 7
        result = clear_cache()
        assert "히트율" in result or "%" in result
