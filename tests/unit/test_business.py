"""bi_agent_mcp.tools.business 단위 테스트."""
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from bi_agent_mcp.tools.business import (
    revenue_analysis,
    rfm_analysis,
    ltv_analysis,
    churn_analysis,
    pareto_analysis,
    growth_analysis,
)

# ---------------------------------------------------------------------------
# revenue_analysis
# ---------------------------------------------------------------------------

class TestRevenueAnalysis:
    def test_basic_monthly_revenue(self, with_df_business):
        df = pd.DataFrame({
            "dt": ["2024-01-15", "2024-01-20", "2024-02-10", "2024-03-05"],
            "amount": [100.0, 200.0, 150.0, 300.0],
        })
        result = with_df_business(df, revenue_analysis, "test_conn", "SELECT 1",
                          revenue_col="amount", time_col="dt", period="month")
        assert "매출 분석" in result
        assert "누적 매출" in result
        assert "300.00" in result

    def test_unknown_conn_id_returns_error(self):
        result = revenue_analysis("unknown_conn", "SELECT 1", "amount", "dt")
        assert "[ERROR]" in result

    def test_missing_revenue_col_returns_error(self, with_df_business):
        df = pd.DataFrame({"dt": ["2024-01-01"], "amount": [100.0]})
        result = with_df_business(df, revenue_analysis, "test_conn", "SELECT 1",
                          revenue_col="no_col", time_col="dt")
        assert "[ERROR]" in result

    def test_invalid_period_returns_error(self, with_df_business):
        df = pd.DataFrame({"dt": ["2024-01-01"], "amount": [100.0]})
        result = with_df_business(df, revenue_analysis, "test_conn", "SELECT 1",
                          revenue_col="amount", time_col="dt", period="decade")
        assert "[ERROR]" in result

    def test_summary_stats_present(self, with_df_business):
        df = pd.DataFrame({
            "dt": ["2024-01-01", "2024-02-01", "2024-03-01"],
            "amount": [100.0, 200.0, 150.0],
        })
        result = with_df_business(df, revenue_analysis, "test_conn", "SELECT 1",
                          revenue_col="amount", time_col="dt", period="month")
        assert "총 매출" in result
        assert "최고 기간" in result

    def test_single_row_no_growth_shown(self, with_df_business):
        df = pd.DataFrame({"dt": ["2024-01-01"], "amount": [500.0]})
        result = with_df_business(df, revenue_analysis, "test_conn", "SELECT 1",
                          revenue_col="amount", time_col="dt", period="month")
        assert "매출 분석" in result
        assert "500.00" in result


# ---------------------------------------------------------------------------
# rfm_analysis
# ---------------------------------------------------------------------------

class TestRfmAnalysis:
    def _make_df(self):
        return pd.DataFrame({
            "customer_id": ["A", "A", "A", "B", "B", "C", "C", "C", "C", "D"],
            "purchase_date": [
                "2024-03-01", "2024-02-01", "2024-01-01",
                "2024-03-10", "2024-01-10",
                "2023-06-01", "2023-05-01", "2023-04-01", "2023-03-01",
                "2023-01-01",
            ],
            "amount": [100, 200, 150, 300, 100, 50, 60, 70, 80, 200],
        })

    def test_basic_rfm(self, with_df_business):
        df = self._make_df()
        result = with_df_business(df, rfm_analysis, "test_conn", "SELECT 1",
                          customer_col="customer_id", date_col="purchase_date",
                          revenue_col="amount")
        assert "RFM 분석" in result
        assert "세그먼트" in result

    def test_unknown_conn_returns_error(self):
        result = rfm_analysis("bad_conn", "SELECT 1", "customer_id", "purchase_date", "amount")
        assert "[ERROR]" in result

    def test_missing_col_returns_error(self, with_df_business):
        df = self._make_df()
        result = with_df_business(df, rfm_analysis, "test_conn", "SELECT 1",
                          customer_col="no_col", date_col="purchase_date",
                          revenue_col="amount")
        assert "[ERROR]" in result

    def test_custom_snapshot_date(self, with_df_business):
        df = self._make_df()
        result = with_df_business(df, rfm_analysis, "test_conn", "SELECT 1",
                          customer_col="customer_id", date_col="purchase_date",
                          revenue_col="amount", snapshot_date="2024-04-01")
        assert "2024-04-01" in result

    def test_single_customer(self, with_df_business):
        df = pd.DataFrame({
            "customer_id": ["A"],
            "purchase_date": ["2024-01-01"],
            "amount": [100.0],
        })
        result = with_df_business(df, rfm_analysis, "test_conn", "SELECT 1",
                          customer_col="customer_id", date_col="purchase_date",
                          revenue_col="amount")
        assert "RFM 분석" in result


# ---------------------------------------------------------------------------
# ltv_analysis
# ---------------------------------------------------------------------------

class TestLtvAnalysis:
    def _make_df(self):
        return pd.DataFrame({
            "customer_id": ["A", "A", "B", "B", "B", "C"],
            "order_date": [
                "2024-01-01", "2024-03-01",
                "2024-01-01", "2024-02-01", "2024-03-01",
                "2024-01-01",
            ],
            "revenue": [200.0, 300.0, 100.0, 150.0, 200.0, 500.0],
        })

    def test_basic_ltv(self, with_df_business):
        df = self._make_df()
        result = with_df_business(df, ltv_analysis, "test_conn", "SELECT 1",
                          customer_col="customer_id", revenue_col="revenue",
                          date_col="order_date", periods=12)
        assert "LTV 분석" in result
        assert "예상 LTV" in result
        assert "평균 LTV" in result

    def test_unknown_conn_returns_error(self):
        result = ltv_analysis("bad_conn", "SELECT 1", "customer_id", "revenue", "order_date")
        assert "[ERROR]" in result

    def test_missing_col_returns_error(self, with_df_business):
        df = self._make_df()
        result = with_df_business(df, ltv_analysis, "test_conn", "SELECT 1",
                          customer_col="no_col", revenue_col="revenue",
                          date_col="order_date")
        assert "[ERROR]" in result

    def test_single_customer_single_order(self, with_df_business):
        df = pd.DataFrame({
            "customer_id": ["A"],
            "order_date": ["2024-01-01"],
            "revenue": [1000.0],
        })
        result = with_df_business(df, ltv_analysis, "test_conn", "SELECT 1",
                          customer_col="customer_id", revenue_col="revenue",
                          date_col="order_date", periods=6)
        assert "LTV 분석" in result
        assert "1,000.00" in result

    def test_top20_limit(self, with_df_business):
        rows = {
            "customer_id": [f"C{i}" for i in range(30)],
            "order_date": ["2024-01-01"] * 15 + ["2024-06-01"] * 15,
            "revenue": [float(i * 100) for i in range(30)],
        }
        df = pd.DataFrame(rows)
        result = with_df_business(df, ltv_analysis, "test_conn", "SELECT 1",
                          customer_col="customer_id", revenue_col="revenue",
                          date_col="order_date")
        assert "LTV 분석" in result


# ---------------------------------------------------------------------------
# churn_analysis
# ---------------------------------------------------------------------------

class TestChurnAnalysis:
    def _make_df(self):
        return pd.DataFrame({
            "customer_id": ["A", "B", "C", "D", "E"],
            "purchase_date": [
                "2024-03-20",  # 활성 (최근)
                "2024-02-15",  # 이탈 위험
                "2023-12-01",  # 이탈
                "2024-03-25",  # 활성
                "2024-01-01",  # 이탈 위험
            ],
        })

    def test_basic_churn(self, with_df_business):
        df = self._make_df()
        result = with_df_business(df, churn_analysis, "test_conn", "SELECT 1",
                          customer_col="customer_id", date_col="purchase_date",
                          inactivity_days=90)
        assert "이탈 분석" in result
        assert "활성" in result
        assert "이탈 위험" in result
        assert "이탈" in result

    def test_unknown_conn_returns_error(self):
        result = churn_analysis("bad_conn", "SELECT 1", "customer_id", "purchase_date")
        assert "[ERROR]" in result

    def test_missing_col_returns_error(self, with_df_business):
        df = self._make_df()
        result = with_df_business(df, churn_analysis, "test_conn", "SELECT 1",
                          customer_col="no_col", date_col="purchase_date")
        assert "[ERROR]" in result

    def test_all_active(self, with_df_business):
        df = pd.DataFrame({
            "customer_id": ["A", "B"],
            "purchase_date": ["2024-03-25", "2024-03-24"],
        })
        result = with_df_business(df, churn_analysis, "test_conn", "SELECT 1",
                          customer_col="customer_id", date_col="purchase_date",
                          inactivity_days=90)
        assert "이탈 분석" in result

    def test_custom_inactivity_threshold(self, with_df_business):
        df = self._make_df()
        result = with_df_business(df, churn_analysis, "test_conn", "SELECT 1",
                          customer_col="customer_id", date_col="purchase_date",
                          inactivity_days=30)
        assert "30일" in result


# ---------------------------------------------------------------------------
# pareto_analysis
# ---------------------------------------------------------------------------

class TestParetoAnalysis:
    def _make_df(self):
        return pd.DataFrame({
            "product": ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"],
            "revenue": [500, 300, 200, 100, 80, 60, 40, 30, 20, 10],
        })

    def test_basic_pareto(self, with_df_business):
        df = self._make_df()
        result = with_df_business(df, pareto_analysis, "test_conn", "SELECT 1",
                          category_col="product", value_col="revenue")
        assert "파레토 분석" in result
        assert "80%" in result
        assert "누적 기여도" in result

    def test_unknown_conn_returns_error(self):
        result = pareto_analysis("bad_conn", "SELECT 1", "product", "revenue")
        assert "[ERROR]" in result

    def test_missing_col_returns_error(self, with_df_business):
        df = self._make_df()
        result = with_df_business(df, pareto_analysis, "test_conn", "SELECT 1",
                          category_col="no_col", value_col="revenue")
        assert "[ERROR]" in result

    def test_zero_total_returns_error(self, with_df_business):
        df = pd.DataFrame({"product": ["A", "B"], "revenue": [0, 0]})
        result = with_df_business(df, pareto_analysis, "test_conn", "SELECT 1",
                          category_col="product", value_col="revenue")
        assert "[ERROR]" in result

    def test_single_category(self, with_df_business):
        df = pd.DataFrame({"product": ["A"], "revenue": [1000.0]})
        result = with_df_business(df, pareto_analysis, "test_conn", "SELECT 1",
                          category_col="product", value_col="revenue")
        assert "파레토 분석" in result
        assert "1,000.00" in result

    def test_summary_shows_pareto_count(self, with_df_business):
        df = self._make_df()
        result = with_df_business(df, pareto_analysis, "test_conn", "SELECT 1",
                          category_col="product", value_col="revenue")
        assert "전체의 80% 기여" in result


# ---------------------------------------------------------------------------
# growth_analysis
# ---------------------------------------------------------------------------

class TestGrowthAnalysis:
    def _make_df(self):
        return pd.DataFrame({
            "dt": [
                "2023-01-01", "2023-02-01", "2023-03-01", "2023-04-01",
                "2023-05-01", "2023-06-01", "2023-07-01", "2023-08-01",
                "2023-09-01", "2023-10-01", "2023-11-01", "2023-12-01",
                "2024-01-01",
            ],
            "metric": [100, 110, 105, 120, 130, 125, 140, 135, 150, 160, 155, 170, 120],
        })

    def test_basic_monthly_growth(self, with_df_business):
        df = self._make_df()
        result = with_df_business(df, growth_analysis, "test_conn", "SELECT 1",
                          metric_col="metric", time_col="dt", period="month")
        assert "성장률 분석" in result
        assert "MoM" in result
        assert "CAGR" in result

    def test_unknown_conn_returns_error(self):
        result = growth_analysis("bad_conn", "SELECT 1", "metric", "dt")
        assert "[ERROR]" in result

    def test_missing_metric_col_returns_error(self, with_df_business):
        df = self._make_df()
        result = with_df_business(df, growth_analysis, "test_conn", "SELECT 1",
                          metric_col="no_col", time_col="dt")
        assert "[ERROR]" in result

    def test_invalid_period_returns_error(self, with_df_business):
        df = self._make_df()
        result = with_df_business(df, growth_analysis, "test_conn", "SELECT 1",
                          metric_col="metric", time_col="dt", period="decade")
        assert "[ERROR]" in result

    def test_yoy_growth_with_sufficient_data(self, with_df_business):
        df = self._make_df()
        result = with_df_business(df, growth_analysis, "test_conn", "SELECT 1",
                          metric_col="metric", time_col="dt", period="month")
        assert "YoY" in result

    def test_single_period_no_cagr(self, with_df_business):
        df = pd.DataFrame({
            "dt": ["2024-01-01"],
            "metric": [100.0],
        })
        result = with_df_business(df, growth_analysis, "test_conn", "SELECT 1",
                          metric_col="metric", time_col="dt", period="month")
        assert "성장률 분석" in result
        assert "데이터 부족" in result
