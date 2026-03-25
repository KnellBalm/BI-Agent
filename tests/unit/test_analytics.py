"""bi_agent_mcp.tools.analytics 단위 테스트."""
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from bi_agent_mcp.tools.analytics import (
    trend_analysis,
    correlation_analysis,
    distribution_analysis,
    segment_analysis,
    funnel_analysis,
    cohort_analysis,
    pivot_table,
    top_n_analysis,
)

# ---------------------------------------------------------------------------
# 공통 헬퍼
# ---------------------------------------------------------------------------

def _make_patches(df: pd.DataFrame):
    conn_info = MagicMock()
    mock_conn = MagicMock()
    return [
        patch("bi_agent_mcp.tools.analytics._connections", {"test_conn": conn_info}),
        patch("bi_agent_mcp.tools.analytics._get_conn", return_value=mock_conn),
        patch("bi_agent_mcp.tools.analytics._validate_select", return_value=None),
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
# trend_analysis
# ---------------------------------------------------------------------------

class TestTrendAnalysis:
    def test_basic_monthly_trend(self):
        df = pd.DataFrame({
            "dt": ["2024-01-01", "2024-02-01", "2024-03-01"],
            "revenue": [100.0, 120.0, 90.0],
        })
        result = _with_df(df, trend_analysis, "test_conn", "SELECT 1",
                          time_col="dt", metric_cols=["revenue"], period="month")
        assert "트렌드 분석" in result
        assert "revenue" in result
        assert "증감률" in result

    def test_missing_time_col_returns_error(self):
        df = pd.DataFrame({"revenue": [100.0]})
        result = _with_df(df, trend_analysis, "test_conn", "SELECT 1",
                          time_col="no_col", metric_cols=["revenue"])
        assert "[ERROR]" in result

    def test_invalid_period_returns_error(self):
        df = pd.DataFrame({"dt": ["2024-01-01"], "revenue": [100.0]})
        result = _with_df(df, trend_analysis, "test_conn", "SELECT 1",
                          time_col="dt", metric_cols=["revenue"], period="decade")
        assert "[ERROR]" in result

    def test_invalid_metric_cols_returns_error(self):
        df = pd.DataFrame({"dt": ["2024-01-01"], "revenue": [100.0]})
        result = _with_df(df, trend_analysis, "test_conn", "SELECT 1",
                          time_col="dt", metric_cols=["no_col"])
        assert "[ERROR]" in result

    def test_validate_error_propagates(self):
        with patch("bi_agent_mcp.tools.analytics._validate_select", return_value="SELECT only"):
            result = trend_analysis("test_conn", "DELETE FROM t",
                                    time_col="dt", metric_cols=["v"])
        assert "[ERROR]" in result

    def test_unknown_conn_id_returns_error(self):
        with patch("bi_agent_mcp.tools.analytics._connections", {}):
            with patch("bi_agent_mcp.tools.analytics._validate_select", return_value=None):
                result = trend_analysis("no_conn", "SELECT 1",
                                        time_col="dt", metric_cols=["v"])
        assert "[ERROR]" in result

    def test_period_day(self):
        df = pd.DataFrame({
            "dt": ["2024-01-01", "2024-01-02"],
            "v": [10.0, 20.0],
        })
        result = _with_df(df, trend_analysis, "test_conn", "SELECT 1",
                          time_col="dt", metric_cols=["v"], period="day")
        assert "트렌드 분석" in result


# ---------------------------------------------------------------------------
# correlation_analysis
# ---------------------------------------------------------------------------

class TestCorrelationAnalysis:
    def test_basic_correlation(self):
        df = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [2.0, 4.0, 6.0]})
        result = _with_df(df, correlation_analysis, "test_conn", "SELECT 1")
        assert "상관관계 분석" in result
        assert "1.000" in result

    def test_strong_correlation_summary(self):
        df = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 5.0],
                           "y": [2.0, 4.0, 6.0, 8.0, 10.0]})
        result = _with_df(df, correlation_analysis, "test_conn", "SELECT 1")
        assert "강한 상관관계" in result

    def test_no_strong_correlation(self):
        import numpy as np
        rng = np.random.default_rng(42)
        df = pd.DataFrame({"x": rng.random(50), "y": rng.random(50)})
        result = _with_df(df, correlation_analysis, "test_conn", "SELECT 1")
        assert "발견되지 않았습니다" in result

    def test_columns_filter(self):
        df = pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0], "c": [5.0, 6.0]})
        result = _with_df(df, correlation_analysis, "test_conn", "SELECT 1",
                          columns=["a", "b"])
        assert "a" in result

    def test_invalid_columns_returns_error(self):
        df = pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]})
        result = _with_df(df, correlation_analysis, "test_conn", "SELECT 1",
                          columns=["no_col"])
        assert "[ERROR]" in result

    def test_single_numeric_col_returns_error(self):
        df = pd.DataFrame({"a": [1.0, 2.0], "b": ["x", "y"]})
        result = _with_df(df, correlation_analysis, "test_conn", "SELECT 1")
        assert "[ERROR]" in result


# ---------------------------------------------------------------------------
# distribution_analysis
# ---------------------------------------------------------------------------

class TestDistributionAnalysis:
    def test_basic_distribution(self):
        df = pd.DataFrame({"value": list(range(1, 101))})
        result = _with_df(df, distribution_analysis, "test_conn", "SELECT 1",
                          column="value")
        assert "분포 분석" in result
        assert "평균" in result
        assert "구간 분포" in result

    def test_missing_column_returns_error(self):
        df = pd.DataFrame({"value": [1.0, 2.0]})
        result = _with_df(df, distribution_analysis, "test_conn", "SELECT 1",
                          column="no_col")
        assert "[ERROR]" in result

    def test_non_numeric_column_returns_error(self):
        df = pd.DataFrame({"value": ["a", "b", "c"]})
        result = _with_df(df, distribution_analysis, "test_conn", "SELECT 1",
                          column="value")
        assert "[ERROR]" in result

    def test_custom_bins(self):
        df = pd.DataFrame({"value": list(range(1, 21))})
        result = _with_df(df, distribution_analysis, "test_conn", "SELECT 1",
                          column="value", bins=5)
        assert "bins=5" in result

    def test_percentiles_present(self):
        df = pd.DataFrame({"value": list(range(1, 101))})
        result = _with_df(df, distribution_analysis, "test_conn", "SELECT 1",
                          column="value")
        assert "p90" in result
        assert "p95" in result


# ---------------------------------------------------------------------------
# segment_analysis
# ---------------------------------------------------------------------------

class TestSegmentAnalysis:
    def test_basic_segment(self):
        df = pd.DataFrame({"region": ["A", "B", "A", "B"],
                           "sales": [10.0, 20.0, 30.0, 40.0]})
        result = _with_df(df, segment_analysis, "test_conn", "SELECT 1",
                          group_col="region", metric_col="sales")
        assert "세그먼트 분석" in result
        assert "비율(%)" in result

    def test_invalid_agg_returns_error(self):
        df = pd.DataFrame({"region": ["A"], "sales": [10.0]})
        result = _with_df(df, segment_analysis, "test_conn", "SELECT 1",
                          group_col="region", metric_col="sales", agg="median")
        assert "[ERROR]" in result

    def test_missing_group_col_returns_error(self):
        df = pd.DataFrame({"sales": [10.0]})
        result = _with_df(df, segment_analysis, "test_conn", "SELECT 1",
                          group_col="no_col", metric_col="sales")
        assert "[ERROR]" in result

    def test_missing_metric_col_returns_error(self):
        df = pd.DataFrame({"region": ["A"]})
        result = _with_df(df, segment_analysis, "test_conn", "SELECT 1",
                          group_col="region", metric_col="no_col")
        assert "[ERROR]" in result

    def test_avg_agg(self):
        df = pd.DataFrame({"region": ["A", "A", "B"],
                           "sales": [10.0, 20.0, 30.0]})
        result = _with_df(df, segment_analysis, "test_conn", "SELECT 1",
                          group_col="region", metric_col="sales", agg="avg")
        assert "세그먼트 분석" in result


# ---------------------------------------------------------------------------
# funnel_analysis
# ---------------------------------------------------------------------------

class TestFunnelAnalysis:
    def test_basic_funnel(self):
        dfs = [
            pd.DataFrame({"cnt": [1000]}),
            pd.DataFrame({"cnt": [500]}),
            pd.DataFrame({"cnt": [100]}),
        ]
        call_count = [0]

        def fake_fetch(conn_id, sql):
            idx = call_count[0]
            call_count[0] += 1
            return dfs[idx], ""

        steps = [
            {"name": "방문", "sql": "SELECT 1000"},
            {"name": "가입", "sql": "SELECT 500"},
            {"name": "구매", "sql": "SELECT 100"},
        ]
        with patch("bi_agent_mcp.tools.analytics._fetch_df", side_effect=fake_fetch):
            result = funnel_analysis("test_conn", steps)

        assert "퍼널 분석" in result
        assert "50.0%" in result
        assert "10.0%" in result

    def test_empty_steps_returns_error(self):
        result = funnel_analysis("test_conn", [])
        assert "[ERROR]" in result

    def test_step_fetch_error_propagates(self):
        steps = [{"name": "방문", "sql": "DELETE FROM t"}]
        with patch("bi_agent_mcp.tools.analytics._fetch_df",
                   return_value=(None, "[ERROR] SELECT only")):
            result = funnel_analysis("test_conn", steps)
        assert "[ERROR]" in result

    def test_empty_step_df_treated_as_zero(self):
        steps = [{"name": "방문", "sql": "SELECT 0"}]
        with patch("bi_agent_mcp.tools.analytics._fetch_df",
                   return_value=(pd.DataFrame(), "")):
            result = funnel_analysis("test_conn", steps)
        assert "퍼널 분석" in result


# ---------------------------------------------------------------------------
# cohort_analysis
# ---------------------------------------------------------------------------

class TestCohortAnalysis:
    def _build_df(self):
        return pd.DataFrame({
            "user_id": [1, 1, 2, 3, 3],
            "join_date": ["2024-01-01", "2024-01-01", "2024-02-01",
                          "2024-01-01", "2024-01-01"],
            "activity_date": ["2024-01-15", "2024-02-15", "2024-02-10",
                              "2024-01-20", "2024-03-20"],
        })

    def test_basic_cohort(self):
        df = self._build_df()
        result = _with_df(df, cohort_analysis, "test_conn", "SELECT 1",
                          user_col="user_id", cohort_date_col="join_date",
                          activity_date_col="activity_date")
        assert "코호트 리텐션 분석" in result
        assert "M+0" in result

    def test_missing_user_col_returns_error(self):
        df = pd.DataFrame({"join_date": ["2024-01-01"],
                           "activity_date": ["2024-01-01"]})
        result = _with_df(df, cohort_analysis, "test_conn", "SELECT 1",
                          user_col="no_col", cohort_date_col="join_date",
                          activity_date_col="activity_date")
        assert "[ERROR]" in result

    def test_missing_cohort_date_col_returns_error(self):
        df = pd.DataFrame({"user_id": [1], "activity_date": ["2024-01-01"]})
        result = _with_df(df, cohort_analysis, "test_conn", "SELECT 1",
                          user_col="user_id", cohort_date_col="no_col",
                          activity_date_col="activity_date")
        assert "[ERROR]" in result

    def test_missing_activity_date_col_returns_error(self):
        df = pd.DataFrame({"user_id": [1], "join_date": ["2024-01-01"]})
        result = _with_df(df, cohort_analysis, "test_conn", "SELECT 1",
                          user_col="user_id", cohort_date_col="join_date",
                          activity_date_col="no_col")
        assert "[ERROR]" in result


# ---------------------------------------------------------------------------
# pivot_table
# ---------------------------------------------------------------------------

class TestPivotTable:
    def _build_df(self):
        return pd.DataFrame({
            "region": ["A", "A", "B", "B"],
            "month": ["Jan", "Feb", "Jan", "Feb"],
            "sales": [100.0, 200.0, 150.0, 250.0],
        })

    def test_basic_pivot(self):
        df = self._build_df()
        result = _with_df(df, pivot_table, "test_conn", "SELECT 1",
                          index_col="region", columns_col="month", values_col="sales")
        assert "피벗 테이블" in result
        assert "region" in result

    def test_invalid_aggfunc_returns_error(self):
        df = self._build_df()
        result = _with_df(df, pivot_table, "test_conn", "SELECT 1",
                          index_col="region", columns_col="month",
                          values_col="sales", aggfunc="median")
        assert "[ERROR]" in result

    def test_missing_index_col_returns_error(self):
        df = pd.DataFrame({"month": ["Jan"], "sales": [100.0]})
        result = _with_df(df, pivot_table, "test_conn", "SELECT 1",
                          index_col="no_col", columns_col="month", values_col="sales")
        assert "[ERROR]" in result

    def test_missing_values_col_returns_error(self):
        df = pd.DataFrame({"region": ["A"], "month": ["Jan"]})
        result = _with_df(df, pivot_table, "test_conn", "SELECT 1",
                          index_col="region", columns_col="month", values_col="no_col")
        assert "[ERROR]" in result

    def test_mean_aggfunc(self):
        df = pd.DataFrame({
            "region": ["A", "A"],
            "month": ["Jan", "Jan"],
            "sales": [100.0, 200.0],
        })
        result = _with_df(df, pivot_table, "test_conn", "SELECT 1",
                          index_col="region", columns_col="month",
                          values_col="sales", aggfunc="mean")
        assert "피벗 테이블" in result


# ---------------------------------------------------------------------------
# top_n_analysis
# ---------------------------------------------------------------------------

class TestTopNAnalysis:
    def test_basic_top_n(self):
        df = pd.DataFrame({"product": list("ABCDE"),
                           "revenue": [50.0, 30.0, 80.0, 20.0, 60.0]})
        result = _with_df(df, top_n_analysis, "test_conn", "SELECT 1",
                          metric_col="revenue", n=3)
        assert "Top-3 분석" in result
        assert "누적비율(%)" in result

    def test_missing_metric_col_returns_error(self):
        df = pd.DataFrame({"product": ["A"], "revenue": [100.0]})
        result = _with_df(df, top_n_analysis, "test_conn", "SELECT 1",
                          metric_col="no_col")
        assert "[ERROR]" in result

    def test_group_col_top_n(self):
        df = pd.DataFrame({
            "region": ["A", "A", "B", "B"],
            "product": ["p1", "p2", "p3", "p4"],
            "revenue": [100.0, 50.0, 80.0, 30.0],
        })
        result = _with_df(df, top_n_analysis, "test_conn", "SELECT 1",
                          metric_col="revenue", n=1, group_col="region")
        assert "Top-1 분석" in result
        assert "region" in result

    def test_missing_group_col_returns_error(self):
        df = pd.DataFrame({"revenue": [100.0]})
        result = _with_df(df, top_n_analysis, "test_conn", "SELECT 1",
                          metric_col="revenue", group_col="no_col")
        assert "[ERROR]" in result

    def test_n_larger_than_data(self):
        df = pd.DataFrame({"product": ["A", "B"], "revenue": [10.0, 20.0]})
        result = _with_df(df, top_n_analysis, "test_conn", "SELECT 1",
                          metric_col="revenue", n=10)
        assert "Top-10 분석" in result
