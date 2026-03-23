"""bi_agent_mcp.tools.analysis 단위 테스트."""
import json
import pytest
from unittest.mock import patch
from pathlib import Path
from bi_agent_mcp.tools.analysis import save_query, list_saved_queries, suggest_analysis


class TestSaveQuery:
    def test_save_query_creates_json_file(self, tmp_path):
        queries_file = tmp_path / "saved_queries.json"
        with patch("bi_agent_mcp.tools.analysis.QUERIES_FILE", queries_file):
            result = save_query("test_query", "SELECT 1", "conn_abc")
        assert "[SUCCESS]" in result
        assert queries_file.exists()
        data = json.loads(queries_file.read_text(encoding="utf-8"))
        assert "test_query" in data
        assert data["test_query"]["sql"] == "SELECT 1"
        assert data["test_query"]["connection_id"] == "conn_abc"

    def test_save_query_overwrites_same_name(self, tmp_path):
        queries_file = tmp_path / "saved_queries.json"
        with patch("bi_agent_mcp.tools.analysis.QUERIES_FILE", queries_file):
            save_query("q1", "SELECT 1")
            save_query("q1", "SELECT 2")
        data = json.loads(queries_file.read_text(encoding="utf-8"))
        assert data["q1"]["sql"] == "SELECT 2"

    def test_save_query_multiple_entries(self, tmp_path):
        queries_file = tmp_path / "saved_queries.json"
        with patch("bi_agent_mcp.tools.analysis.QUERIES_FILE", queries_file):
            save_query("q1", "SELECT 1")
            save_query("q2", "SELECT 2")
        data = json.loads(queries_file.read_text(encoding="utf-8"))
        assert "q1" in data
        assert "q2" in data


class TestListSavedQueries:
    def test_no_file_returns_empty_message(self, tmp_path):
        queries_file = tmp_path / "no_such_file.json"
        with patch("bi_agent_mcp.tools.analysis.QUERIES_FILE", queries_file):
            result = list_saved_queries()
        assert "없습니다" in result

    def test_returns_markdown_table(self, tmp_path):
        queries_file = tmp_path / "saved_queries.json"
        queries_file.write_text(
            json.dumps({"월별매출": {"sql": "SELECT month, sum FROM sales", "connection_id": "conn_1", "saved_at": "2026-01-01 00:00:00"}}),
            encoding="utf-8"
        )
        with patch("bi_agent_mcp.tools.analysis.QUERIES_FILE", queries_file):
            result = list_saved_queries()
        assert "|" in result
        assert "월별매출" in result

    def test_empty_json_returns_empty_message(self, tmp_path):
        queries_file = tmp_path / "saved_queries.json"
        queries_file.write_text("{}", encoding="utf-8")
        with patch("bi_agent_mcp.tools.analysis.QUERIES_FILE", queries_file):
            result = list_saved_queries()
        assert "없습니다" in result


class TestSuggestAnalysis:
    def test_returns_string(self):
        result = suggest_analysis("users 테이블: id, name, created_at", "월별 신규 가입자 추이")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_question_in_response(self):
        question = "지역별 매출 비교"
        result = suggest_analysis("sales 테이블: region, amount", question)
        assert question in result

    def test_contains_structured_guide(self):
        result = suggest_analysis("orders 테이블", "주문 취소율 분석")
        assert "1." in result
        assert "2." in result
