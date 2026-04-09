"""
Metabase 연동 도구 단위 테스트.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from bi_agent_mcp.tools.metabase import (
    connect_metabase,
    list_metabase_dashboards,
    list_metabase_questions,
    run_metabase_question,
)


# ---------------------------------------------------------------------------
# connect_metabase
# ---------------------------------------------------------------------------

class TestConnectMetabase:
    def test_success(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "test-session-token"}

        with patch("bi_agent_mcp.tools.metabase.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.post.return_value = mock_resp

            result = connect_metabase(
                url="http://localhost:3000",
                username="admin@test.com",
                password="secret",
                conn_id="test",
            )

        assert "[SUCCESS]" in result
        assert "test" in result

    def test_auth_failure(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 401

        with patch("bi_agent_mcp.tools.metabase.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.post.return_value = mock_resp

            result = connect_metabase(
                url="http://localhost:3000",
                username="bad@test.com",
                password="wrong",
            )

        assert "[ERROR]" in result
        assert "인증 실패" in result

    def test_network_error(self):
        import httpx as _httpx

        with patch("bi_agent_mcp.tools.metabase.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.post.side_effect = _httpx.RequestError("connection refused")

            result = connect_metabase(
                url="http://localhost:3000",
                username="admin@test.com",
                password="secret",
            )

        assert "[ERROR]" in result
        assert "네트워크 오류" in result

    def test_missing_token_in_response(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {}  # 토큰 없음

        with patch("bi_agent_mcp.tools.metabase.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.post.return_value = mock_resp

            result = connect_metabase(
                url="http://localhost:3000",
                username="admin@test.com",
                password="secret",
            )

        assert "[ERROR]" in result
        assert "토큰" in result


# ---------------------------------------------------------------------------
# list_metabase_questions
# ---------------------------------------------------------------------------

class TestListMetabaseQuestions:
    def _setup_conn(self, conn_id="test"):
        import bi_agent_mcp.tools.metabase as m
        m._metabase_connections[conn_id] = {
            "url": "http://localhost:3000",
            "token": "test-token",
        }

    def test_success(self):
        self._setup_conn()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"id": 1, "name": "Daily Revenue", "database_id": 1, "updated_at": "2026-03-01T00:00:00"},
            {"id": 2, "name": "User Funnel", "database_id": 1, "updated_at": "2026-03-02T00:00:00"},
        ]

        with patch("bi_agent_mcp.tools.metabase.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_resp

            result = list_metabase_questions("test")

        assert "Daily Revenue" in result
        assert "User Funnel" in result

    def test_no_connection(self):
        result = list_metabase_questions("nonexistent")
        assert "[ERROR]" in result
        assert "nonexistent" in result

    def test_filter_by_collection(self):
        self._setup_conn("col_test")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"id": 1, "name": "Q1", "collection_id": 10, "database_id": 1, "updated_at": ""},
            {"id": 2, "name": "Q2", "collection_id": 20, "database_id": 1, "updated_at": ""},
        ]

        with patch("bi_agent_mcp.tools.metabase.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_resp

            result = list_metabase_questions("col_test", collection_id=10)

        assert "Q1" in result
        assert "Q2" not in result

    def test_auth_error(self):
        self._setup_conn("auth_test")
        mock_resp = MagicMock()
        mock_resp.status_code = 401

        with patch("bi_agent_mcp.tools.metabase.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_resp

            result = list_metabase_questions("auth_test")

        assert "[ERROR]" in result
        assert "인증 만료" in result


# ---------------------------------------------------------------------------
# run_metabase_question
# ---------------------------------------------------------------------------

class TestRunMetabaseQuestion:
    def _setup_conn(self, conn_id="test"):
        import bi_agent_mcp.tools.metabase as m
        m._metabase_connections[conn_id] = {
            "url": "http://localhost:3000",
            "token": "test-token",
        }

    def test_success(self):
        self._setup_conn()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"date": "2026-03-01", "revenue": 1000},
            {"date": "2026-03-02", "revenue": 1200},
        ]

        with patch("bi_agent_mcp.tools.metabase.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.post.return_value = mock_resp

            result = run_metabase_question("test", card_id=1)

        assert "date" in result
        assert "revenue" in result
        assert "1000" in result

    def test_no_connection(self):
        result = run_metabase_question("nonexistent", card_id=1)
        assert "[ERROR]" in result
        assert "nonexistent" in result

    def test_card_not_found(self):
        self._setup_conn("nf_test")
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        with patch("bi_agent_mcp.tools.metabase.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.post.return_value = mock_resp

            result = run_metabase_question("nf_test", card_id=999)

        assert "[ERROR]" in result
        assert "999" in result

    def test_invalid_parameters_json(self):
        self._setup_conn("json_test")
        result = run_metabase_question("json_test", card_id=1, parameters="not-json")
        assert "[ERROR]" in result
        assert "JSON" in result

    def test_empty_result(self):
        self._setup_conn("empty_test")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []

        with patch("bi_agent_mcp.tools.metabase.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.post.return_value = mock_resp

            result = run_metabase_question("empty_test", card_id=1)

        assert "결과가 없습니다" in result


# ---------------------------------------------------------------------------
# list_metabase_dashboards
# ---------------------------------------------------------------------------

class TestListMetabaseDashboards:
    def _setup_conn(self, conn_id="test"):
        import bi_agent_mcp.tools.metabase as m
        m._metabase_connections[conn_id] = {
            "url": "http://localhost:3000",
            "token": "test-token",
        }

    def test_success(self):
        self._setup_conn()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"id": 1, "name": "Executive Overview", "updated_at": "2026-03-10T00:00:00"},
            {"id": 2, "name": "Marketing KPIs", "updated_at": "2026-03-11T00:00:00"},
        ]

        with patch("bi_agent_mcp.tools.metabase.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_resp

            result = list_metabase_dashboards("test")

        assert "Executive Overview" in result
        assert "Marketing KPIs" in result

    def test_no_connection(self):
        result = list_metabase_dashboards("nonexistent")
        assert "[ERROR]" in result
        assert "nonexistent" in result

    def test_empty_dashboards(self):
        self._setup_conn("empty_dash")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []

        with patch("bi_agent_mcp.tools.metabase.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_resp

            result = list_metabase_dashboards("empty_dash")

        assert "없습니다" in result

    def test_http_error(self):
        self._setup_conn("err_test")
        mock_resp = MagicMock()
        mock_resp.status_code = 500

        with patch("bi_agent_mcp.tools.metabase.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_resp

            result = list_metabase_dashboards("err_test")

        assert "[ERROR]" in result
        assert "500" in result


# ---------------------------------------------------------------------------
# Phase 3a: 신규 4개 함수 테스트
# ---------------------------------------------------------------------------

from bi_agent_mcp.tools.metabase import (
    list_metabase_collections,
    get_metabase_card_data,
    refresh_metabase_cache,
    run_metabase_adhoc_sql,
)


def _make_mb_mock(status=200, json_data=None, text=""):
    mock_resp = MagicMock()
    mock_resp.status_code = status
    mock_resp.json.return_value = json_data or {}
    mock_resp.text = text

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_resp
    mock_client.post.return_value = mock_resp
    return mock_client


def test_list_metabase_collections_returns_collection_list():
    data = {
        "data": [
            {"id": 1, "name": "Our analytics", "location": "/"},
            {"id": 5, "name": "Marketing", "location": "/1/"},
        ]
    }
    mock_client = _make_mb_mock(json_data=data)
    store = {"test": {"url": "http://mb:3000", "token": "abc123"}}

    with patch("bi_agent_mcp.tools.metabase._metabase_connections", store), \
         patch("bi_agent_mcp.tools.metabase.httpx.Client", return_value=mock_client):
        result = list_metabase_collections("test")

    assert "Our analytics" in result
    assert "Marketing" in result


def test_get_metabase_card_data_returns_table():
    data = {
        "data": {
            "cols": [{"display_name": "date"}, {"display_name": "revenue"}],
            "rows": [["2026-04-01", 1000000], ["2026-04-02", 1200000]],
        }
    }
    mock_client = _make_mb_mock(json_data=data)
    store = {"test": {"url": "http://mb:3000", "token": "abc123"}}

    with patch("bi_agent_mcp.tools.metabase._metabase_connections", store), \
         patch("bi_agent_mcp.tools.metabase.httpx.Client", return_value=mock_client):
        result = get_metabase_card_data("test", 42)

    assert "date" in result or "revenue" in result
    assert "1000000" in result or "revenue" in result


def test_refresh_metabase_cache_returns_ok():
    mock_client = _make_mb_mock(status=202)
    store = {"test": {"url": "http://mb:3000", "token": "abc123"}}

    with patch("bi_agent_mcp.tools.metabase._metabase_connections", store), \
         patch("bi_agent_mcp.tools.metabase.httpx.Client", return_value=mock_client):
        result = refresh_metabase_cache("test", 42)

    assert "[OK]" in result


def test_run_metabase_adhoc_sql_returns_results():
    data = {
        "data": {
            "cols": [{"display_name": "cnt"}],
            "rows": [[99]],
        }
    }
    mock_client = _make_mb_mock(json_data=data)
    store = {"test": {"url": "http://mb:3000", "token": "abc123"}}

    with patch("bi_agent_mcp.tools.metabase._metabase_connections", store), \
         patch("bi_agent_mcp.tools.metabase.httpx.Client", return_value=mock_client):
        result = run_metabase_adhoc_sql("test", 1, "SELECT COUNT(*) AS cnt FROM orders")

    assert "99" in result or "cnt" in result


def test_run_metabase_adhoc_sql_blocks_dml():
    store = {"test": {"url": "http://mb:3000", "token": "abc123"}}
    with patch("bi_agent_mcp.tools.metabase._metabase_connections", store):
        result = run_metabase_adhoc_sql("test", 1, "DROP TABLE orders")
    assert "[ERROR]" in result
