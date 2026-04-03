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


class TestChartMode:
    def test_tableau_line_chart_with_columns(self):
        result = bi_tool_guide(
            intent="월별 매출 추이",
            tool="tableau",
            columns="date, revenue",
        )
        assert "Columns Shelf" in result or "Rows Shelf" in result
        assert "date" in result
        assert "revenue" in result
        assert "1단계" in result or "**1" in result

    def test_powerbi_bar_chart(self):
        result = bi_tool_guide(intent="카테고리별 비교", tool="powerbi")
        assert "Axis" in result or "Values" in result
        assert "1단계" in result or "**1" in result

    def test_quicksight_kpi(self):
        result = bi_tool_guide(intent="KPI 카드", tool="quicksight", columns="revenue")
        assert "KPI" in result or "AutoGraph" in result

    def test_looker_fallback_unknown_chart(self):
        result = bi_tool_guide(intent="간트 차트 만들기", tool="looker")
        assert "[ERROR]" not in result
        assert "간트" in result or "가이드" in result or "Looker" in result

    def test_tableau_fallback_unknown_chart(self):
        result = bi_tool_guide(intent="완전히 모르는 차트", tool="tableau")
        assert "[ERROR]" not in result
        assert "단계" in result or "Tableau" in result


class TestCalcMode:
    def test_tableau_lod_min_per_dim(self):
        result = bi_tool_guide(
            intent="고객별 최초구매일 구하기",
            tool="tableau",
            columns="customer_id, purchase_date",
        )
        assert "FIXED" in result or "MIN" in result
        assert "customer_id" in result or "{col0}" not in result

    def test_powerbi_mom_growth(self):
        result = bi_tool_guide(
            intent="MoM 성장률 계산",
            tool="powerbi",
            columns="date, revenue",
        )
        assert "DAX" in result or "DATEADD" in result or "DIVIDE" in result

    def test_quicksight_running_total(self):
        result = bi_tool_guide(intent="누적합 계산", tool="quicksight")
        assert "[ERROR]" not in result
        assert "runningSum" in result or "누적" in result or "calculated" in result.lower()

    def test_looker_ratio(self):
        result = bi_tool_guide(intent="전체 대비 비율 계산", tool="looker")
        assert "[ERROR]" not in result
        assert "%" in result or "비율" in result or "Calculated Field" in result

    def test_unknown_calc_fallback(self):
        result = bi_tool_guide(intent="알 수 없는 계산 수식", tool="tableau")
        # _classify_intent이 calc로 분류 안 되면 chart 폴백으로 감 — 테스트는 에러 없음만 확인
        assert "[ERROR]" not in result
