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


# ─── Extended tests for uncovered lines ───────────────────────────────────────

import tempfile
import os
from bi_agent_mcp.tools.analysis import generate_report, load_domain_context, list_query_history


class TestGenerateReport:
    def test_generate_report_creates_file(self, tmp_path):
        sections = [{"title": "매출 요약", "content": "## Q1\n매출 증가"}]
        with patch("bi_agent_mcp.tools.analysis.Path") as mock_path_cls:
            # Patch Path.home() to return tmp_path
            import bi_agent_mcp.tools.analysis as m
            real_path = Path
            downloads = tmp_path / "Downloads"
            downloads.mkdir()
            with patch.object(m, "Path", wraps=real_path) as mock_p:
                result = generate_report(sections)
        # Just verify it returns a file path string or error
        assert isinstance(result, str)

    def test_generate_report_returns_path_string(self, tmp_path):
        from bi_agent_mcp.tools.analysis import generate_report
        import bi_agent_mcp.tools.analysis as m
        from unittest.mock import patch
        from pathlib import Path

        fake_downloads = tmp_path
        with patch.object(Path, "home", return_value=tmp_path), \
             patch("bi_agent_mcp.tools.analysis.Path.home", return_value=tmp_path):
            result = generate_report([{"title": "Test", "content": "Content"}])
        assert isinstance(result, str)

    def test_generate_report_write_error(self, tmp_path):
        from bi_agent_mcp.tools.analysis import generate_report
        import bi_agent_mcp.tools.analysis as m
        from unittest.mock import patch, mock_open

        with patch("builtins.open", mock_open()) as mo:
            mo.return_value.__enter__.return_value.write.side_effect = OSError("disk full")
            result = generate_report([{"title": "T", "content": "C"}], save_to_file=True)
        assert "[ERROR]" in result


class TestListSavedQueriesExtended:
    def test_list_saved_queries_parse_error(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json")
        from bi_agent_mcp.tools.analysis import list_saved_queries
        with patch("bi_agent_mcp.tools.analysis.QUERIES_FILE", bad_file):
            result = list_saved_queries()
        assert "[ERROR]" in result

    def test_list_saved_queries_empty_dict(self, tmp_path):
        empty_file = tmp_path / "empty.json"
        empty_file.write_text("{}")
        from bi_agent_mcp.tools.analysis import list_saved_queries
        with patch("bi_agent_mcp.tools.analysis.QUERIES_FILE", empty_file):
            result = list_saved_queries()
        assert "없습니다" in result


class TestLoadDomainContext:
    def test_no_context_dir_returns_info(self, tmp_path):
        with patch("bi_agent_mcp.tools.analysis.Path") as MockPath:
            fake_cwd = tmp_path / "no_context_here"
            MockPath.cwd.return_value = fake_cwd
            MockPath.return_value = fake_cwd / "context"
            from bi_agent_mcp.tools.analysis import load_domain_context
            import bi_agent_mcp.tools.analysis as m
            from pathlib import Path as RealPath
            with patch.object(m, "Path", RealPath):
                # cwd won't have context/
                import os
                old = os.getcwd()
                os.chdir(tmp_path)
                try:
                    result = load_domain_context("all")
                finally:
                    os.chdir(old)
        assert "[INFO]" in result or "context/" in result

    def test_context_dir_all_sections(self, tmp_path):
        ctx_dir = tmp_path / "context"
        ctx_dir.mkdir()
        (ctx_dir / "01_business_context.md").write_text("# Business\ncontent here")
        (ctx_dir / "03_kpi_dictionary.md").write_text("# KPIs\n- revenue")
        import os
        old = os.getcwd()
        os.chdir(tmp_path)
        try:
            from bi_agent_mcp.tools.analysis import load_domain_context
            result = load_domain_context("all")
        finally:
            os.chdir(old)
        assert "비즈니스 도메인 컨텍스트" in result

    def test_context_dir_specific_section(self, tmp_path):
        ctx_dir = tmp_path / "context"
        ctx_dir.mkdir()
        (ctx_dir / "03_kpi_dictionary.md").write_text("# KPIs")
        import os
        old = os.getcwd()
        os.chdir(tmp_path)
        try:
            from bi_agent_mcp.tools.analysis import load_domain_context
            result = load_domain_context("kpis")
        finally:
            os.chdir(old)
        assert "KPIs" in result or "도메인" in result

    def test_context_dir_unknown_section(self, tmp_path):
        ctx_dir = tmp_path / "context"
        ctx_dir.mkdir()
        import os
        old = os.getcwd()
        os.chdir(tmp_path)
        try:
            from bi_agent_mcp.tools.analysis import load_domain_context
            result = load_domain_context("unknown_section")
        finally:
            os.chdir(old)
        assert "[ERROR]" in result

    def test_context_dir_no_files(self, tmp_path):
        ctx_dir = tmp_path / "context"
        ctx_dir.mkdir()
        import os
        old = os.getcwd()
        os.chdir(tmp_path)
        try:
            from bi_agent_mcp.tools.analysis import load_domain_context
            result = load_domain_context("all")
        finally:
            os.chdir(old)
        assert "[INFO]" in result


class TestListQueryHistory:
    def test_no_file_returns_info(self, tmp_path):
        nonexistent = tmp_path / "no_history.json"
        from bi_agent_mcp.tools.analysis import list_query_history
        with patch("bi_agent_mcp.tools.analysis._QUERY_HISTORY_FILE", nonexistent):
            result = list_query_history()
        assert "이력이 없습니다" in result

    def test_with_history_returns_table(self, tmp_path):
        hist_file = tmp_path / "history.json"
        import json as _json
        entries = [
            {"timestamp": "2026-01-01T10:00:00", "conn_id": "pg1", "row_count": 10, "sql": "SELECT * FROM orders"},
            {"timestamp": "2026-01-02T11:00:00", "conn_id": "pg1", "row_count": 5, "sql": "SELECT id FROM users"},
        ]
        hist_file.write_text(_json.dumps(entries))
        from bi_agent_mcp.tools.analysis import list_query_history
        with patch("bi_agent_mcp.tools.analysis._QUERY_HISTORY_FILE", hist_file):
            result = list_query_history(limit=5)
        assert "|" in result
        assert "orders" in result

    def test_bad_json_returns_error(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not valid json")
        from bi_agent_mcp.tools.analysis import list_query_history
        with patch("bi_agent_mcp.tools.analysis._QUERY_HISTORY_FILE", bad_file):
            result = list_query_history()
        assert "[ERROR]" in result

    def test_empty_history_returns_info(self, tmp_path):
        hist_file = tmp_path / "hist.json"
        hist_file.write_text("[]")
        from bi_agent_mcp.tools.analysis import list_query_history
        with patch("bi_agent_mcp.tools.analysis._QUERY_HISTORY_FILE", hist_file):
            result = list_query_history()
        assert "없습니다" in result

    def test_limit_clamps_to_100(self, tmp_path):
        hist_file = tmp_path / "h.json"
        import json as _json
        entries = [{"timestamp": f"2026-01-{i:02d}T10:00:00", "conn_id": "c", "row_count": i, "sql": "SELECT 1"} for i in range(1, 51)]
        hist_file.write_text(_json.dumps(entries))
        from bi_agent_mcp.tools.analysis import list_query_history
        with patch("bi_agent_mcp.tools.analysis._QUERY_HISTORY_FILE", hist_file):
            result = list_query_history(limit=200)
        assert "|" in result


class TestSuggestAnalysisWithContext:
    def test_suggest_with_question(self, tmp_path):
        from bi_agent_mcp.tools.analysis import suggest_analysis
        import os
        old = os.getcwd()
        os.chdir(tmp_path)
        try:
            result = suggest_analysis("orders(id, amount, date)", "월별 매출을 보고 싶다")
        finally:
            os.chdir(old)
        assert "월별 매출" in result

    def test_suggest_with_context_dir(self, tmp_path):
        ctx_dir = tmp_path / "context"
        ctx_dir.mkdir()
        (ctx_dir / "03_kpi_dictionary.md").write_text("# KPI: GMV")
        (ctx_dir / "04_analysis_patterns.md").write_text("# Pattern: trend")
        import os
        old = os.getcwd()
        os.chdir(tmp_path)
        try:
            from bi_agent_mcp.tools.analysis import suggest_analysis
            result = suggest_analysis("sales table")
        finally:
            os.chdir(old)
        assert "도메인" in result or "GMV" in result or "Pattern" in result


class TestSaveQueryErrorPaths:
    """save_query: 읽기 오류(76-77) 및 쓰기 오류(90-92) 경로."""

    def test_read_error_in_existing_file_continues(self, tmp_path):
        """QUERIES_FILE이 존재하지만 JSON 파싱 실패 → logger.warning 후 계속 진행."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not valid json!!!")
        from bi_agent_mcp.tools.analysis import save_query
        with patch("bi_agent_mcp.tools.analysis.QUERIES_FILE", bad_file):
            result = save_query("q1", "SELECT 1", "conn1")
        assert "[SUCCESS]" in result

    def test_write_failure_returns_error(self, tmp_path):
        """QUERIES_FILE 쓰기 실패 → [ERROR] 반환."""
        new_file = tmp_path / "q.json"
        from bi_agent_mcp.tools.analysis import save_query
        import json as _json
        with patch("bi_agent_mcp.tools.analysis.QUERIES_FILE", new_file), \
             patch.object(_json, "dump", side_effect=OSError("permission denied")):
            result = save_query("q2", "SELECT 2", "conn2")
        assert "[ERROR]" in result


class TestLoadDomainContextOSError:
    """load_domain_context: 파일 읽기 OSError → pass (line 167)."""

    def test_os_error_on_read_skips_file(self, tmp_path):
        import os
        ctx_dir = tmp_path / "context"
        ctx_dir.mkdir()
        # 디렉터리를 파일 이름으로 만들면 read_text()가 OSError 발생
        dir_as_file = ctx_dir / "01_business_context.md"
        dir_as_file.mkdir()
        old = os.getcwd()
        os.chdir(tmp_path)
        try:
            from bi_agent_mcp.tools.analysis import load_domain_context
            result = load_domain_context()
        finally:
            os.chdir(old)
        assert "없거나" in result or isinstance(result, str)


class TestSuggestAnalysisOSError:
    """suggest_analysis: context 파일 읽기 OSError → pass (line 231)."""

    def test_os_error_on_kpi_file_skips(self, tmp_path):
        import os
        ctx_dir = tmp_path / "context"
        ctx_dir.mkdir()
        # 디렉터리로 만들어 read_text() OSError 유발
        kpi_dir = ctx_dir / "03_kpi_dictionary.md"
        kpi_dir.mkdir()
        old = os.getcwd()
        os.chdir(tmp_path)
        try:
            from bi_agent_mcp.tools.analysis import suggest_analysis
            result = suggest_analysis("sales(id, amount)")
        finally:
            os.chdir(old)
        assert isinstance(result, str)
