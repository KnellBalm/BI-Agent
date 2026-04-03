"""bi_tool_guide 단위 테스트."""
import pytest
from bi_agent_mcp.tools.bi_tool_guide import bi_tool_guide, _classify_intent


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


class TestClassifyIntent:
    def test_chart_intent(self):
        assert _classify_intent("라인 차트 만들기", "") == "chart"

    def test_calc_intent(self):
        assert _classify_intent("고객별 최초구매일 구하기", "") == "calc"

    def test_calc_mom_intent(self):
        assert _classify_intent("MoM 성장률 계산", "") == "calc"

    def test_feature_intent_parameter(self):
        assert _classify_intent("매개변수 만들기", "") == "feature"

    def test_feature_intent_set(self):
        assert _classify_intent("집합 생성", "") == "feature"

    def test_troubleshoot_via_situation(self):
        assert _classify_intent("뭔가 이상함", "연결 오류") == "troubleshoot"

    def test_troubleshoot_via_intent(self):
        assert _classify_intent("연결이 안 된다", "") == "troubleshoot"

    def test_unknown_defaults_to_chart(self):
        assert _classify_intent("완전히 모르는 의도", "") == "chart"
