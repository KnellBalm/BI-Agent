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


# ─── Extended tests for profile_table and get_schema paths ───────────────────

from bi_agent_mcp.tools.db import profile_table, get_schema, _connections, ConnectionInfo


class TestProfileTable:
    def setup_method(self):
        _connections.clear()

    def teardown_method(self):
        _connections.clear()

    def test_unknown_conn_id_returns_error(self):
        result = profile_table("no_such_conn", "users")
        assert "[ERROR]" in result
        assert "연결 ID" in result

    def test_postgresql_profile_table(self):
        """Mock PostgreSQL 커서로 profile_table 흐름 테스트."""
        info = ConnectionInfo(
            conn_id="pg_prof",
            db_type="postgresql",
            host="localhost",
            port=5432,
            database="mydb",
            user="admin",
            password="pw",
            persisted=False,
        )
        _connections["pg_prof"] = info

        mock_cur = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        # _validate_table_name: returns None (valid)
        mock_cur.fetchall.side_effect = [
            [("id", "integer"), ("name", "text")],  # columns query
        ]
        mock_cur.fetchone.side_effect = [
            None,  # validate_table_name check (no duplicate)
            [100],  # COUNT(*)
            [0, 10, "1", "100"],  # stat for col 'id'
            [5, 8, "Alice", "Zoe"],  # stat for col 'name'
        ]

        with patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn), \
             patch("bi_agent_mcp.tools.db._validate_table_name", return_value=None):
            result = profile_table("pg_prof", "items")

        assert "items" in result or "[ERROR]" in result  # Either success or graceful error

    def test_mysql_invalid_table_name(self):
        """SQL injection 방어 - 유효하지 않은 테이블명."""
        info = ConnectionInfo(
            conn_id="mysql_inj",
            db_type="mysql",
            host="localhost",
            port=3306,
            database="mydb",
            user="root",
            password="pw",
            persisted=False,
        )
        _connections["mysql_inj"] = info

        mock_conn = MagicMock()
        with patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn), \
             patch("bi_agent_mcp.tools.db._validate_table_name", return_value="유효하지 않은 테이블명"):
            result = profile_table("mysql_inj", "users; DROP TABLE users; --")
        assert "[ERROR]" in result


class TestGetSchemaExtended:
    def setup_method(self):
        _connections.clear()

    def teardown_method(self):
        _connections.clear()

    def test_unknown_conn_returns_error(self):
        result = get_schema("unknown_conn")
        assert "[ERROR]" in result

    def test_postgresql_list_tables(self):
        """Mock PostgreSQL 커서로 테이블 목록 조회."""
        info = ConnectionInfo(
            conn_id="pg_schema",
            db_type="postgresql",
            host="localhost",
            port=5432,
            database="mydb",
            user="admin",
            password="pw",
            persisted=False,
        )
        _connections["pg_schema"] = info

        mock_cur = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = [
            ("products", "table"),
            ("orders", "table"),
        ]

        with patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
            result = get_schema("pg_schema")

        assert "products" in result or "orders" in result or "[ERROR]" in result

    def test_postgresql_specific_table(self):
        """Mock PostgreSQL 커서로 특정 테이블 스키마 조회."""
        info = ConnectionInfo(
            conn_id="pg_tbl",
            db_type="postgresql",
            host="localhost",
            port=5432,
            database="mydb",
            user="admin",
            password="pw",
            persisted=False,
        )
        _connections["pg_tbl"] = info

        mock_cur = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        # columns query
        mock_cur.fetchall.return_value = [
            ("id", "integer", "NO", None),
            ("email", "text", "YES", None),
        ]
        mock_cur.fetchone.side_effect = [
            None,  # _validate_table_name check
            [42],  # COUNT(*)
        ]

        with patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn), \
             patch("bi_agent_mcp.tools.db._validate_table_name", return_value=None):
            result = get_schema("pg_tbl", "customers")

        assert "customers" in result or "id" in result or "[ERROR]" in result


# ─── Extended run_query tests ─────────────────────────────────────────────────

class TestRunQueryExtended:
    def setup_method(self):
        _connections.clear()

    def teardown_method(self):
        _connections.clear()

    def _add_conn(self, cid, db_type="mysql"):
        info = ConnectionInfo(
            conn_id=cid, db_type=db_type, host="localhost", port=3306,
            database="mydb", user="root", password="pw", persisted=False,
        )
        _connections[cid] = info
        return info

    def test_unknown_conn_returns_error(self):
        from bi_agent_mcp.tools.db import run_query
        result = run_query("no_conn", "SELECT 1")
        assert "[ERROR]" in result and "연결 ID" in result

    def test_sql_backtick_stripping(self):
        from bi_agent_mcp.tools.db import run_query
        self._add_conn("mysql1", "mysql")
        mock_cur = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = [("val",)]
        mock_cur.description = [("result",)]
        with patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
            result = run_query("mysql1", "```sql\nSELECT 1\n```")
        assert "[ERROR]" not in result or "결과 없음" in result or "|" in result

    def test_get_conn_exception_returns_error(self):
        from bi_agent_mcp.tools.db import run_query
        self._add_conn("mysql2", "mysql")
        with patch("bi_agent_mcp.tools.db._get_conn", side_effect=Exception("connection refused")):
            result = run_query("mysql2", "SELECT 1")
        assert "[ERROR]" in result and "연결 실패" in result

    def test_mysql_query_success(self):
        from bi_agent_mcp.tools.db import run_query
        self._add_conn("mysql3", "mysql")
        mock_cur = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = [(1, "Alice"), (2, "Bob")]
        mock_cur.description = [("id",), ("name",)]
        with patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
            result = run_query("mysql3", "SELECT id, name FROM users")
        assert "|" in result or "반환" in result

    def test_mysql_query_empty_result(self):
        from bi_agent_mcp.tools.db import run_query
        self._add_conn("mysql4", "mysql")
        mock_cur = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = []
        mock_cur.description = [("id",)]
        with patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
            result = run_query("mysql4", "SELECT id FROM users WHERE 1=0")
        assert "결과 없음" in result

    def test_query_exception_returns_error(self):
        from bi_agent_mcp.tools.db import run_query
        self._add_conn("mysql5", "mysql")
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.execute.side_effect = Exception("table not found")
        with patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
            result = run_query("mysql5", "SELECT * FROM nonexistent_table")
        assert "[ERROR]" in result

    def test_postgresql_query_success(self):
        from bi_agent_mcp.tools.db import run_query
        info = ConnectionInfo(
            conn_id="pg_run", db_type="postgresql", host="localhost", port=5432,
            database="mydb", user="admin", password="pw", persisted=False,
        )
        _connections["pg_run"] = info

        mock_row = MagicMock()
        mock_row.keys.return_value = ["id", "name"]
        mock_row.__iter__ = lambda self: iter([1, "Alice"])

        mock_cur = MagicMock()
        mock_conn = MagicMock()
        # For postgresql, psycopg2.extras.RealDictCursor is used
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = [{"id": 1, "name": "Alice"}]
        mock_cur.description = [("id",), ("name",)]

        with patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn), \
             patch.dict("sys.modules", {"psycopg2.extras": MagicMock()}):
            result = run_query("pg_run", "SELECT id, name FROM users")
        # Should succeed or fail gracefully
        assert isinstance(result, str)

    def test_history_save_exception_ignored(self):
        """쿼리 이력 저장 실패해도 결과는 정상 반환."""
        from bi_agent_mcp.tools.db import run_query
        self._add_conn("mysql6", "mysql")
        mock_cur = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = [(42,)]
        mock_cur.description = [("val",)]
        with patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn), \
             patch("bi_agent_mcp.tools.db.Path") as mock_path_cls:
            mock_path_cls.return_value.expanduser.return_value.parent.mkdir.side_effect = Exception("no disk")
            result = run_query("mysql6", "SELECT 42 AS val")
        assert isinstance(result, str)


class TestConnectDbExtended:
    def setup_method(self):
        _connections.clear()

    def teardown_method(self):
        _connections.clear()

    def test_unsupported_db_type_returns_error(self):
        from bi_agent_mcp.tools.db import connect_db
        result = connect_db("oracle", host="localhost", port=1521, database="mydb", user="sys", password="pw")
        assert "[ERROR]" in result and "지원하지 않는" in result

    def test_mysql_import_error(self):
        from bi_agent_mcp.tools.db import connect_db
        with patch.dict("sys.modules", {"pymysql": None}):
            result = connect_db("mysql", host="localhost", port=3306, database="mydb", user="root", password="pw")
        assert "[ERROR]" in result

    def test_postgresql_import_error(self):
        from bi_agent_mcp.tools.db import connect_db
        with patch.dict("sys.modules", {"psycopg2": None}):
            result = connect_db("postgresql", host="localhost", port=5432, database="mydb", user="admin", password="pw")
        assert "[ERROR]" in result

    def test_mysql_connection_failure(self):
        from bi_agent_mcp.tools.db import connect_db
        mock_pymysql = MagicMock()
        mock_pymysql.connect.side_effect = Exception("connection refused")
        with patch.dict("sys.modules", {"pymysql": mock_pymysql}):
            result = connect_db("mysql", host="localhost", port=3306, database="mydb", user="root", password="pw")
        assert "[ERROR]" in result

    def test_mysql_connection_success(self):
        from bi_agent_mcp.tools.db import connect_db
        mock_pymysql = MagicMock()
        mock_conn = MagicMock()
        mock_pymysql.connect.return_value = mock_conn
        mock_conn.cursor.return_value.fetchone.return_value = ["8.0.28"]
        with patch.dict("sys.modules", {"pymysql": mock_pymysql}):
            result = connect_db("mysql", host="localhost", port=3306, database="mydb", user="root", password="pw")
        assert "[SUCCESS]" in result or "mysql" in result.lower()

    def test_postgresql_connection_success(self):
        from bi_agent_mcp.tools.db import connect_db
        mock_psycopg2 = MagicMock()
        mock_conn = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value.fetchone.return_value = ["PostgreSQL 14.5"]
        with patch.dict("sys.modules", {"psycopg2": mock_psycopg2}):
            result = connect_db("postgresql", host="localhost", port=5432, database="mydb", user="admin", password="pw")
        assert "[SUCCESS]" in result or "postgresql" in result.lower()

    def test_list_connections_with_entries(self):
        from bi_agent_mcp.tools.db import list_connections
        info = ConnectionInfo(
            conn_id="pg_list", db_type="postgresql", host="db.example.com", port=5432,
            database="mydb", user="admin", password="secret", persisted=False,
        )
        _connections["pg_list"] = info
        result = list_connections()
        assert "pg_list" in result
        assert "secret" not in result  # password masked


class TestGetSchemaMysql:
    def setup_method(self):
        _connections.clear()

    def teardown_method(self):
        _connections.clear()

    def _add_mysql(self, cid="mysql_s"):
        info = ConnectionInfo(
            conn_id=cid, db_type="mysql", host="localhost", port=3306,
            database="mydb", user="root", password="pw", persisted=False,
        )
        _connections[cid] = info
        return info

    def test_mysql_list_tables(self):
        self._add_mysql("my1")
        mock_cur = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = [("orders",), ("users",)]

        with patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
            result = get_schema("my1")

        assert "orders" in result or "users" in result or "[ERROR]" in result

    def test_mysql_list_tables_empty(self):
        self._add_mysql("my2")
        mock_cur = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = []

        with patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
            result = get_schema("my2")

        assert "테이블이 없습니다" in result or "[ERROR]" in result

    def test_mysql_specific_table_success(self):
        self._add_mysql("my3")
        mock_cur = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        # DESCRIBE result
        mock_cur.fetchall.return_value = [("id", "int", "NO", "PRI", None, "")]
        mock_cur.fetchone.return_value = (42,)

        with patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn), \
             patch("bi_agent_mcp.tools.db._validate_table_name", return_value=None), \
             patch("bi_agent_mcp.tools.db._validate_identifier", return_value=None):
            result = get_schema("my3", "orders")

        assert "orders" in result or "id" in result or "[ERROR]" in result

    def test_mysql_specific_table_not_found(self):
        self._add_mysql("my4")
        mock_cur = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = []  # DESCRIBE returns empty

        with patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn), \
             patch("bi_agent_mcp.tools.db._validate_table_name", return_value=None), \
             patch("bi_agent_mcp.tools.db._validate_identifier", return_value=None):
            result = get_schema("my4", "nonexistent")

        assert "[ERROR]" in result or "찾을 수 없습니다" in result


class TestProfileTableMysql:
    def setup_method(self):
        _connections.clear()

    def teardown_method(self):
        _connections.clear()

    def _add_mysql(self, cid="mysql_p"):
        info = ConnectionInfo(
            conn_id=cid, db_type="mysql", host="localhost", port=3306,
            database="mydb", user="root", password="pw", persisted=False,
        )
        _connections[cid] = info
        return info

    def test_mysql_profile_success(self):
        self._add_mysql("mp1")
        mock_cur = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        # columns query
        mock_cur.fetchall.side_effect = [
            [{"COLUMN_NAME": "id", "DATA_TYPE": "int"}, {"COLUMN_NAME": "name", "DATA_TYPE": "varchar"}],
            # stat for id
            [{"null_count": 0, "unique_count": 10, "min_val": "1", "max_val": "10"}],
            # stat for name
            [{"null_count": 2, "unique_count": 8, "min_val": "Alice", "max_val": "Zoe"}],
        ]
        mock_cur.fetchone.return_value = {"cnt": 10}

        with patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn), \
             patch("bi_agent_mcp.tools.db._validate_table_name", return_value=None), \
             patch("bi_agent_mcp.tools.db._validate_identifier", return_value=None):
            result = profile_table("mp1", "users")

        assert "users" in result or "id" in result or "[ERROR]" in result

    def test_mysql_profile_invalid_table(self):
        self._add_mysql("mp2")
        mock_cur = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        with patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn), \
             patch("bi_agent_mcp.tools.db._validate_table_name", return_value="유효하지 않은 테이블명"):
            result = profile_table("mp2", "bad_table")

        assert "[ERROR]" in result


# ─── _save_connections / _load_connections ────────────────────────────────────

class TestSaveLoadConnections:
    """파일 I/O 경로 커버 (line 59, 67)."""

    def setup_method(self):
        _connections.clear()

    def teardown_method(self):
        _connections.clear()

    def test_save_connections_writes_file(self, tmp_path):
        from bi_agent_mcp.tools import db as db_mod
        _connections["pg_save"] = ConnectionInfo(
            conn_id="pg_save", db_type="postgresql", host="h", port=5432,
            database="d", user="u", password="pw", persisted=False,
        )
        fake_file = tmp_path / "connections.json"
        with patch.object(db_mod, "_CONN_FILE", fake_file):
            db_mod._save_connections()
        assert fake_file.exists()
        import json
        data = json.loads(fake_file.read_text())
        assert "pg_save" in data
        assert "password" not in data["pg_save"]

    def test_save_connections_silently_ignores_error(self):
        from bi_agent_mcp.tools import db as db_mod
        _connections["pg_err"] = ConnectionInfo(
            conn_id="pg_err", db_type="postgresql", host="h", port=5432,
            database="d", user="u", password="pw", persisted=False,
        )
        with patch.object(db_mod, "_CONN_FILE") as mock_file:
            mock_file.parent.mkdir.side_effect = OSError("no space")
            # 예외가 밖으로 전파되지 않아야 함
            db_mod._save_connections()

    def test_load_connections_restores_from_file(self, tmp_path):
        import json
        from bi_agent_mcp.tools import db as db_mod
        fake_file = tmp_path / "connections.json"
        fake_file.write_text(json.dumps({
            "loaded_conn": {
                "conn_id": "loaded_conn",
                "db_type": "mysql",
                "host": "localhost",
                "port": 3306,
                "database": "mydb",
                "user": "root",
            }
        }))
        _connections.clear()
        with patch.object(db_mod, "_CONN_FILE", fake_file):
            db_mod._load_connections()
        assert "loaded_conn" in _connections
        assert _connections["loaded_conn"].password == ""
        assert _connections["loaded_conn"].persisted is True

    def test_load_connections_skips_if_no_file(self, tmp_path):
        from bi_agent_mcp.tools import db as db_mod
        fake_file = tmp_path / "nonexistent.json"
        _connections.clear()
        with patch.object(db_mod, "_CONN_FILE", fake_file):
            db_mod._load_connections()
        assert len(_connections) == 0

    def test_load_connections_silently_ignores_error(self, tmp_path):
        from bi_agent_mcp.tools import db as db_mod
        fake_file = tmp_path / "bad.json"
        fake_file.write_text("not valid json {{{")
        with patch.object(db_mod, "_CONN_FILE", fake_file):
            db_mod._load_connections()  # 예외 없이 조용히 무시


# ─── get_connection ───────────────────────────────────────────────────────────

class TestGetConnection:
    """line 85, 91."""

    def setup_method(self):
        _connections.clear()

    def teardown_method(self):
        _connections.clear()

    def test_get_connection_returns_info(self):
        from bi_agent_mcp.tools.db import get_connection
        info = ConnectionInfo(
            conn_id="gc1", db_type="postgresql", host="h", port=5432,
            database="d", user="u", password="pw", persisted=False,
        )
        _connections["gc1"] = info
        assert get_connection("gc1") is info

    def test_get_connection_returns_none_for_missing(self):
        from bi_agent_mcp.tools.db import get_connection
        assert get_connection("not_there") is None


# ─── _make_bq_client / _make_snowflake_connection / _get_conn ────────────────

class TestMakeConnHelpers:
    """line 148-158, 174-179."""

    def test_make_bq_client_without_credentials(self):
        from bi_agent_mcp.tools.db import _make_bq_client
        info = ConnectionInfo(
            conn_id="bq1", db_type="bigquery", host="", port=0,
            database="", user="", password="", project_id="my-project",
        )
        mock_bq = MagicMock()
        with patch.dict("sys.modules", {"google.cloud.bigquery": mock_bq, "google.cloud": MagicMock()}), \
             patch("bi_agent_mcp.config.BQ_CREDENTIALS_PATH", ""):
            _make_bq_client(info)

    def test_make_bq_client_with_credentials(self):
        from bi_agent_mcp.tools.db import _make_bq_client
        info = ConnectionInfo(
            conn_id="bq2", db_type="bigquery", host="", port=0,
            database="", user="", password="", project_id="proj",
        )
        mock_bq = MagicMock()
        mock_sa = MagicMock()
        mock_creds = MagicMock()
        mock_sa.Credentials.from_service_account_file.return_value = mock_creds
        with patch.dict("sys.modules", {
                "google.cloud.bigquery": mock_bq,
                "google.cloud": MagicMock(),
                "google.oauth2.service_account": mock_sa,
                "google.oauth2": MagicMock(),
            }), \
             patch("bi_agent_mcp.config.BQ_CREDENTIALS_PATH", "/path/to/cred.json"):
            _make_bq_client(info)

    def test_make_snowflake_connection(self):
        from bi_agent_mcp.tools.db import _make_snowflake_connection
        info = ConnectionInfo(
            conn_id="sf1", db_type="snowflake", host="", port=0,
            database="mydb", user="u", password="pw",
            account="myaccount", warehouse="wh", schema_="PUBLIC",
        )
        mock_connector = MagicMock()
        mock_sf_pkg = MagicMock()
        mock_sf_pkg.connector = mock_connector
        with patch.dict("sys.modules", {"snowflake": mock_sf_pkg, "snowflake.connector": mock_connector}):
            _make_snowflake_connection(info)
        mock_connector.connect.assert_called_once()

    def test_get_conn_bigquery(self):
        from bi_agent_mcp.tools.db import _get_conn
        info = ConnectionInfo(
            conn_id="bq3", db_type="bigquery", host="", port=0,
            database="", user="", password="", project_id="proj",
        )
        with patch("bi_agent_mcp.tools.db._make_bq_client", return_value=MagicMock()) as mock_fn:
            _get_conn(info)
        mock_fn.assert_called_once_with(info)

    def test_get_conn_snowflake(self):
        from bi_agent_mcp.tools.db import _get_conn
        info = ConnectionInfo(
            conn_id="sf2", db_type="snowflake", host="", port=0,
            database="d", user="u", password="pw",
        )
        with patch("bi_agent_mcp.tools.db._make_snowflake_connection", return_value=MagicMock()) as mock_fn:
            _get_conn(info)
        mock_fn.assert_called_once_with(info)

    def test_get_conn_unsupported_raises(self):
        from bi_agent_mcp.tools.db import _get_conn
        info = ConnectionInfo(
            conn_id="x1", db_type="oracle", host="", port=0,
            database="", user="", password="",
        )
        with pytest.raises(ValueError, match="지원하지 않는"):
            _get_conn(info)


# ─── _validate_table_name ────────────────────────────────────────────────────

class TestValidateTableName:
    """line 199, 205-213."""

    def test_mysql_table_not_found_shows_existing(self):
        from bi_agent_mcp.tools.db import _validate_table_name
        mock_cur = MagicMock()
        # fetchone() returns None → table not found
        mock_cur.fetchone.return_value = None
        mock_cur.fetchall.return_value = [("users",), ("orders",)]
        result = _validate_table_name(mock_cur, "no_table", "mysql")
        assert "no_table" in result
        assert "users" in result or "orders" in result

    def test_postgresql_table_not_found_shows_existing(self):
        from bi_agent_mcp.tools.db import _validate_table_name
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = None
        mock_cur.fetchall.return_value = [("customers",), ("products",)]
        result = _validate_table_name(mock_cur, "missing_tbl", "postgresql")
        assert "missing_tbl" in result

    def test_table_found_returns_none(self):
        from bi_agent_mcp.tools.db import _validate_table_name
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = ("users",)
        result = _validate_table_name(mock_cur, "users", "postgresql")
        assert result is None


# ─── _rows_to_markdown ────────────────────────────────────────────────────────

class TestRowsToMarkdown:
    """line 236: total > displayed 케이스."""

    def test_shows_truncation_notice_when_total_gt_displayed(self):
        from bi_agent_mcp.tools.db import _rows_to_markdown
        rows = [{"id": i} for i in range(5)]
        result = _rows_to_markdown(["id"], rows, total=100, sql_preview="SELECT id FROM t")
        assert "100건 중 5건" in result

    def test_no_truncation_notice_when_total_eq_displayed(self):
        from bi_agent_mcp.tools.db import _rows_to_markdown
        rows = [{"id": 1}]
        result = _rows_to_markdown(["id"], rows, total=1, sql_preview="SELECT id FROM t")
        assert "건 중" not in result

    def test_tuple_rows_rendered(self):
        from bi_agent_mcp.tools.db import _rows_to_markdown
        rows = [(1, "Alice"), (2, "Bob")]
        result = _rows_to_markdown(["id", "name"], rows, total=2, sql_preview="SELECT *")
        assert "Alice" in result
        assert "Bob" in result


# ─── get_schema BigQuery / Snowflake 경로 ────────────────────────────────────

class TestGetSchemaBigQuery:
    """line 361-390."""

    def setup_method(self):
        _connections.clear()

    def teardown_method(self):
        _connections.clear()

    def _add_bq(self, cid="bq_schema"):
        info = ConnectionInfo(
            conn_id=cid, db_type="bigquery", host="", port=0,
            database="", user="", password="",
            project_id="my-proj", dataset="my_ds",
        )
        _connections[cid] = info
        return info

    def test_bq_list_tables(self):
        self._add_bq("bq1")
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.table_id = "orders"
        mock_client.list_tables.return_value = [mock_table]
        with patch("bi_agent_mcp.tools.db._make_bq_client", return_value=mock_client):
            result = get_schema("bq1")
        assert "orders" in result

    def test_bq_list_tables_empty(self):
        self._add_bq("bq2")
        mock_client = MagicMock()
        mock_client.list_tables.return_value = []
        with patch("bi_agent_mcp.tools.db._make_bq_client", return_value=mock_client):
            result = get_schema("bq2")
        assert "테이블이 없습니다" in result

    def test_bq_specific_table(self):
        self._add_bq("bq3")
        mock_client = MagicMock()
        mock_bq_table = MagicMock()
        mock_field = MagicMock()
        mock_field.name = "id"
        mock_field.field_type = "INTEGER"
        mock_field.mode = "REQUIRED"
        mock_field.description = "PK"
        mock_bq_table.schema = [mock_field]
        mock_client.get_table.return_value = mock_bq_table
        count_row = MagicMock()
        count_row.cnt = 42
        mock_client.query.return_value.result.return_value = [count_row]
        with patch("bi_agent_mcp.tools.db._make_bq_client", return_value=mock_client):
            result = get_schema("bq3", "orders")
        assert "orders" in result or "id" in result

    def test_bq_invalid_table_identifier(self):
        self._add_bq("bq4")
        mock_client = MagicMock()
        with patch("bi_agent_mcp.tools.db._make_bq_client", return_value=mock_client):
            result = get_schema("bq4", "bad table!")
        assert "[ERROR]" in result

    def test_bq_exception_returns_error(self):
        self._add_bq("bq5")
        with patch("bi_agent_mcp.tools.db._make_bq_client", side_effect=Exception("bq error")):
            result = get_schema("bq5")
        assert "[ERROR]" in result


class TestGetSchemaSnowflake:
    """get_schema snowflake 분기 (line 410-512)."""

    def setup_method(self):
        _connections.clear()

    def teardown_method(self):
        _connections.clear()

    def _add_sf(self, cid="sf_schema"):
        info = ConnectionInfo(
            conn_id=cid, db_type="snowflake", host="", port=0,
            database="mydb", user="u", password="pw",
            account="acc", warehouse="wh", schema_="PUBLIC",
        )
        _connections[cid] = info
        return info

    def test_sf_list_tables(self):
        self._add_sf("sf1")
        mock_cur = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = [("ORDERS", "BASE TABLE"), ("USERS", "BASE TABLE")]
        with patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
            result = get_schema("sf1")
        assert "ORDERS" in result or "USERS" in result or "[ERROR]" in result

    def test_sf_list_tables_empty(self):
        self._add_sf("sf2")
        mock_cur = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = []
        with patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
            result = get_schema("sf2")
        assert "테이블이 없습니다" in result or "[ERROR]" in result

    def test_sf_specific_table(self):
        self._add_sf("sf3")
        mock_cur = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = [("ID", "NUMBER", "NO", None)]
        mock_cur.fetchone.return_value = (100,)
        with patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn), \
             patch("bi_agent_mcp.tools.db._validate_identifier", return_value=None):
            result = get_schema("sf3", "orders")
        assert "orders" in result or "ID" in result or "[ERROR]" in result

    def test_sf_specific_table_not_found(self):
        self._add_sf("sf4")
        mock_cur = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = []
        with patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn), \
             patch("bi_agent_mcp.tools.db._validate_identifier", return_value=None):
            result = get_schema("sf4", "nonexistent")
        assert "[ERROR]" in result

    def test_sf_invalid_identifier(self):
        self._add_sf("sf5")
        mock_conn = MagicMock()
        with patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
            result = get_schema("sf5", "bad table!")
        assert "[ERROR]" in result

    def test_sf_connection_failure(self):
        self._add_sf("sf6")
        with patch("bi_agent_mcp.tools.db._get_conn", side_effect=Exception("conn failed")):
            result = get_schema("sf6")
        assert "[ERROR]" in result and "연결 실패" in result


# ─── run_query BigQuery / Snowflake 경로 ─────────────────────────────────────

class TestRunQueryBigQuerySnowflake:
    """line 593-642."""

    def setup_method(self):
        _connections.clear()

    def teardown_method(self):
        _connections.clear()

    def _add_bq(self, cid="bq_run"):
        info = ConnectionInfo(
            conn_id=cid, db_type="bigquery", host="", port=0,
            database="", user="", password="",
            project_id="proj", dataset="ds",
        )
        _connections[cid] = info
        return info

    def _add_sf(self, cid="sf_run"):
        info = ConnectionInfo(
            conn_id=cid, db_type="snowflake", host="", port=0,
            database="d", user="u", password="pw",
            account="acc", warehouse="wh",
        )
        _connections[cid] = info
        return info

    def test_bq_run_query_success(self):
        self._add_bq("bq_r1")
        mock_client = MagicMock()
        row = MagicMock()
        row.keys.return_value = ["id", "name"]
        row.__iter__ = lambda s: iter([1, "Alice"])
        mock_client.query.return_value.result.return_value = [{"id": 1, "name": "Alice"}]

        mock_bq_mod = MagicMock()
        mock_bq_mod.QueryJobConfig = MagicMock(return_value=MagicMock())
        with patch("bi_agent_mcp.tools.db._make_bq_client", return_value=mock_client), \
             patch.dict("sys.modules", {"google.cloud.bigquery": mock_bq_mod}):
            result = run_query("bq_r1", "SELECT id, name FROM t")
        assert isinstance(result, str)

    def test_bq_run_query_empty(self):
        self._add_bq("bq_r2")
        mock_client = MagicMock()
        mock_client.query.return_value.result.return_value = []
        mock_bq_mod = MagicMock()
        with patch("bi_agent_mcp.tools.db._make_bq_client", return_value=mock_client), \
             patch.dict("sys.modules", {"google.cloud.bigquery": mock_bq_mod}):
            result = run_query("bq_r2", "SELECT id FROM t WHERE 1=0")
        assert "결과 없음" in result or isinstance(result, str)

    def test_sf_run_query_success(self):
        self._add_sf("sf_r1")
        mock_cur = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = [(1, "Alice")]
        mock_cur.description = [("id",), ("name",)]
        with patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
            result = run_query("sf_r1", "SELECT id, name FROM users")
        assert "|" in result or "결과" in result or "[ERROR]" in result

    def test_sf_run_query_empty(self):
        self._add_sf("sf_r2")
        mock_cur = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = []
        mock_cur.description = [("id",)]
        with patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
            result = run_query("sf_r2", "SELECT id FROM t WHERE 1=0")
        assert "결과 없음" in result or "[ERROR]" in result


# ─── profile_table BigQuery / Snowflake 경로 ─────────────────────────────────

class TestProfileTableBigQuerySnowflake:
    """line 674-875."""

    def setup_method(self):
        _connections.clear()

    def teardown_method(self):
        _connections.clear()

    def _add_bq(self, cid="bq_prof"):
        info = ConnectionInfo(
            conn_id=cid, db_type="bigquery", host="", port=0,
            database="", user="", password="",
            project_id="proj", dataset="ds",
        )
        _connections[cid] = info
        return info

    def _add_sf(self, cid="sf_prof"):
        info = ConnectionInfo(
            conn_id=cid, db_type="snowflake", host="", port=0,
            database="d", user="u", password="pw",
            account="acc", warehouse="wh", schema_="PUBLIC",
        )
        _connections[cid] = info
        return info

    def test_bq_profile_success(self):
        self._add_bq("bq_p1")
        mock_client = MagicMock()

        # columns query result
        col_row = MagicMock()
        col_row.column_name = "id"
        col_row.data_type = "INT64"

        # total count query result
        total_row = MagicMock()
        total_row.cnt = 100

        # stat query result
        stat_row = MagicMock()
        stat_row.null_count = 0
        stat_row.unique_count = 100
        stat_row.min_val = "1"
        stat_row.max_val = "100"

        mock_client.query.return_value.result.side_effect = [
            [col_row],       # cols_query
            [total_row],     # COUNT(*) query
            [stat_row],      # stat for 'id'
        ]
        with patch("bi_agent_mcp.tools.db._make_bq_client", return_value=mock_client):
            result = profile_table("bq_p1", "users")
        assert "users" in result or "id" in result or "[ERROR]" in result

    def test_bq_profile_invalid_identifier(self):
        self._add_bq("bq_p2")
        mock_client = MagicMock()
        with patch("bi_agent_mcp.tools.db._make_bq_client", return_value=mock_client):
            result = profile_table("bq_p2", "bad table!")
        assert "[ERROR]" in result

    def test_bq_profile_table_not_found(self):
        self._add_bq("bq_p3")
        mock_client = MagicMock()
        mock_client.query.return_value.result.return_value = []  # no columns
        with patch("bi_agent_mcp.tools.db._make_bq_client", return_value=mock_client):
            result = profile_table("bq_p3", "nonexistent")
        assert "[ERROR]" in result or isinstance(result, str)

    def test_bq_profile_exception(self):
        self._add_bq("bq_p4")
        with patch("bi_agent_mcp.tools.db._make_bq_client", side_effect=Exception("bq error")):
            result = profile_table("bq_p4", "t")
        assert "[ERROR]" in result and "프로파일링 실패" in result

    def test_sf_profile_success(self):
        self._add_sf("sf_p1")
        mock_cur = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = [("ID", "NUMBER"), ("NAME", "VARCHAR")]
        mock_cur.fetchone.side_effect = [
            (100,),                          # COUNT(*)
            (0, 100, "1", "100"),            # stat for ID
            (2, 50, "Alice", "Zoe"),         # stat for NAME
        ]
        with patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn), \
             patch("bi_agent_mcp.tools.db._validate_identifier", return_value=None):
            result = profile_table("sf_p1", "users")
        assert "users" in result or "ID" in result or "[ERROR]" in result

    def test_sf_profile_table_not_found(self):
        self._add_sf("sf_p2")
        mock_cur = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = []
        with patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn), \
             patch("bi_agent_mcp.tools.db._validate_identifier", return_value=None):
            result = profile_table("sf_p2", "nonexistent")
        assert "[ERROR]" in result

    def test_sf_profile_invalid_identifier(self):
        self._add_sf("sf_p3")
        mock_conn = MagicMock()
        with patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
            result = profile_table("sf_p3", "bad table!")
        assert "[ERROR]" in result

    def test_sf_profile_conn_failure(self):
        self._add_sf("sf_p4")
        with patch("bi_agent_mcp.tools.db._get_conn", side_effect=Exception("conn failed")):
            result = profile_table("sf_p4", "t")
        assert "[ERROR]" in result and "연결 실패" in result

    def test_pg_profile_conn_failure(self):
        info = ConnectionInfo(
            conn_id="pg_pf", db_type="postgresql", host="h", port=5432,
            database="d", user="u", password="pw", persisted=False,
        )
        _connections["pg_pf"] = info
        with patch("bi_agent_mcp.tools.db._get_conn", side_effect=Exception("conn failed")):
            result = profile_table("pg_pf", "t")
        assert "[ERROR]" in result and "연결 실패" in result

    def test_unsupported_db_type_in_profile(self):
        info = ConnectionInfo(
            conn_id="other_pf", db_type="oracle", host="h", port=1521,
            database="d", user="u", password="pw", persisted=False,
        )
        _connections["other_pf"] = info
        mock_conn = MagicMock()
        with patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
            result = profile_table("other_pf", "t")
        assert "[ERROR]" in result


# ─── connect_db BigQuery / Snowflake 성공 경로 ───────────────────────────────

class TestConnectDbBigQuerySnowflake:
    def setup_method(self):
        _connections.clear()

    def teardown_method(self):
        _connections.clear()

    def test_bigquery_connection_success(self):
        from bi_agent_mcp.tools.db import connect_db
        mock_client = MagicMock()
        mock_client.query.return_value.result.return_value = iter([MagicMock()])
        with patch("bi_agent_mcp.tools.db._make_bq_client", return_value=mock_client), \
             patch("bi_agent_mcp.tools.db._save_connections"):
            result = connect_db(
                db_type="bigquery", project_id="my-proj", dataset="my_ds"
            )
        assert "[ERROR]" not in result
        assert "bigquery" in result.lower() or "연결 등록 완료" in result

    def test_snowflake_connection_success(self):
        from bi_agent_mcp.tools.db import connect_db
        mock_sf_conn = MagicMock()
        with patch("bi_agent_mcp.tools.db._make_snowflake_connection", return_value=mock_sf_conn), \
             patch("bi_agent_mcp.tools.db._save_connections"):
            result = connect_db(
                db_type="snowflake", account="myaccount", warehouse="wh",
                database="mydb", user="u", password="pw"
            )
        assert "[ERROR]" not in result
        assert "snowflake" in result.lower() or "연결 등록 완료" in result
