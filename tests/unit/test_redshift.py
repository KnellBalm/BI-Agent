"""bi_agent_mcp.tools.redshift 단위 테스트."""
from unittest.mock import MagicMock, patch
import pytest


def _make_boto3_mock(temp_user="IAM:testuser", temp_password="AmazonAWS123"):
    mock_client = MagicMock()
    mock_client.get_cluster_credentials.return_value = {
        "DbUser": temp_user,
        "DbPassword": temp_password,
    }
    return mock_client


def _make_psycopg2_mock():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.description = [("id",), ("name",)]
    mock_cursor.fetchall.return_value = [(1, "Alice"), (2, "Bob")]
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn


def test_connect_redshift_stores_connection():
    mock_boto = _make_boto3_mock()
    mock_conn = _make_psycopg2_mock()

    with patch("bi_agent_mcp.tools.redshift._redshift_connections", {}) as store, \
         patch("bi_agent_mcp.tools.redshift.boto3.client", return_value=mock_boto), \
         patch("bi_agent_mcp.tools.redshift.psycopg2.connect", return_value=mock_conn):
        from bi_agent_mcp.tools.redshift import connect_redshift
        result = connect_redshift("my-cluster", "mydb", "testuser", "ap-northeast-2", "test")

    assert "[OK]" in result
    assert "test" in result


def test_connect_redshift_iam_failure_returns_error():
    mock_boto = MagicMock()
    mock_boto.get_cluster_credentials.side_effect = Exception("AccessDenied")

    with patch("bi_agent_mcp.tools.redshift.boto3.client", return_value=mock_boto):
        from bi_agent_mcp.tools.redshift import connect_redshift
        result = connect_redshift("bad-cluster", "db", "user")

    assert "[ERROR]" in result


def test_run_redshift_query_returns_markdown_table():
    mock_boto = _make_boto3_mock()
    mock_conn = _make_psycopg2_mock()
    store = {"test": {"cluster_id": "c", "database": "d", "user": "u", "region": "ap-northeast-2"}}

    with patch("bi_agent_mcp.tools.redshift._redshift_connections", store), \
         patch("bi_agent_mcp.tools.redshift.boto3.client", return_value=mock_boto), \
         patch("bi_agent_mcp.tools.redshift.psycopg2.connect", return_value=mock_conn):
        from bi_agent_mcp.tools.redshift import run_redshift_query
        result = run_redshift_query("test", "SELECT id, name FROM users")

    assert "id" in result
    assert "Alice" in result


def test_run_redshift_query_blocks_dml():
    store = {"test": {"cluster_id": "c", "database": "d", "user": "u", "region": "ap-northeast-2"}}
    with patch("bi_agent_mcp.tools.redshift._redshift_connections", store):
        from bi_agent_mcp.tools.redshift import run_redshift_query
        result = run_redshift_query("test", "DELETE FROM users")

    assert "[ERROR]" in result


def test_run_redshift_query_unknown_conn_id_returns_error():
    with patch("bi_agent_mcp.tools.redshift._redshift_connections", {}):
        from bi_agent_mcp.tools.redshift import run_redshift_query
        result = run_redshift_query("not_exist", "SELECT 1")

    assert "[ERROR]" in result


def test_get_redshift_schema_returns_column_info():
    mock_boto = _make_boto3_mock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.description = [("table_name",), ("column_name",), ("data_type",)]
    mock_cursor.fetchall.return_value = [
        ("orders", "id", "integer"),
        ("orders", "amount", "numeric"),
    ]
    mock_conn.cursor.return_value = mock_cursor
    store = {"test": {"cluster_id": "c", "database": "d", "user": "u", "region": "ap-northeast-2"}}

    with patch("bi_agent_mcp.tools.redshift._redshift_connections", store), \
         patch("bi_agent_mcp.tools.redshift.boto3.client", return_value=mock_boto), \
         patch("bi_agent_mcp.tools.redshift.psycopg2.connect", return_value=mock_conn):
        from bi_agent_mcp.tools.redshift import get_redshift_schema
        result = get_redshift_schema("test", "public")

    assert "orders" in result
    assert "amount" in result


def test_list_redshift_tables_returns_table_list():
    mock_boto = _make_boto3_mock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.description = [("schemaname",), ("tablename",), ("tableowner",)]
    mock_cursor.fetchall.return_value = [("public", "orders", "admin"), ("public", "users", "admin")]
    mock_conn.cursor.return_value = mock_cursor
    store = {"test": {"cluster_id": "c", "database": "d", "user": "u", "region": "ap-northeast-2"}}

    with patch("bi_agent_mcp.tools.redshift._redshift_connections", store), \
         patch("bi_agent_mcp.tools.redshift.boto3.client", return_value=mock_boto), \
         patch("bi_agent_mcp.tools.redshift.psycopg2.connect", return_value=mock_conn):
        from bi_agent_mcp.tools.redshift import list_redshift_tables
        result = list_redshift_tables("test")

    assert "orders" in result
    assert "users" in result


def test_get_redshift_schema_unknown_conn_id_returns_error():
    with patch("bi_agent_mcp.tools.redshift._redshift_connections", {}):
        from bi_agent_mcp.tools.redshift import get_redshift_schema
        result = get_redshift_schema("not_exist")

    assert "[ERROR]" in result
