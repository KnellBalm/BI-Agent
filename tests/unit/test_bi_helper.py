"""bi_helper.py 단위 테스트."""
from bi_agent_mcp.tools.bi_helper import bi_tool_selector


def test_bi_tool_selector_revenue():
    result = bi_tool_selector("매출 추이 분석")
    assert "## BI 도구 추천" in result
    assert "revenue_analysis" in result


def test_bi_tool_selector_ab_test():
    result = bi_tool_selector("A/B 테스트 결과 검증")
    assert "ab_test_analysis" in result
    assert "ttest_independent" in result


def test_bi_tool_selector_churn():
    result = bi_tool_selector("고객 이탈 원인 파악")
    assert "churn_analysis" in result


def test_bi_tool_selector_with_domain():
    result = bi_tool_selector("매출 분석", data_domain="ecommerce")
    assert "ecommerce" in result.lower() or "이커머스" in result


def test_bi_tool_selector_unknown():
    result = bi_tool_selector("알 수 없는 분석 목표")
    assert "## BI 도구 추천" in result


def test_bi_tool_selector_forecast():
    result = bi_tool_selector("다음 달 매출 예측")
    assert "forecast" in result.lower() or "예측" in result


def test_bi_tool_selector_constraints():
    result = bi_tool_selector("통계 분석", constraints="scipy 없음")
    assert "scipy" in result.lower()


def test_bi_tool_selector_multi_category():
    result = bi_tool_selector("매출 예측 분석")
    assert "revenue_analysis" in result
    assert "forecast" in result.lower() or "linear_trend_forecast" in result


def test_bi_tool_selector_workflow_steps():
    result = bi_tool_selector("이탈 분석")
    assert "churn_analysis" in result
    assert "retention_curve" in result


def test_bi_tool_selector_funnel():
    result = bi_tool_selector("퍼널 전환율 분석")
    assert "funnel_analysis" in result
    assert "권장 분석 순서" in result
