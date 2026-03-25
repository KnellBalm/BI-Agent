"""bi_agent_mcp.tools.text_to_sql 단위 테스트."""
import sqlite3
import pytest
from unittest.mock import patch

import bi_agent_mcp.tools.text_to_sql as _mod
from bi_agent_mcp.tools.text_to_sql import generate_sql
from bi_agent_mcp.tools.db import ConnectionInfo, _connections


# ─── helpers ─────────────────────────────────────────────────────────────────

def _sqlite_info(conn_id: str, db_file: str) -> ConnectionInfo:
    return ConnectionInfo(
        conn_id=conn_id, db_type="sqlite",
        host="", port=0, database=db_file, user="", password="",
    )


def _setup_db(tmp_path, name: str = "shop.db") -> str:
    db_file = str(tmp_path / name)
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, amount REAL, created_at TEXT)")
    conn.execute("INSERT INTO orders VALUES (1, 100.0, '2024-01-01')")
    conn.commit()
    conn.close()
    return db_file


# ─── 에러 케이스 ──────────────────────────────────────────────────────────────

class TestGenerateSqlErrors:
    def test_unknown_conn_id(self):
        """conn_id 없음 → [ERROR]."""
        with patch.object(_mod, "_connections", {}):
            result = generate_sql("no_conn", "주문 수 알려줘")
        assert "[ERROR]" in result
        assert "no_conn" in result

    def test_schema_error_propagated(self, tmp_path):
        """테이블 없는 DB → 스키마 [ERROR] 전파."""
        db_file = str(tmp_path / "empty.db")
        sqlite3.connect(db_file).close()
        conn_id = "conn_empty"
        _connections[conn_id] = _sqlite_info(conn_id, db_file)
        try:
            result = generate_sql(conn_id, "주문 알려줘")
        finally:
            del _connections[conn_id]
        assert "[ERROR]" in result


# ─── 정상 케이스 ──────────────────────────────────────────────────────────────

class TestGenerateSqlSuccess:
    def test_returns_schema_and_instructions(self, tmp_path):
        """정상 반환: 스키마 + 질문 + SQL 생성 지시문 포함."""
        db_file = _setup_db(tmp_path)
        conn_id = "conn_ok01"
        _connections[conn_id] = _sqlite_info(conn_id, db_file)
        try:
            result = generate_sql(conn_id, "총 매출 알려줘")
        finally:
            del _connections[conn_id]

        assert "SQL 생성 요청" in result
        assert "총 매출 알려줘" in result
        assert "orders" in result           # 스키마 포함
        assert "SELECT" in result           # SQL 생성 지시문 포함
        assert "run_query" in result        # 실행 안내 포함
        assert "[ERROR]" not in result

    def test_db_type_included(self, tmp_path):
        """DB 타입이 결과에 포함됨."""
        db_file = _setup_db(tmp_path)
        conn_id = "conn_dbtype"
        _connections[conn_id] = _sqlite_info(conn_id, db_file)
        try:
            result = generate_sql(conn_id, "주문 목록")
        finally:
            del _connections[conn_id]

        assert "sqlite" in result

    def test_no_anthropic_dependency(self, tmp_path):
        """anthropic 라이브러리 / API 키 없어도 동작."""
        db_file = _setup_db(tmp_path)
        conn_id = "conn_no_api"
        _connections[conn_id] = _sqlite_info(conn_id, db_file)
        try:
            with patch.dict("sys.modules", {"anthropic": None}):
                result = generate_sql(conn_id, "매출 합계")
        finally:
            del _connections[conn_id]

        assert "[ERROR]" not in result
        assert "SQL 생성 요청" in result

    def test_select_only_rule_in_output(self, tmp_path):
        """SELECT 전용 규칙이 지시문에 포함됨."""
        db_file = _setup_db(tmp_path)
        conn_id = "conn_rule"
        _connections[conn_id] = _sqlite_info(conn_id, db_file)
        try:
            result = generate_sql(conn_id, "주문 수")
        finally:
            del _connections[conn_id]

        assert "SELECT" in result
        assert "INSERT" in result or "변경" in result or "DELETE" in result
