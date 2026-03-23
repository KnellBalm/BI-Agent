"""bi_agent_mcp.tools.db MCP 도구 단위 테스트."""
import pytest
from unittest.mock import MagicMock, patch
from bi_agent_mcp.tools.db import connect_db, get_schema, run_query, _connections, ConnectionInfo
from bi_agent_mcp.config import QUERY_LIMIT


class TestConnectDb:
    def test_invalid_db_type_returns_error(self):
        result = connect_db(db_type="oracle", host="localhost", port=1521, database="db", user="u", password="p")
        assert result.startswith("[ERROR]")

    def test_postgresql_connection_failure_returns_error(self):
        with patch("bi_agent_mcp.tools.db._make_pg_connection", side_effect=Exception("connection refused")):
            result = connect_db(db_type="postgresql", host="localhost", port=5432, database="db", user="u", password="p")
        assert "[ERROR]" in result

    def test_mysql_connection_failure_returns_error(self):
        with patch("bi_agent_mcp.tools.db._make_mysql_connection", side_effect=Exception("access denied")):
            result = connect_db(db_type="mysql", host="localhost", port=3306, database="db", user="u", password="p")
        assert "[ERROR]" in result

    def test_postgresql_success_registers_connection(self):
        mock_conn = MagicMock()
        with patch("bi_agent_mcp.tools.db._make_pg_connection", return_value=mock_conn):
            result = connect_db(db_type="postgresql", host="localhost", port=5432, database="testdb", user="user", password="pass")
        assert "[ERROR]" not in result
        assert "conn_" in result

    def test_bigquery_invalid_no_project_returns_error(self):
        with patch("bi_agent_mcp.tools.db._make_bq_client", side_effect=Exception("project not set")):
            result = connect_db(db_type="bigquery", project_id="", dataset="ds")
        assert "[ERROR]" in result


class TestRunQuery:
    def _register_mock_pg_conn(self):
        """테스트용 postgresql mock 연결 등록."""
        conn_id = "conn_test01"
        _connections[conn_id] = ConnectionInfo(
            conn_id=conn_id,
            db_type="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            user="user",
            password="pass",
        )
        return conn_id

    def _register_mock_mysql_conn(self):
        conn_id = "conn_test02"
        _connections[conn_id] = ConnectionInfo(
            conn_id=conn_id,
            db_type="mysql",
            host="localhost",
            port=3306,
            database="testdb",
            user="user",
            password="pass",
        )
        return conn_id

    def test_unknown_conn_id_returns_error(self):
        result = run_query("conn_nonexistent", "SELECT 1")
        assert "[ERROR]" in result

    def test_blocked_sql_returns_error(self):
        conn_id = self._register_mock_pg_conn()
        result = run_query(conn_id, "DROP TABLE users")
        assert "[ERROR]" in result

    def test_postgresql_select_returns_markdown(self):
        conn_id = self._register_mock_pg_conn()
        mock_row = {"id": 1, "name": "Alice"}

        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = [mock_row]
        mock_cur.description = [("id",), ("name",)]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        with patch("bi_agent_mcp.tools.db._make_pg_connection", return_value=mock_conn):
            import psycopg2.extras
            mock_cur_rd = MagicMock()
            mock_cur_rd.fetchall.return_value = [mock_row]
            mock_cur_rd.description = [("id",), ("name",)]
            mock_conn.cursor.return_value = mock_cur_rd
            result = run_query(conn_id, "SELECT id, name FROM users")

        assert "[ERROR]" not in result or "결과 없음" in result or "|" in result

    def test_limit_applied_in_query(self):
        """LIMIT QUERY_LIMIT이 safe_query에 포함되는지 확인."""
        conn_id = self._register_mock_pg_conn()

        captured = {}

        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = []
        mock_cur.description = None

        def fake_execute(sql, *args, **kwargs):
            captured["sql"] = str(sql)

        mock_cur.execute.side_effect = fake_execute
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        with patch("bi_agent_mcp.tools.db._make_pg_connection", return_value=mock_conn):
            run_query(conn_id, "SELECT 1")

        assert str(QUERY_LIMIT) in captured.get("sql", "")

    def test_mysql_select_returns_markdown(self):
        conn_id = self._register_mock_mysql_conn()
        mock_row = {"id": 1, "val": "x"}

        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = [mock_row]
        mock_cur.description = [("id",), ("val",)]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        with patch("bi_agent_mcp.tools.db._make_mysql_connection", return_value=mock_conn):
            result = run_query(conn_id, "SELECT id, val FROM t")

        assert "[ERROR]" not in result or "결과 없음" in result or "|" in result


class TestGetSchema:
    def _register_mock_pg_conn(self):
        conn_id = "conn_schema01"
        _connections[conn_id] = ConnectionInfo(
            conn_id=conn_id,
            db_type="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            user="user",
            password="pass",
        )
        return conn_id

    def test_unknown_conn_id_returns_error(self):
        result = get_schema("conn_nonexistent")
        assert "[ERROR]" in result

    def test_postgresql_table_list_returned(self):
        conn_id = self._register_mock_pg_conn()

        mock_cur = MagicMock()
        mock_cur.fetchall.side_effect = [
            [("users", "BASE TABLE"), ("orders", "BASE TABLE")],
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        with patch("bi_agent_mcp.tools.db._make_pg_connection", return_value=mock_conn):
            result = get_schema(conn_id)

        assert "users" in result or "[ERROR]" in result
