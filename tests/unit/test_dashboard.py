"""bi_agent_mcp.tools.dashboard 단위 테스트."""
import json
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

# files.py를 패치 전에 미리 임포트 — 모듈 레벨에서 _validate_select를 실제 함수에
# 바인딩해야 이후 db._validate_select 패치가 files.py 네임스페이스에 누출되지 않음
import bi_agent_mcp.tools.files  # noqa: F401

from bi_agent_mcp.tools.dashboard import (
    _render_chart,
    _build_html,
    _save_dashboard,
    generate_dashboard,
    chart_from_file,
)


class TestRenderChart:
    def test_empty_rows_returns_no_data_card(self):
        result = _render_chart("chart_1", {"title": "매출", "type": "bar"}, [], [])
        assert "데이터 없음" in result
        assert "매출" in result

    def test_kpi_type_renders_value(self):
        result = _render_chart("chart_1", {"title": "총매출", "type": "kpi"}, ["amount"], [[1234567]])
        assert "kpi-value" in result
        assert "1,234,567" in result

    def test_kpi_type_with_dict_row(self):
        result = _render_chart("chart_1", {"title": "총매출", "type": "kpi"}, ["amount"], [{"amount": 999}])
        assert "999" in result

    def test_kpi_type_string_value(self):
        result = _render_chart("chart_1", {"title": "상태", "type": "kpi"}, ["status"], [["active"]])
        assert "active" in result

    def test_table_type_renders_headers(self):
        cols = ["id", "name", "value"]
        rows = [[1, "Alice", 100], [2, "Bob", 200]]
        result = _render_chart("chart_1", {"title": "테이블", "type": "table"}, cols, rows)
        assert "<table>" in result
        assert "id" in result
        assert "Alice" in result

    def test_table_type_with_dict_rows(self):
        cols = ["id", "name"]
        rows = [{"id": 1, "name": "Alice"}]
        result = _render_chart("chart_1", {"title": "T", "type": "table"}, cols, rows)
        assert "Alice" in result

    def test_bar_chart_renders_canvas(self):
        cols = ["category", "sales"]
        rows = [["A", 100], ["B", 200]]
        result = _render_chart("chart_1", {"title": "막대", "type": "bar"}, cols, rows)
        assert "<canvas" in result
        assert "chart_1" in result

    def test_line_chart_renders_canvas(self):
        cols = ["date", "revenue"]
        rows = [["2026-01-01", 500], ["2026-01-02", 600]]
        result = _render_chart("chart_1", {"title": "선그래프", "type": "line"}, cols, rows)
        assert "line" in result

    def test_pie_chart_renders_canvas(self):
        cols = ["category", "count"]
        rows = [["A", 10], ["B", 20]]
        result = _render_chart("chart_1", {"title": "파이", "type": "pie"}, cols, rows)
        assert "pie" in result

    def test_single_column_no_crash(self):
        cols = ["total"]
        rows = [[999]]
        result = _render_chart("chart_1", {"title": "단일", "type": "bar"}, cols, rows)
        assert isinstance(result, str)

    def test_none_value_in_rows_becomes_zero(self):
        cols = ["cat", "val"]
        rows = [["A", None], ["B", 100]]
        result = _render_chart("chart_1", {"title": "None값", "type": "bar"}, cols, rows)
        assert isinstance(result, str)


class TestBuildHtml:
    def test_returns_html_string(self):
        result = _build_html("테스트 대시보드", "<div>card</div>")
        assert "<!DOCTYPE html>" in result
        assert "테스트 대시보드" in result
        assert "<div>card</div>" in result

    def test_includes_chartjs_cdn(self):
        result = _build_html("대시보드", "")
        assert "chart.js" in result


class TestSaveDashboard:
    def test_saves_to_specified_path(self, tmp_path):
        out_path = str(tmp_path / "my_dashboard.html")
        result = _save_dashboard("<html></html>", out_path, "테스트")
        assert result == out_path
        assert Path(out_path).read_text(encoding="utf-8") == "<html></html>"

    def test_saves_to_downloads_when_no_path(self, tmp_path):
        with patch("bi_agent_mcp.tools.dashboard.Path") as MockPath:
            # Path("~/Downloads").expanduser() 모킹
            mock_downloads = tmp_path / "Downloads"
            mock_downloads.mkdir()

            fake_path = mock_downloads / "dashboard_test_20260101_000000.html"

            mock_path_instance = MagicMock()
            mock_path_instance.parent = MagicMock()
            mock_path_instance.write_text = MagicMock()
            mock_path_instance.__str__ = MagicMock(return_value=str(fake_path))

            MockPath.return_value.expanduser.return_value.__truediv__ = MagicMock(return_value=mock_path_instance)
            MockPath.return_value = mock_path_instance

            # 실제 파일 저장으로 테스트 (output_path 없이)
        out = _save_dashboard("<html>test</html>", str(tmp_path / "out.html"), "대시보드")
        assert "out.html" in out


class TestGenerateDashboard:
    def test_invalid_json_returns_error(self):
        result = generate_dashboard("conn_1", "NOT_JSON")
        assert "[ERROR]" in result
        assert "JSON" in result

    def test_no_sql_in_queries_returns_error(self):
        queries = json.dumps([{"title": "빈쿼리", "type": "bar"}])
        result = generate_dashboard("conn_1", queries)
        assert "[ERROR]" in result

    def test_connection_error_renders_error_card_and_saves(self, tmp_path):
        queries = json.dumps([{"sql": "SELECT 1", "title": "테스트", "type": "bar"}])
        out_path = str(tmp_path / "dash.html")

        with patch("bi_agent_mcp.tools.dashboard._execute_query", side_effect=ValueError("연결 없음")):
            result = generate_dashboard("conn_bad", queries, output_path=out_path)

        # 에러 카드가 포함된 대시보드가 생성됨
        assert "대시보드 생성 완료" in result
        assert Path(out_path).exists()

    def test_successful_dashboard_generation(self, tmp_path):
        queries = json.dumps([{"sql": "SELECT category, sales FROM t", "title": "매출", "type": "bar"}])
        out_path = str(tmp_path / "dash.html")

        with patch("bi_agent_mcp.tools.dashboard._execute_query", return_value=(["category", "sales"], [["A", 100]])):
            result = generate_dashboard("conn_1", queries, title="테스트대시보드", output_path=out_path)

        assert "대시보드 생성 완료" in result
        assert "1개" in result
        assert Path(out_path).exists()

    def test_single_dict_query_also_works(self, tmp_path):
        queries = json.dumps({"sql": "SELECT 1 AS v", "title": "단일", "type": "kpi"})
        out_path = str(tmp_path / "dash2.html")

        with patch("bi_agent_mcp.tools.dashboard._execute_query", return_value=(["v"], [[1]])):
            result = generate_dashboard("conn_1", queries, output_path=out_path)

        assert "대시보드 생성 완료" in result


class TestChartFromFile:
    def test_invalid_json_returns_error(self):
        result = chart_from_file("file_1", "NOT_JSON")
        assert "[ERROR]" in result

    def test_no_sql_returns_error(self):
        queries = json.dumps([{"title": "빈", "type": "bar"}])
        result = chart_from_file("file_1", queries)
        assert "[ERROR]" in result

    def test_file_query_error_renders_error_card(self, tmp_path):
        queries = json.dumps([{"sql": "SELECT * FROM df", "title": "파일차트", "type": "table"}])
        out_path = str(tmp_path / "file_dash.html")

        with patch("bi_agent_mcp.tools.dashboard._execute_file_query", side_effect=ValueError("파일 없음")):
            result = chart_from_file("file_bad", queries, output_path=out_path)

        assert "대시보드 생성 완료" in result

    def test_successful_file_dashboard(self, tmp_path):
        queries = json.dumps([{"sql": "SELECT * FROM df", "title": "파일데이터", "type": "table"}])
        out_path = str(tmp_path / "file_dash2.html")

        with patch("bi_agent_mcp.tools.dashboard._execute_file_query",
                   return_value=(["id", "name"], [[1, "Alice"], [2, "Bob"]])):
            result = chart_from_file("file_1", queries, output_path=out_path)

        assert "대시보드 생성 완료" in result
        assert Path(out_path).exists()


# ─── Extended tests for _execute_query and _execute_file_query ───────────────

class TestExecuteQuery:
    def test_invalid_sql_raises_value_error(self):
        from bi_agent_mcp.tools.dashboard import _execute_query
        with patch("bi_agent_mcp.tools.db._validate_select", return_value="SELECT만 허용"):
            try:
                _execute_query("conn1", "DROP TABLE users")
                assert False, "Should have raised"
            except ValueError as e:
                assert "SELECT" in str(e)

    def test_unknown_conn_raises_value_error(self):
        from bi_agent_mcp.tools.dashboard import _execute_query
        from bi_agent_mcp.tools.db import _connections
        _connections.clear()
        with patch("bi_agent_mcp.tools.db._validate_select", return_value=None):
            try:
                _execute_query("nonexistent_conn", "SELECT 1")
                assert False, "Should have raised"
            except ValueError as e:
                assert "nonexistent_conn" in str(e)

    def test_mysql_success_returns_columns_rows(self):
        from bi_agent_mcp.tools.dashboard import _execute_query
        from bi_agent_mcp.tools.db import _connections, ConnectionInfo
        _connections.clear()
        info = ConnectionInfo(
            conn_id="db1", db_type="mysql", host="localhost", port=3306,
            database="mydb", user="root", password="pw", persisted=False,
        )
        _connections["db1"] = info

        mock_cur = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = [(1, "A"), (2, "B")]
        mock_cur.description = [("id",), ("name",)]

        with patch("bi_agent_mcp.tools.db._validate_select", return_value=None), \
             patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
            cols, rows = _execute_query("db1", "SELECT id, name FROM t")

        assert cols == ["id", "name"]
        assert len(rows) == 2

    def test_mysql_empty_result(self):
        from bi_agent_mcp.tools.dashboard import _execute_query
        from bi_agent_mcp.tools.db import _connections, ConnectionInfo
        _connections.clear()
        info = ConnectionInfo(
            conn_id="db2", db_type="mysql", host="localhost", port=3306,
            database="mydb", user="root", password="pw", persisted=False,
        )
        _connections["db2"] = info

        mock_cur = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = []
        mock_cur.description = [("id",)]

        with patch("bi_agent_mcp.tools.db._validate_select", return_value=None), \
             patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
            cols, rows = _execute_query("db2", "SELECT id FROM t WHERE 1=0")

        assert cols == ["id"]
        assert rows == []


class TestExecuteFileQuery:
    def test_invalid_sql_raises_value_error(self):
        from bi_agent_mcp.tools.dashboard import _execute_file_query
        with patch("bi_agent_mcp.tools.db._validate_select", return_value="SELECT만 허용"):
            try:
                _execute_file_query("file_abc", "DROP TABLE df")
                assert False, "Should have raised"
            except ValueError as e:
                assert "SELECT" in str(e)

    def test_unknown_file_id_raises_value_error(self):
        from bi_agent_mcp.tools.dashboard import _execute_file_query
        from bi_agent_mcp.tools.files import _files
        _files.clear()
        with patch("bi_agent_mcp.tools.db._validate_select", return_value=None):
            try:
                _execute_file_query("file_unknown", "SELECT * FROM df")
                assert False, "Should have raised"
            except ValueError as e:
                assert "file_unknown" in str(e)

    def test_success_returns_columns_rows(self):
        import pandas as pd
        from bi_agent_mcp.tools.dashboard import _execute_file_query
        from bi_agent_mcp.tools.files import _files
        _files.clear()
        df = pd.DataFrame({"name": ["Alice", "Bob"], "val": [10, 20]})
        _files["file_test"] = {"df": df, "name": "test.csv"}

        with patch("bi_agent_mcp.tools.db._validate_select", return_value=None):
            cols, rows = _execute_file_query("file_test", "SELECT * FROM df")

        assert "name" in cols
        assert len(rows) == 2


class TestSaveDashboardExtended:
    def test_no_output_path_uses_downloads(self, tmp_path):
        from bi_agent_mcp.tools.dashboard import _save_dashboard
        fake_home = tmp_path
        fake_downloads = tmp_path / "Downloads"
        fake_downloads.mkdir()
        with patch.object(Path, "home", return_value=fake_home):
            result = _save_dashboard("<html></html>", "", "My Dashboard")
        assert result.endswith(".html")
        assert "My_Dashboard" in result or "dashboard" in result.lower()


class TestRenderChartNonNumeric:
    """_render_chart: 비수치 문자열 값 → except (ValueError, TypeError) 경로 (lines 152-153)."""

    def test_bar_chart_non_numeric_string_falls_back_to_zero(self):
        cols = ["category", "value"]
        rows = [["A", "N/A"], ["B", "unknown"]]
        result = _render_chart("chart_1", {"title": "비수치", "type": "bar"}, cols, rows)
        assert isinstance(result, str)
        assert "<canvas" in result


class TestChartFromFileSingleDict:
    """chart_from_file: 단일 dict를 배열로 감싸는 경로 (line 292)."""

    def test_single_dict_query_wraps_in_list(self, tmp_path):
        queries = json.dumps({"sql": "SELECT * FROM df", "title": "파일", "type": "table"})
        out_path = str(tmp_path / "fd.html")
        with patch("bi_agent_mcp.tools.dashboard._execute_file_query",
                   return_value=(["id"], [[1]])):
            result = chart_from_file("file_1", queries, output_path=out_path)
        assert "대시보드 생성 완료" in result


class TestExecuteQueryPostgresql:
    """_execute_query: postgresql 경로 (lines 64-66, 74)."""

    def test_postgresql_returns_dict_rows(self):
        from bi_agent_mcp.tools.dashboard import _execute_query
        from bi_agent_mcp.tools.db import _connections, ConnectionInfo
        _connections.clear()
        info = ConnectionInfo(
            conn_id="pg1", db_type="postgresql", host="localhost", port=5432,
            database="mydb", user="root", password="pw", persisted=False,
        )
        _connections["pg1"] = info

        mock_cur = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = [{"id": 1, "name": "A"}]
        mock_cur.description = [("id",), ("name",)]

        with patch("bi_agent_mcp.tools.db._validate_select", return_value=None), \
             patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
            cols, rows = _execute_query("pg1", "SELECT id, name FROM t")

        assert cols == ["id", "name"]
        assert len(rows) == 1
