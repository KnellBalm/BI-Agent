"""orchestrator.py 단위 테스트."""
from unittest.mock import patch, MagicMock
import pytest


def test_bi_start_no_connection_guides_user():
    from bi_agent_mcp.tools.orchestrator import bi_start
    with patch("bi_agent_mcp.tools.orchestrator._connections", {}):
        result = bi_start("매출 분석해줘")
    assert "연결" in result
    assert "connect_db" in result


def test_bi_start_guide_mode_for_how_questions():
    from bi_agent_mcp.tools.orchestrator import bi_start
    mock_conn = {"mydb": MagicMock()}
    with patch("bi_agent_mcp.tools.orchestrator._connections", mock_conn):
        result = bi_start("매출 분석 어떻게 해?")
    assert "가이드" in result or "도구" in result or "워크플로우" in result


def test_bi_start_orchestrator_mode_for_analyze_requests():
    from bi_agent_mcp.tools.orchestrator import bi_start
    mock_conn = {"mydb": MagicMock()}
    with patch("bi_agent_mcp.tools.orchestrator._connections", mock_conn), \
         patch("bi_agent_mcp.tools.orchestrator.bi_orchestrate") as mock_orch:
        mock_orch.return_value = "## BI 분석 실행 계획"
        result = bi_start("이번 달 매출 왜 떨어졌어?", conn_id="mydb")
    mock_orch.assert_called_once_with("이번 달 매출 왜 떨어졌어?", "mydb")
    assert "BI 분석 실행 계획" in result


def test_bi_start_uses_first_connection_when_no_conn_id():
    from bi_agent_mcp.tools.orchestrator import bi_start
    mock_conn = {"first_db": MagicMock()}
    with patch("bi_agent_mcp.tools.orchestrator._connections", mock_conn), \
         patch("bi_agent_mcp.tools.orchestrator.bi_orchestrate") as mock_orch:
        mock_orch.return_value = "## BI 분석 실행 계획"
        bi_start("매출 하락 원인 찾아줘")
    mock_orch.assert_called_once_with("매출 하락 원인 찾아줘", "first_db")


def test_bi_orchestrate_returns_error_for_unknown_conn():
    from bi_agent_mcp.tools.orchestrator import bi_orchestrate
    with patch("bi_agent_mcp.tools.orchestrator._connections", {}):
        result = bi_orchestrate("매출 분석", "nonexistent")
    assert result.startswith("[ERROR]")
    assert "nonexistent" in result


def test_bi_orchestrate_returns_full_plan():
    from bi_agent_mcp.tools.orchestrator import bi_orchestrate
    mock_conn = {"mydb": MagicMock()}
    with patch("bi_agent_mcp.tools.orchestrator._connections", mock_conn), \
         patch("bi_agent_mcp.tools.orchestrator.get_schema", return_value="## Schema\n- orders(id, amount)"), \
         patch("bi_agent_mcp.tools.orchestrator.generate_sql", return_value="## SQL 생성 요청\n질문: 매출"), \
         patch("bi_agent_mcp.tools.orchestrator.bi_tool_selector", return_value="### 핵심 도구\n- revenue_analysis"), \
         patch("bi_agent_mcp.tools.orchestrator.hypothesis_helper", return_value="### 가설\n1. 신규 고객 감소"), \
         patch("bi_agent_mcp.tools.orchestrator.suggest_analysis", return_value="1. 핵심 지표 정의"):
        result = bi_orchestrate("이번 달 매출 왜 떨어졌어?", "mydb")
    assert "SQL" in result
    assert "도구" in result or "핵심" in result
    assert "run_query" in result
    assert "generate_report" in result


def test_bi_orchestrate_dashboard_output_includes_generate_dashboard():
    from bi_agent_mcp.tools.orchestrator import bi_orchestrate
    mock_conn = {"mydb": MagicMock()}
    with patch("bi_agent_mcp.tools.orchestrator._connections", mock_conn), \
         patch("bi_agent_mcp.tools.orchestrator.get_schema", return_value="schema"), \
         patch("bi_agent_mcp.tools.orchestrator.generate_sql", return_value="sql context"), \
         patch("bi_agent_mcp.tools.orchestrator.bi_tool_selector", return_value="tools"), \
         patch("bi_agent_mcp.tools.orchestrator.hypothesis_helper", return_value="hypotheses"), \
         patch("bi_agent_mcp.tools.orchestrator.suggest_analysis", return_value="analysis"):
        result = bi_orchestrate("매출 현황", "mydb", output="dashboard")
    assert "generate_dashboard" in result


def test_classify_intent_revenue_decline():
    from bi_agent_mcp.tools.orchestrator import _classify_intent
    assert _classify_intent("이번 달 매출 왜 하락했어?") == "revenue_decline"


def test_classify_intent_churn():
    from bi_agent_mcp.tools.orchestrator import _classify_intent
    assert _classify_intent("이탈률이 늘었어") == "churn_increase"


def test_classify_intent_general():
    from bi_agent_mcp.tools.orchestrator import _classify_intent
    assert _classify_intent("데이터 좀 봐줘") == "general"
