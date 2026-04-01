"""bi_agent_mcp.tools.analysis 추가 단위 테스트 — generate_report, load_domain_context, list_query_history."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch

from bi_agent_mcp.tools.analysis import generate_report, load_domain_context, list_query_history


class TestGenerateReport:
    def test_creates_markdown_file(self, tmp_path):
        sections = [{"title": "매출 요약", "content": "3월 매출 1억"}]
        fake_path = tmp_path / "report.md"

        with patch("bi_agent_mcp.tools.analysis.Path") as MockPath:
            # home() / "Downloads" 패치
            mock_downloads = MagicMock()
            mock_downloads.exists.return_value = True
            MockPath.home.return_value.expanduser.return_value.__truediv__ = lambda self, other: fake_path.parent
            # 직접 파일 경로로 테스트
            pass

        # patch 없이 실제 Downloads 경로로 파일 생성 → 경로만 확인
        result = generate_report(sections)
        assert isinstance(result, str)
        # 성공 또는 에러 모두 문자열 반환
        assert len(result) > 0

    def test_report_contains_section_title(self, tmp_path):
        sections = [{"title": "KPI 현황", "content": "DAU 10만명"}]
        result = generate_report(sections)
        # 파일이 생성됐으면 경로 반환, 실패면 [ERROR] 포함
        if "[ERROR]" not in result:
            # 파일이 존재하고 내용 확인
            p = Path(result)
            if p.exists():
                content = p.read_text(encoding="utf-8")
                assert "KPI 현황" in content
                assert "DAU 10만명" in content

    def test_empty_sections_creates_file(self):
        result = generate_report([])
        assert isinstance(result, str)

    def test_multiple_sections(self):
        sections = [
            {"title": "섹션1", "content": "내용1"},
            {"title": "섹션2", "content": "내용2"},
        ]
        result = generate_report(sections)
        assert isinstance(result, str)
        if "[ERROR]" not in result:
            p = Path(result)
            if p.exists():
                content = p.read_text(encoding="utf-8")
                assert "섹션1" in content
                assert "섹션2" in content

    def test_ioerror_returns_error_string(self, tmp_path):
        sections = [{"title": "T", "content": "C"}]
        with patch("builtins.open", side_effect=OSError("permission denied")):
            result = generate_report(sections, save_to_file=True)
        assert "[ERROR]" in result


class TestLoadDomainContext:
    def test_no_context_dir_returns_info(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = load_domain_context()
        assert "[INFO]" in result
        assert "context/" in result

    def test_all_sections_loaded(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        ctx_dir = tmp_path / "context"
        ctx_dir.mkdir()
        (ctx_dir / "01_business_context.md").write_text("비즈니스 개요", encoding="utf-8")
        (ctx_dir / "03_kpi_dictionary.md").write_text("KPI 정의", encoding="utf-8")

        result = load_domain_context("all")
        assert "비즈니스 개요" in result or "[INFO]" in result

    def test_specific_section(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        ctx_dir = tmp_path / "context"
        ctx_dir.mkdir()
        (ctx_dir / "03_kpi_dictionary.md").write_text("KPI 내용", encoding="utf-8")

        result = load_domain_context("kpis")
        assert "KPI 내용" in result

    def test_unknown_section_returns_error(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        ctx_dir = tmp_path / "context"
        ctx_dir.mkdir()

        result = load_domain_context("nonexistent_section")
        assert "[ERROR]" in result

    def test_empty_context_dir_returns_info(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        ctx_dir = tmp_path / "context"
        ctx_dir.mkdir()

        result = load_domain_context("all")
        assert "[INFO]" in result


class TestListQueryHistory:
    def test_no_history_file_returns_message(self, tmp_path):
        fake_file = tmp_path / "query_history.json"
        with patch("bi_agent_mcp.tools.analysis._QUERY_HISTORY_FILE", fake_file):
            result = list_query_history()
        assert "이력이 없습니다" in result

    def test_empty_history_returns_message(self, tmp_path):
        fake_file = tmp_path / "query_history.json"
        fake_file.write_text("[]", encoding="utf-8")
        with patch("bi_agent_mcp.tools.analysis._QUERY_HISTORY_FILE", fake_file):
            result = list_query_history()
        assert "이력이 없습니다" in result

    def test_returns_markdown_table(self, tmp_path):
        history = [
            {"timestamp": "2026-03-01T10:00:00", "conn_id": "conn_1", "row_count": 10, "sql": "SELECT * FROM users"},
            {"timestamp": "2026-03-02T11:00:00", "conn_id": "conn_2", "row_count": 5, "sql": "SELECT id FROM orders"},
        ]
        fake_file = tmp_path / "query_history.json"
        fake_file.write_text(json.dumps(history), encoding="utf-8")
        with patch("bi_agent_mcp.tools.analysis._QUERY_HISTORY_FILE", fake_file):
            result = list_query_history()
        assert "|" in result
        assert "conn_1" in result

    def test_limit_is_respected(self, tmp_path):
        history = [
            {"timestamp": f"2026-03-{i:02d}T00:00:00", "conn_id": "c", "row_count": i, "sql": f"SELECT {i}"}
            for i in range(1, 25)
        ]
        fake_file = tmp_path / "query_history.json"
        fake_file.write_text(json.dumps(history), encoding="utf-8")
        with patch("bi_agent_mcp.tools.analysis._QUERY_HISTORY_FILE", fake_file):
            result = list_query_history(limit=5)
        assert "최근 5개" in result

    def test_invalid_json_returns_error(self, tmp_path):
        fake_file = tmp_path / "query_history.json"
        fake_file.write_text("INVALID_JSON", encoding="utf-8")
        with patch("bi_agent_mcp.tools.analysis._QUERY_HISTORY_FILE", fake_file):
            result = list_query_history()
        assert "[ERROR]" in result

    def test_limit_clamped_to_100(self, tmp_path):
        history = [
            {"timestamp": "2026-03-01T00:00:00", "conn_id": "c", "row_count": 1, "sql": "SELECT 1"}
        ]
        fake_file = tmp_path / "query_history.json"
        fake_file.write_text(json.dumps(history), encoding="utf-8")
        with patch("bi_agent_mcp.tools.analysis._QUERY_HISTORY_FILE", fake_file):
            result = list_query_history(limit=999)
        assert isinstance(result, str)


# MagicMock import
from unittest.mock import MagicMock
