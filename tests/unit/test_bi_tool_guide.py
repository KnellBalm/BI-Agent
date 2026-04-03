"""bi_tool_guide 단위 테스트."""
import pytest
from bi_agent_mcp.tools.bi_tool_guide import bi_tool_guide


class TestErrors:
    def test_empty_intent_returns_error(self):
        result = bi_tool_guide(intent="")
        assert "[ERROR]" in result
        assert "intent" in result

    def test_unknown_tool_returns_error(self):
        result = bi_tool_guide(intent="차트 만들기", tool="powerpoint")
        assert "[ERROR]" in result
        assert "tableau" in result.lower() or "지원하지 않는" in result

    def test_whitespace_intent_returns_error(self):
        result = bi_tool_guide(intent="   ")
        assert "[ERROR]" in result


class TestRecommendMode:
    def test_no_tool_returns_chart_recommendation(self):
        result = bi_tool_guide(intent="월별 매출 추이를 보고 싶다")
        assert "라인" in result or "line" in result.lower()
        assert "tableau" in result.lower()
        assert "powerbi" in result.lower() or "power bi" in result.lower()

    def test_no_tool_pie_intent(self):
        result = bi_tool_guide(intent="카테고리별 비율을 보고 싶다")
        assert "파이" in result or "pie" in result.lower() or "도넛" in result

    def test_no_tool_unknown_intent_shows_general(self):
        result = bi_tool_guide(intent="완전히 모르는 의도")
        assert "tableau" in result.lower()
        assert "tool=" in result  # 다음 호출 안내 포함

    def test_no_tool_includes_next_step_hint(self):
        result = bi_tool_guide(intent="바 차트 만들기")
        assert "tool=" in result
