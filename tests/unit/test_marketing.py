"""bi_agent_mcp.tools.marketing 단위 테스트."""
import pytest
import sqlite3
import pandas as pd
from unittest.mock import patch, MagicMock

from bi_agent_mcp.tools.marketing import (
    campaign_performance,
    channel_attribution,
    cac_roas,
    conversion_funnel,
)

# ---------------------------------------------------------------------------
# 공통 헬퍼
# ---------------------------------------------------------------------------

def _make_patches(df: pd.DataFrame):
    conn_info = MagicMock()
    mock_conn = MagicMock()
    return [
        patch("bi_agent_mcp.tools.marketing._connections", {"test_conn": conn_info}),
        patch("bi_agent_mcp.tools.marketing._get_conn", return_value=mock_conn),
        patch("bi_agent_mcp.tools.marketing._validate_select", return_value=None),
        patch("pandas.read_sql", return_value=df),
    ]


def _with_df(df, fn, *args, **kwargs):
    patches = _make_patches(df)
    for p in patches:
        p.start()
    try:
        return fn(*args, **kwargs)
    finally:
        for p in patches:
            p.stop()


# ---------------------------------------------------------------------------
# campaign_performance
# ---------------------------------------------------------------------------

class TestCampaignPerformance:
    def test_basic_campaign_metrics(self):
        df = pd.DataFrame({
            "campaign": ["A", "A", "B", "B"],
            "impressions": [1000, 500, 800, 600],
            "clicks": [100, 50, 120, 80],
            "conversions": [10, 5, 20, 15],
            "revenue": [500.0, 250.0, 800.0, 600.0],
        })
        result = _with_df(df, campaign_performance, "test_conn", "SELECT 1",
                          campaign_col="campaign",
                          metric_cols=["impressions", "clicks", "conversions", "revenue"])
        assert "캠페인 성과 분석" in result
        assert "CTR(%)" in result
        assert "CVR(%)" in result
        assert "최고 성과 캠페인" in result
        assert "B" in result

    def test_unknown_conn_id_returns_error(self):
        result = campaign_performance("no_conn", "SELECT 1",
                                      campaign_col="campaign",
                                      metric_cols=["revenue"])
        assert "[ERROR]" in result
        assert "no_conn" in result

    def test_invalid_campaign_col_returns_error(self):
        df = pd.DataFrame({"campaign": ["A"], "revenue": [100.0]})
        result = _with_df(df, campaign_performance, "test_conn", "SELECT 1",
                          campaign_col="no_col",
                          metric_cols=["revenue"])
        assert "[ERROR]" in result
        assert "no_col" in result

    def test_invalid_metric_cols_returns_error(self):
        df = pd.DataFrame({"campaign": ["A"], "revenue": [100.0]})
        result = _with_df(df, campaign_performance, "test_conn", "SELECT 1",
                          campaign_col="campaign",
                          metric_cols=["no_metric"])
        assert "[ERROR]" in result

    def test_with_date_col_includes_trend(self):
        df = pd.DataFrame({
            "campaign": ["A", "A", "B"],
            "revenue": [100.0, 150.0, 200.0],
            "dt": ["2024-01-01", "2024-02-01", "2024-01-01"],
        })
        result = _with_df(df, campaign_performance, "test_conn", "SELECT 1",
                          campaign_col="campaign",
                          metric_cols=["revenue"],
                          date_col="dt")
        assert "기간별 트렌드" in result

    def test_with_invalid_date_col_warns(self):
        df = pd.DataFrame({"campaign": ["A"], "revenue": [100.0]})
        result = _with_df(df, campaign_performance, "test_conn", "SELECT 1",
                          campaign_col="campaign",
                          metric_cols=["revenue"],
                          date_col="no_date")
        assert "WARN" in result

    def test_validate_error_propagates(self):
        with patch("bi_agent_mcp.tools.marketing._validate_select", return_value="SELECT only"):
            result = campaign_performance("test_conn", "DELETE FROM t",
                                          campaign_col="campaign",
                                          metric_cols=["revenue"])
        assert "[ERROR]" in result


# ---------------------------------------------------------------------------
# channel_attribution
# ---------------------------------------------------------------------------

class TestChannelAttribution:
    def test_last_touch_attribution(self):
        df = pd.DataFrame({
            "channel": ["SEO", "SEO", "Paid", "Email", "Paid"],
            "conversions": [1, 1, 2, 1, 3],
            "revenue": [100.0, 80.0, 200.0, 150.0, 300.0],
        })
        result = _with_df(df, channel_attribution, "test_conn", "SELECT 1",
                          channel_col="channel",
                          conversion_col="conversions",
                          revenue_col="revenue",
                          model="last_touch")
        assert "채널 어트리뷰션 분석" in result
        assert "last_touch" in result
        assert "기여율(%)" in result
        assert "기여_매출" in result

    def test_first_touch_attribution(self):
        df = pd.DataFrame({
            "channel": ["SEO", "Paid", "Email"],
            "conversions": [5, 3, 2],
        })
        result = _with_df(df, channel_attribution, "test_conn", "SELECT 1",
                          channel_col="channel",
                          conversion_col="conversions",
                          model="first_touch")
        assert "first_touch" in result
        assert "SEO" in result

    def test_linear_attribution(self):
        df = pd.DataFrame({
            "channel": ["SEO", "Paid", "Email", "SEO"],
            "conversions": [1, 1, 1, 1],
        })
        result = _with_df(df, channel_attribution, "test_conn", "SELECT 1",
                          channel_col="channel",
                          conversion_col="conversions",
                          model="linear")
        assert "linear" in result
        assert "균등 분배" in result

    def test_unsupported_model_returns_error(self):
        df = pd.DataFrame({"channel": ["A"], "conversions": [1]})
        result = _with_df(df, channel_attribution, "test_conn", "SELECT 1",
                          channel_col="channel",
                          conversion_col="conversions",
                          model="data_driven")
        assert "[ERROR]" in result
        assert "data_driven" in result

    def test_unknown_conn_id_returns_error(self):
        result = channel_attribution("no_conn", "SELECT 1",
                                     channel_col="channel",
                                     conversion_col="conversions")
        assert "[ERROR]" in result

    def test_invalid_channel_col_returns_error(self):
        df = pd.DataFrame({"channel": ["A"], "conversions": [1]})
        result = _with_df(df, channel_attribution, "test_conn", "SELECT 1",
                          channel_col="no_channel",
                          conversion_col="conversions")
        assert "[ERROR]" in result

    def test_invalid_revenue_col_returns_error(self):
        df = pd.DataFrame({"channel": ["A"], "conversions": [1]})
        result = _with_df(df, channel_attribution, "test_conn", "SELECT 1",
                          channel_col="channel",
                          conversion_col="conversions",
                          revenue_col="no_revenue")
        assert "[ERROR]" in result

    def test_no_revenue_col_omits_revenue_column(self):
        df = pd.DataFrame({"channel": ["SEO", "Paid"], "conversions": [5, 3]})
        result = _with_df(df, channel_attribution, "test_conn", "SELECT 1",
                          channel_col="channel",
                          conversion_col="conversions")
        assert "기여_매출" not in result


# ---------------------------------------------------------------------------
# cac_roas
# ---------------------------------------------------------------------------

class TestCacRoas:
    def test_basic_cac_roas(self):
        df = pd.DataFrame({
            "channel": ["SEO", "SEO", "Paid", "Paid"],
            "cost": [500.0, 300.0, 1000.0, 800.0],
            "revenue": [2000.0, 1500.0, 3000.0, 2500.0],
            "conversions": [10, 8, 20, 15],
        })
        result = _with_df(df, cac_roas, "test_conn", "SELECT 1",
                          channel_col="channel",
                          cost_col="cost",
                          revenue_col="revenue",
                          conversions_col="conversions")
        assert "CAC / ROAS / ROI 분석" in result
        assert "CAC" in result
        assert "ROAS(%)" in result
        assert "ROI(%)" in result
        assert "최효율 채널" in result

    def test_without_conversions_col_uses_revenue_gt_zero(self):
        df = pd.DataFrame({
            "channel": ["SEO", "SEO", "Paid"],
            "cost": [500.0, 300.0, 1000.0],
            "revenue": [2000.0, 0.0, 3000.0],
        })
        result = _with_df(df, cac_roas, "test_conn", "SELECT 1",
                          channel_col="channel",
                          cost_col="cost",
                          revenue_col="revenue")
        assert "CAC / ROAS / ROI 분석" in result
        assert "[ERROR]" not in result

    def test_unknown_conn_id_returns_error(self):
        result = cac_roas("no_conn", "SELECT 1",
                          channel_col="channel",
                          cost_col="cost",
                          revenue_col="revenue")
        assert "[ERROR]" in result

    def test_invalid_cost_col_returns_error(self):
        df = pd.DataFrame({"channel": ["A"], "cost": [100.0], "revenue": [200.0]})
        result = _with_df(df, cac_roas, "test_conn", "SELECT 1",
                          channel_col="channel",
                          cost_col="no_cost",
                          revenue_col="revenue")
        assert "[ERROR]" in result

    def test_invalid_conversions_col_returns_error(self):
        df = pd.DataFrame({"channel": ["A"], "cost": [100.0], "revenue": [200.0]})
        result = _with_df(df, cac_roas, "test_conn", "SELECT 1",
                          channel_col="channel",
                          cost_col="cost",
                          revenue_col="revenue",
                          conversions_col="no_conv")
        assert "[ERROR]" in result


# ---------------------------------------------------------------------------
# conversion_funnel
# ---------------------------------------------------------------------------

class TestConversionFunnel:
    def test_basic_funnel(self):
        df = pd.DataFrame({
            "stage": ["visit", "visit", "visit", "signup", "signup", "purchase"],
            "user_id": [1, 2, 3, 1, 2, 1],
        })
        result = _with_df(df, conversion_funnel, "test_conn", "SELECT 1",
                          stage_col="stage",
                          user_col="user_id")
        assert "퍼널 전환율 분석" in result
        assert "visit" in result
        assert "signup" in result
        assert "purchase" in result
        assert "병목 지점" in result

    def test_funnel_conversion_rates(self):
        df = pd.DataFrame({
            "stage": ["visit"] * 100 + ["signup"] * 50 + ["purchase"] * 20,
            "user_id": list(range(100)) + list(range(50)) + list(range(20)),
        })
        result = _with_df(df, conversion_funnel, "test_conn", "SELECT 1",
                          stage_col="stage",
                          user_col="user_id")
        assert "50.0%" in result  # signup: 50/100
        assert "40.0%" in result  # purchase: 20/50

    def test_unknown_conn_id_returns_error(self):
        result = conversion_funnel("no_conn", "SELECT 1",
                                   stage_col="stage",
                                   user_col="user_id")
        assert "[ERROR]" in result

    def test_invalid_stage_col_returns_error(self):
        df = pd.DataFrame({"stage": ["visit"], "user_id": [1]})
        result = _with_df(df, conversion_funnel, "test_conn", "SELECT 1",
                          stage_col="no_stage",
                          user_col="user_id")
        assert "[ERROR]" in result

    def test_invalid_user_col_returns_error(self):
        df = pd.DataFrame({"stage": ["visit"], "user_id": [1]})
        result = _with_df(df, conversion_funnel, "test_conn", "SELECT 1",
                          stage_col="stage",
                          user_col="no_user")
        assert "[ERROR]" in result

    def test_with_date_col_includes_trend(self):
        df = pd.DataFrame({
            "stage": ["visit", "visit", "signup"],
            "user_id": [1, 2, 1],
            "dt": ["2024-01-01", "2024-01-01", "2024-01-02"],
        })
        result = _with_df(df, conversion_funnel, "test_conn", "SELECT 1",
                          stage_col="stage",
                          user_col="user_id",
                          date_col="dt")
        assert "기간별 퍼널 트렌드" in result

    def test_with_invalid_date_col_warns(self):
        df = pd.DataFrame({"stage": ["visit"], "user_id": [1]})
        result = _with_df(df, conversion_funnel, "test_conn", "SELECT 1",
                          stage_col="stage",
                          user_col="user_id",
                          date_col="no_date")
        assert "WARN" in result

    def test_validate_error_propagates(self):
        with patch("bi_agent_mcp.tools.marketing._validate_select", return_value="SELECT only"):
            result = conversion_funnel("test_conn", "DELETE FROM t",
                                       stage_col="stage",
                                       user_col="user_id")
        assert "[ERROR]" in result
