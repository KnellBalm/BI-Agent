"""bi_agent_mcp.tools.context 단위 테스트."""
import sqlite3
import pytest
from unittest.mock import MagicMock, patch

from bi_agent_mcp.tools.context import get_context_for_question, get_table_relationships
from bi_agent_mcp.tools.db import ConnectionInfo, _connections


def _sqlite_info(conn_id: str, db_file: str) -> ConnectionInfo:
    return ConnectionInfo(
        conn_id=conn_id,
        db_type="sqlite",
        host="",
        port=0,
        database=db_file,
        user="",
        password="",
    )


def _bq_info(conn_id: str) -> ConnectionInfo:
    return ConnectionInfo(
        conn_id=conn_id,
        db_type="bigquery",
        host="",
        port=0,
        database="",
        user="",
        password="",
        project_id="my-project",
        dataset="my_dataset",
    )


class TestGetContextForQuestion:
    """get_context_for_question 테스트."""

    def test_unknown_conn_id_returns_error(self):
        """conn_id 없음 → [ERROR] 반환."""
        result = get_context_for_question("conn_nonexistent", "사용자 수를 알려줘")
        assert result.startswith("[ERROR]")
        assert "conn_nonexistent" in result

    def test_sqlite_keyword_matching(self, tmp_path):
        """SQLite에서 질문 키워드로 테이블 매칭."""
        db_file = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_file)
        conn.execute("CREATE TABLE orders (id INTEGER, amount REAL)")
        conn.execute("INSERT INTO orders VALUES (1, 100.0)")
        conn.commit()
        conn.close()

        conn_id = "conn_ctx_sqlite01"
        _connections[conn_id] = _sqlite_info(conn_id, db_file)
        try:
            result = get_context_for_question(conn_id, "orders 테이블 알려줘")
            assert "orders" in result
            assert "id" in result or "amount" in result
        finally:
            del _connections[conn_id]

    def test_sqlite_no_match_returns_all_tables(self, tmp_path):
        """키워드 미매칭 시 전체 테이블(최대 5개) 반환."""
        db_file = str(tmp_path / "test2.db")
        conn = sqlite3.connect(db_file)
        conn.execute("CREATE TABLE users (id INTEGER, name TEXT)")
        conn.commit()
        conn.close()

        conn_id = "conn_ctx_sqlite02"
        _connections[conn_id] = _sqlite_info(conn_id, db_file)
        try:
            result = get_context_for_question(conn_id, "전혀 다른 질문")
            assert "users" in result
        finally:
            del _connections[conn_id]

    def test_bigquery_support(self):
        """BigQuery conn_id 등록 시 클라이언트 mock 호출."""
        conn_id = "conn_ctx_bq01"
        _connections[conn_id] = _bq_info(conn_id)
        try:
            mock_table = MagicMock()
            mock_table.table_id = "sales"
            mock_bq_table = MagicMock()
            field = MagicMock()
            field.name = "id"
            field.field_type = "INTEGER"
            mock_bq_table.schema = [field]

            mock_client = MagicMock()
            mock_client.list_tables.return_value = [mock_table]
            mock_client.get_table.return_value = mock_bq_table
            mock_client.query.return_value.result.return_value = []

            with patch("bi_agent_mcp.tools.context._get_conn", return_value=mock_client):
                result = get_context_for_question(conn_id, "sales 데이터 알려줘")
            assert "sales" in result
        finally:
            del _connections[conn_id]

    def test_no_tables_returns_error(self, tmp_path):
        """테이블 없는 DB → [ERROR] 반환."""
        db_file = str(tmp_path / "empty.db")
        sqlite3.connect(db_file).close()

        conn_id = "conn_ctx_empty"
        _connections[conn_id] = _sqlite_info(conn_id, db_file)
        try:
            result = get_context_for_question(conn_id, "주문 알려줘")
            assert "[ERROR]" in result
        finally:
            del _connections[conn_id]


class TestGetTableRelationships:
    """get_table_relationships 테스트."""

    def test_unknown_conn_id_returns_error(self):
        """conn_id 없음 → [ERROR] 반환."""
        result = get_table_relationships("conn_nonexistent")
        assert result.startswith("[ERROR]")

    def test_postgresql_fk_mock(self):
        """PostgreSQL FK 조회 mock 테스트."""
        conn_id = "conn_rel_pg01"
        _connections[conn_id] = ConnectionInfo(
            conn_id=conn_id,
            db_type="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            user="user",
            password="pass",
        )
        try:
            mock_cur = MagicMock()
            mock_cur.fetchall.return_value = [
                ("orders", "user_id", "users", "id")
            ]
            mock_conn = MagicMock()
            mock_conn.cursor.return_value = mock_cur

            with patch("bi_agent_mcp.tools.context._get_conn", return_value=mock_conn):
                result = get_table_relationships(conn_id)
            assert "erDiagram" in result
            assert "orders" in result
            assert "users" in result
        finally:
            del _connections[conn_id]

    def test_mysql_fk_mock(self):
        """MySQL FK 조회 mock 테스트."""
        conn_id = "conn_rel_mysql01"
        _connections[conn_id] = ConnectionInfo(
            conn_id=conn_id,
            db_type="mysql",
            host="localhost",
            port=3306,
            database="testdb",
            user="user",
            password="pass",
        )
        try:
            mock_cur = MagicMock()
            mock_cur.fetchall.return_value = [
                ("items", "order_id", "orders", "id")
            ]
            mock_conn = MagicMock()
            mock_conn.cursor.return_value = mock_cur

            with patch("bi_agent_mcp.tools.context._get_conn", return_value=mock_conn):
                result = get_table_relationships(conn_id)
            assert "erDiagram" in result
            assert "items" in result
            assert "orders" in result
        finally:
            del _connections[conn_id]

    def test_sqlite_pragma_mock(self, tmp_path):
        """SQLite PRAGMA foreign_key_list — 실제 FK 포함 DB로 테스트."""
        db_file = str(tmp_path / "fk_test.db")
        conn = sqlite3.connect(db_file)
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute(
            "CREATE TABLE orders ("
            "  id INTEGER PRIMARY KEY,"
            "  user_id INTEGER,"
            "  FOREIGN KEY(user_id) REFERENCES users(id)"
            ")"
        )
        conn.commit()
        conn.close()

        conn_id = "conn_rel_sqlite01"
        _connections[conn_id] = _sqlite_info(conn_id, db_file)
        try:
            result = get_table_relationships(conn_id)
            assert "erDiagram" in result
            assert "orders" in result
            assert "users" in result
        finally:
            del _connections[conn_id]

    def test_bigquery_not_supported(self):
        """BigQuery는 FK 미지원 메시지 반환."""
        conn_id = "conn_rel_bq01"
        _connections[conn_id] = _bq_info(conn_id)
        try:
            result = get_table_relationships(conn_id)
            assert "BigQuery" in result
            assert "FK" in result or "외래 키" in result or "지원하지 않" in result
        finally:
            del _connections[conn_id]

    def test_no_fk_returns_message(self, tmp_path):
        """FK 없는 DB → 관계 없음 메시지 반환."""
        db_file = str(tmp_path / "no_fk.db")
        conn = sqlite3.connect(db_file)
        conn.execute("CREATE TABLE standalone (id INTEGER, val TEXT)")
        conn.commit()
        conn.close()

        conn_id = "conn_rel_nofk"
        _connections[conn_id] = _sqlite_info(conn_id, db_file)
        try:
            result = get_table_relationships(conn_id)
            assert "[ERROR]" not in result
            assert "erDiagram" not in result
        finally:
            del _connections[conn_id]

    def test_snowflake_fk_mock(self):
        """Snowflake FK 조회 mock 테스트 (lines 305-334)."""
        conn_id = "conn_rel_sf01"
        _connections[conn_id] = ConnectionInfo(
            conn_id=conn_id,
            db_type="snowflake",
            host="account.snowflakecomputing.com",
            port=443,
            database="testdb",
            user="user",
            password="pass",
        )
        try:
            mock_cur = MagicMock()
            mock_cur.fetchall.return_value = [
                ("fk_name", "orders", "user_id", "users", "id")
            ]
            mock_conn = MagicMock()
            mock_conn.cursor.return_value = mock_cur

            with patch("bi_agent_mcp.tools.context._get_conn", return_value=mock_conn):
                result = get_table_relationships(conn_id)
            assert "erDiagram" in result
            assert "orders" in result
        finally:
            del _connections[conn_id]

    def test_relationship_fetch_exception(self):
        """get_table_relationships에서 예외 발생 → [ERROR] 반환 (lines 349-350)."""
        conn_id = "conn_rel_exc"
        _connections[conn_id] = ConnectionInfo(
            conn_id=conn_id,
            db_type="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            user="user",
            password="pass",
        )
        try:
            with patch("bi_agent_mcp.tools.context._get_conn", side_effect=Exception("연결 실패")):
                result = get_table_relationships(conn_id)
            assert "[ERROR]" in result
        finally:
            del _connections[conn_id]


class TestGetContextPostgreSQLMySQL:
    """PostgreSQL/MySQL/Snowflake 브랜치 커버리지 테스트."""

    def _pg_info(self, conn_id: str) -> "ConnectionInfo":
        from bi_agent_mcp.tools.db import ConnectionInfo
        return ConnectionInfo(
            conn_id=conn_id, db_type="postgresql",
            host="localhost", port=5432, database="db", user="u", password="p",
        )

    def _mysql_info(self, conn_id: str) -> "ConnectionInfo":
        from bi_agent_mcp.tools.db import ConnectionInfo
        return ConnectionInfo(
            conn_id=conn_id, db_type="mysql",
            host="localhost", port=3306, database="db", user="u", password="p",
        )

    def _sf_info(self, conn_id: str) -> "ConnectionInfo":
        from bi_agent_mcp.tools.db import ConnectionInfo
        return ConnectionInfo(
            conn_id=conn_id, db_type="snowflake",
            host="acct.snowflakecomputing.com", port=443,
            database="db", user="u", password="p",
        )

    def test_postgresql_list_and_schema(self):
        """PostgreSQL _list_tables + _get_table_schema_and_sample (lines 26-35, 84-98)."""
        conn_id = "conn_ctx_pg_ls"
        _connections[conn_id] = self._pg_info(conn_id)
        try:
            list_cur = MagicMock()
            list_cur.fetchall.return_value = [("orders",)]
            list_conn = MagicMock()
            list_conn.cursor.return_value = list_cur

            schema_cur = MagicMock()
            schema_cur.fetchall.side_effect = [
                [("id", "integer"), ("amount", "numeric")],
                [(1, 100.0)],
            ]
            schema_conn = MagicMock()
            schema_conn.cursor.return_value = schema_cur

            with patch("bi_agent_mcp.tools.context._get_conn", side_effect=[list_conn, schema_conn]):
                result = get_context_for_question(conn_id, "orders 알려줘")
            assert "orders" in result
        finally:
            del _connections[conn_id]

    def test_mysql_list_and_schema(self):
        """MySQL _list_tables + _get_table_schema_and_sample (lines 38-47, 101-120)."""
        conn_id = "conn_ctx_mysql_ls"
        _connections[conn_id] = self._mysql_info(conn_id)
        try:
            list_cur = MagicMock()
            list_cur.fetchall.return_value = [("sales",)]
            list_conn = MagicMock()
            list_conn.cursor.return_value = list_cur

            schema_cur = MagicMock()
            schema_cur.fetchall.side_effect = [
                [("id", "int"), ("name", "varchar")],
                [(1, "test")],
            ]
            schema_conn = MagicMock()
            schema_conn.cursor.return_value = schema_cur

            with patch("bi_agent_mcp.tools.context._get_conn", side_effect=[list_conn, schema_conn]):
                result = get_context_for_question(conn_id, "sales 알려줘")
            assert "sales" in result
        finally:
            del _connections[conn_id]

    def test_snowflake_list_and_schema(self):
        """Snowflake _list_tables + _get_table_schema_and_sample (lines 54-63, 131-143)."""
        conn_id = "conn_ctx_sf_ls"
        _connections[conn_id] = self._sf_info(conn_id)
        try:
            list_cur = MagicMock()
            list_cur.fetchall.return_value = [("row0", "products")]
            list_conn = MagicMock()
            list_conn.cursor.return_value = list_cur

            schema_cur = MagicMock()
            schema_cur.fetchall.side_effect = [
                [("id", "NUMBER"), ("title", "VARCHAR")],
                [(1, "item")],
            ]
            schema_conn = MagicMock()
            schema_conn.cursor.return_value = schema_cur

            with patch("bi_agent_mcp.tools.context._get_conn", side_effect=[list_conn, schema_conn]):
                result = get_context_for_question(conn_id, "products 알려줘")
            assert "products" in result
        finally:
            del _connections[conn_id]

    def test_list_tables_exception_returns_error(self, tmp_path):
        """_list_tables 예외 → [ERROR] 반환 (lines 207-208)."""
        conn_id = "conn_ctx_exc_list"
        _connections[conn_id] = self._pg_info(conn_id)
        try:
            with patch("bi_agent_mcp.tools.context._get_conn", side_effect=RuntimeError("timeout")):
                result = get_context_for_question(conn_id, "주문 알려줘")
            assert "[ERROR]" in result
            assert "테이블 목록" in result
        finally:
            del _connections[conn_id]

    def test_schema_fetch_exception_appends_error(self):
        """_get_table_schema_and_sample 예외 → 오류 행 추가 (lines 220-221)."""
        conn_id = "conn_ctx_exc_schema"
        _connections[conn_id] = self._pg_info(conn_id)
        try:
            list_cur = MagicMock()
            list_cur.fetchall.return_value = [("orders",)]
            list_conn = MagicMock()
            list_conn.cursor.return_value = list_cur

            # 두 번째 _get_conn 호출에서 예외 발생
            schema_conn = MagicMock()
            schema_conn.cursor.side_effect = Exception("schema 오류")

            with patch("bi_agent_mcp.tools.context._get_conn", side_effect=[list_conn, schema_conn]):
                result = get_context_for_question(conn_id, "orders 알려줘")
            assert "orders" in result
            assert "오류" in result
        finally:
            del _connections[conn_id]

    def test_short_word_skipped_in_matching(self, tmp_path):
        """1글자 단어는 매칭 제외 (line 154 continue)."""
        db_file = str(tmp_path / "short_word.db")
        conn = sqlite3.connect(db_file)
        conn.execute("CREATE TABLE orders (id INTEGER)")
        conn.commit()
        conn.close()

        conn_id = "conn_ctx_short_word"
        _connections[conn_id] = _sqlite_info(conn_id, db_file)
        try:
            # "a"는 1글자라 skip, "orders"는 매칭
            result = get_context_for_question(conn_id, "a orders 알려줘")
            assert "orders" in result
        finally:
            del _connections[conn_id]

    def test_mysql_dict_rows_in_schema(self):
        """MySQL dict 형태 row 처리 (lines 101-120 dict branch)."""
        conn_id = "conn_ctx_mysql_dict"
        _connections[conn_id] = self._mysql_info(conn_id)
        try:
            list_cur = MagicMock()
            list_cur.fetchall.return_value = [{"table_name": "users"}]
            list_conn = MagicMock()
            list_conn.cursor.return_value = list_cur

            schema_cur = MagicMock()
            schema_cur.fetchall.side_effect = [
                [{"column_name": "id", "data_type": "int"}],
                [{"id": 1}],
            ]
            schema_conn = MagicMock()
            schema_conn.cursor.return_value = schema_cur

            with patch("bi_agent_mcp.tools.context._get_conn", side_effect=[list_conn, schema_conn]):
                result = get_context_for_question(conn_id, "users 알려줘")
            assert "users" in result
        finally:
            del _connections[conn_id]
