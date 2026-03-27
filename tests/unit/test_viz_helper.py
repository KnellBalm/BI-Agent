"""viz_helper 단위 테스트."""
from bi_agent_mcp.tools.viz_helper import visualize_advisor, dashboard_design_guide


def test_visualize_advisor_time_series():
    result = visualize_advisor(["date", "revenue"], "월별 매출 추이")
    assert "## 시각화 방법 추천" in result
    assert "generate_dashboard" in result or "generate_twbx" in result


def test_visualize_advisor_category():
    result = visualize_advisor(["category", "sales", "count"], "카테고리별 비교")
    assert "Bar" in result or "bar" in result


def test_visualize_advisor_tableau_format():
    result = visualize_advisor(["product", "revenue"], "제품별 매출", output_format="tableau")
    assert "generate_twbx" in result


def test_dashboard_design_guide_basic():
    result = dashboard_design_guide(["revenue", "orders"], ["category"])
    assert "## 대시보드 설계 가이드" in result
    assert "generate_dashboard" in result


def test_dashboard_design_guide_with_time():
    result = dashboard_design_guide(["sales", "profit"], ["region", "channel"], time_col="date")
    assert "line" in result.lower() or "시계열" in result
    assert "generate_dashboard" in result
