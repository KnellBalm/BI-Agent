"""bi_agent_mcp.tools.db 보안 검증 함수 단위 테스트."""
import pytest
from bi_agent_mcp.tools.db import _validate_select, _validate_identifier


class TestValidateSelect:
    """_validate_select SQL injection 벡터 10개 이상 커버."""

    def test_drop_table_rejected(self):
        assert _validate_select("DROP TABLE users") is not None

    def test_delete_rejected(self):
        assert _validate_select("SELECT * FROM t; DELETE FROM t") is not None

    def test_insert_rejected(self):
        assert _validate_select("INSERT INTO t VALUES(1)") is not None

    def test_update_rejected(self):
        assert _validate_select("UPDATE t SET x=1") is not None

    def test_create_rejected(self):
        assert _validate_select("CREATE TABLE hack(id INT)") is not None

    def test_truncate_rejected(self):
        assert _validate_select("TRUNCATE TABLE t") is not None

    def test_alter_rejected(self):
        assert _validate_select("ALTER TABLE t ADD COLUMN x INT") is not None

    def test_select_with_drop_in_subquery_rejected(self):
        assert _validate_select("SELECT * FROM t WHERE DROP=1") is not None

    def test_select_with_delete_keyword_rejected(self):
        assert _validate_select("SELECT DELETE FROM t") is not None

    def test_empty_string_rejected(self):
        assert _validate_select("") is not None

    def test_select_lowercase_passes(self):
        assert _validate_select("  select * from t  ") is None

    def test_select_1_passes(self):
        assert _validate_select("SELECT 1") is None

    def test_select_with_where_passes(self):
        assert _validate_select("SELECT id, name FROM users WHERE active = 1") is None

    def test_select_with_join_passes(self):
        assert _validate_select("SELECT a.id FROM a JOIN b ON a.id = b.id") is None


class TestValidateIdentifier:
    """_validate_identifier 정규식 검증."""

    def test_valid_simple_name(self):
        assert _validate_identifier("users") is None

    def test_valid_with_underscore(self):
        assert _validate_identifier("my_table") is None

    def test_valid_with_dollar(self):
        assert _validate_identifier("col$1") is None

    def test_valid_with_dot(self):
        assert _validate_identifier("schema.table") is None

    def test_valid_starts_with_underscore(self):
        assert _validate_identifier("_private") is None

    def test_invalid_starts_with_number(self):
        assert _validate_identifier("1table") is not None

    def test_invalid_backtick(self):
        assert _validate_identifier("`users`") is not None

    def test_invalid_semicolon(self):
        assert _validate_identifier("users; DROP TABLE users") is not None

    def test_invalid_space(self):
        assert _validate_identifier("my table") is not None

    def test_invalid_dash(self):
        assert _validate_identifier("my-table") is not None

    def test_invalid_quote(self):
        assert _validate_identifier("users'") is not None
