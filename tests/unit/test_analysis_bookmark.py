"""bi_agent_mcp.tools.analysis — search/run/delete_saved_query 단위 테스트."""
import json
from unittest.mock import patch, MagicMock
import pytest

from bi_agent_mcp.tools.analysis import (
    search_saved_queries,
    run_saved_query,
    delete_saved_query,
)


def _write_queries(path, data: dict):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


SAMPLE_QUERIES = {
    "월별매출": {
        "sql": "SELECT month, SUM(amount) FROM sales GROUP BY month",
        "connection_id": "conn_pg",
        "saved_at": "2026-01-01 00:00:00",
        "tags": ["매출", "월별"],
        "description": "월별 매출 집계",
        "parameters": {},
    },
    "user_detail": {
        "sql": "SELECT * FROM users WHERE id = {user_id}",
        "connection_id": "conn_pg",
        "saved_at": "2026-01-02 00:00:00",
        "tags": ["사용자", "상세"],
        "description": "특정 사용자 상세 조회",
        "parameters": {"user_id": "사용자 ID"},
    },
    "daily_orders": {
        "sql": "SELECT date, COUNT(*) FROM orders GROUP BY date",
        "connection_id": "conn_mysql",
        "saved_at": "2026-01-03 00:00:00",
        "tags": ["주문", "일별"],
        "description": "일별 주문 수",
        "parameters": {},
    },
}


# ─── search_saved_queries ────────────────────────────────────────────────────

class TestSearchSavedQueries:
    def test_keyword_case_insensitive(self, tmp_path):
        qf = tmp_path / "saved_queries.json"
        _write_queries(qf, SAMPLE_QUERIES)
        with patch("bi_agent_mcp.tools.analysis.QUERIES_FILE", qf):
            result = search_saved_queries(keyword="MONTHLY")  # 대문자
        # "월별매출"의 sql에 "month"가 있으므로 매칭 없음, 이름도 없으므로 검색 결과 없음
        # keyword "sales"는 sql에 존재
        with patch("bi_agent_mcp.tools.analysis.QUERIES_FILE", qf):
            result = search_saved_queries(keyword="sales")
        assert "월별매출" in result

    def test_keyword_name_match(self, tmp_path):
        qf = tmp_path / "saved_queries.json"
        _write_queries(qf, SAMPLE_QUERIES)
        with patch("bi_agent_mcp.tools.analysis.QUERIES_FILE", qf):
            result = search_saved_queries(keyword="월별")
        assert "월별매출" in result
        assert "daily_orders" not in result

    def test_keyword_sql_match(self, tmp_path):
        qf = tmp_path / "saved_queries.json"
        _write_queries(qf, SAMPLE_QUERIES)
        with patch("bi_agent_mcp.tools.analysis.QUERIES_FILE", qf):
            result = search_saved_queries(keyword="users")
        assert "user_detail" in result

    def test_tags_and_filter(self, tmp_path):
        qf = tmp_path / "saved_queries.json"
        _write_queries(qf, SAMPLE_QUERIES)
        with patch("bi_agent_mcp.tools.analysis.QUERIES_FILE", qf):
            result = search_saved_queries(tags=["매출", "월별"])
        assert "월별매출" in result
        assert "daily_orders" not in result

    def test_tags_partial_not_matched(self, tmp_path):
        qf = tmp_path / "saved_queries.json"
        _write_queries(qf, SAMPLE_QUERIES)
        with patch("bi_agent_mcp.tools.analysis.QUERIES_FILE", qf):
            result = search_saved_queries(tags=["매출", "일별"])
        assert "검색 결과가 없습니다" in result

    def test_empty_result(self, tmp_path):
        qf = tmp_path / "saved_queries.json"
        _write_queries(qf, SAMPLE_QUERIES)
        with patch("bi_agent_mcp.tools.analysis.QUERIES_FILE", qf):
            result = search_saved_queries(keyword="nonexistent_xyz_keyword")
        assert "없습니다" in result

    def test_no_queries_file_returns_empty_message(self, tmp_path):
        qf = tmp_path / "no_such.json"
        with patch("bi_agent_mcp.tools.analysis.QUERIES_FILE", qf):
            result = search_saved_queries(keyword="anything")
        assert "없습니다" in result

    def test_no_keyword_returns_all(self, tmp_path):
        qf = tmp_path / "saved_queries.json"
        _write_queries(qf, SAMPLE_QUERIES)
        with patch("bi_agent_mcp.tools.analysis.QUERIES_FILE", qf):
            result = search_saved_queries()
        assert "월별매출" in result
        assert "user_detail" in result
        assert "daily_orders" in result


# ─── run_saved_query ─────────────────────────────────────────────────────────

class TestRunSavedQuery:
    def test_normal_execution(self, tmp_path):
        qf = tmp_path / "saved_queries.json"
        _write_queries(qf, SAMPLE_QUERIES)
        mock_result = "| date | count |\n|------|-------|\n| 2026-01-01 | 5 |"
        with patch("bi_agent_mcp.tools.analysis.QUERIES_FILE", qf), \
             patch("bi_agent_mcp.tools.db.run_query", return_value=mock_result) as mock_rq:
            result = run_saved_query("daily_orders", "conn_mysql")
        assert "2026-01-01" in result

    def test_params_binding(self, tmp_path):
        qf = tmp_path / "saved_queries.json"
        _write_queries(qf, SAMPLE_QUERIES)
        captured = {}

        def fake_run_query(conn_id, sql):
            captured["sql"] = sql
            return "| id |\n|----|"

        with patch("bi_agent_mcp.tools.analysis.QUERIES_FILE", qf), \
             patch("bi_agent_mcp.tools.db.run_query", side_effect=fake_run_query):
            result = run_saved_query("user_detail", "conn_pg", params={"user_id": "42"})

        assert "42" in captured["sql"]
        assert "{user_id}" not in captured["sql"]

    def test_unknown_query_id_returns_error(self, tmp_path):
        qf = tmp_path / "saved_queries.json"
        _write_queries(qf, SAMPLE_QUERIES)
        with patch("bi_agent_mcp.tools.analysis.QUERIES_FILE", qf):
            result = run_saved_query("nonexistent_query", "conn_pg")
        assert "[ERROR]" in result

    def test_missing_param_returns_error(self, tmp_path):
        qf = tmp_path / "saved_queries.json"
        _write_queries(qf, SAMPLE_QUERIES)
        with patch("bi_agent_mcp.tools.analysis.QUERIES_FILE", qf):
            # user_id 파라미터를 넘기지 않으면 KeyError → [ERROR]
            result = run_saved_query("user_detail", "conn_pg", params={})
        assert "[ERROR]" in result


# ─── delete_saved_query ──────────────────────────────────────────────────────

class TestDeleteSavedQuery:
    def test_normal_deletion(self, tmp_path):
        qf = tmp_path / "saved_queries.json"
        _write_queries(qf, SAMPLE_QUERIES)
        with patch("bi_agent_mcp.tools.analysis.QUERIES_FILE", qf):
            result = delete_saved_query("daily_orders")
        assert "삭제" in result
        remaining = json.loads(qf.read_text(encoding="utf-8"))
        assert "daily_orders" not in remaining
        assert "월별매출" in remaining

    def test_unknown_query_id_returns_error(self, tmp_path):
        qf = tmp_path / "saved_queries.json"
        _write_queries(qf, SAMPLE_QUERIES)
        with patch("bi_agent_mcp.tools.analysis.QUERIES_FILE", qf):
            result = delete_saved_query("no_such_query")
        assert "[ERROR]" in result
        # 기존 데이터는 유지
        remaining = json.loads(qf.read_text(encoding="utf-8"))
        assert len(remaining) == 3

    def test_delete_write_failure_returns_error(self, tmp_path):
        qf = tmp_path / "saved_queries.json"
        _write_queries(qf, SAMPLE_QUERIES)
        with patch("bi_agent_mcp.tools.analysis.QUERIES_FILE", qf), \
             patch("bi_agent_mcp.tools.analysis._save_queries", side_effect=OSError("disk full")):
            result = delete_saved_query("daily_orders")
        assert "[ERROR]" in result
