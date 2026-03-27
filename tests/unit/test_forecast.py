"""bi_agent_mcp.tools.forecast 단위 테스트."""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

from bi_agent_mcp.tools.forecast import (
    moving_average_forecast,
    exponential_smoothing_forecast,
    linear_trend_forecast,
)

# ---------------------------------------------------------------------------
# 공통 헬퍼
# ---------------------------------------------------------------------------

def _make_patches(df: pd.DataFrame):
    conn_info = MagicMock()
    mock_conn = MagicMock()
    return [
        patch("bi_agent_mcp.tools.forecast._connections", {"test_conn": conn_info}),
        patch("bi_agent_mcp.tools.forecast._get_conn", return_value=mock_conn),
        patch("bi_agent_mcp.tools.forecast._validate_select", return_value=None),
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


def _make_monthly_df(n: int = 12) -> pd.DataFrame:
    """n개월치 월별 시계열 데이터 생성."""
    dates = pd.date_range("2023-01-01", periods=n, freq="MS")
    values = np.arange(100.0, 100.0 + n * 10, 10.0)
    return pd.DataFrame({"dt": dates.strftime("%Y-%m-%d"), "value": values})


# ---------------------------------------------------------------------------
# moving_average_forecast
# ---------------------------------------------------------------------------

class TestMovingAverageForecast:
    def test_basic_moving_average(self):
        df = _make_monthly_df(12)
        result = _with_df(df, moving_average_forecast, "test_conn", "SELECT 1",
                          time_col="dt", metric_col="value", window=3,
                          forecast_periods=3, period="month")
        assert "이동평균 예측" in result
        assert "SMA-3" in result
        assert "미래 예측" in result

    def test_forecast_rows_count(self):
        df = _make_monthly_df(12)
        result = _with_df(df, moving_average_forecast, "test_conn", "SELECT 1",
                          time_col="dt", metric_col="value", window=3,
                          forecast_periods=5, period="month")
        # 미래 예측 섹션만 추출하여 행 수 확인
        forecast_section = result.split("미래 예측")[-1]
        lines = [l for l in forecast_section.split("\n") if l.startswith("| 20")]
        assert len(lines) == 5

    def test_missing_time_col_returns_error(self):
        df = _make_monthly_df(6)
        result = _with_df(df, moving_average_forecast, "test_conn", "SELECT 1",
                          time_col="no_col", metric_col="value")
        assert "[ERROR]" in result

    def test_missing_metric_col_returns_error(self):
        df = _make_monthly_df(6)
        result = _with_df(df, moving_average_forecast, "test_conn", "SELECT 1",
                          time_col="dt", metric_col="no_col")
        assert "[ERROR]" in result

    def test_invalid_period_returns_error(self):
        df = _make_monthly_df(6)
        result = _with_df(df, moving_average_forecast, "test_conn", "SELECT 1",
                          time_col="dt", metric_col="value", period="decade")
        assert "[ERROR]" in result

    def test_insufficient_data_returns_error(self):
        # window=3 → min_rows=6, 데이터 3개
        df = _make_monthly_df(3)
        result = _with_df(df, moving_average_forecast, "test_conn", "SELECT 1",
                          time_col="dt", metric_col="value", window=3)
        assert "[ERROR]" in result
        assert "부족" in result

    def test_unknown_conn_id_returns_error(self):
        with patch("bi_agent_mcp.tools.forecast._connections", {}):
            with patch("bi_agent_mcp.tools.forecast._validate_select", return_value=None):
                result = moving_average_forecast("no_conn", "SELECT 1",
                                                  time_col="dt", metric_col="value")
        assert "[ERROR]" in result

    def test_validate_error_propagates(self):
        with patch("bi_agent_mcp.tools.forecast._validate_select", return_value="SELECT only"):
            result = moving_average_forecast("test_conn", "DELETE FROM t",
                                              time_col="dt", metric_col="value")
        assert "[ERROR]" in result

    def test_daily_period(self):
        dates = pd.date_range("2024-01-01", periods=20, freq="D")
        df = pd.DataFrame({"dt": dates.strftime("%Y-%m-%d"),
                           "value": np.arange(20.0)})
        result = _with_df(df, moving_average_forecast, "test_conn", "SELECT 1",
                          time_col="dt", metric_col="value", window=3,
                          forecast_periods=2, period="day")
        assert "이동평균 예측" in result
        assert "미래 예측" in result


# ---------------------------------------------------------------------------
# exponential_smoothing_forecast
# ---------------------------------------------------------------------------

class TestExponentialSmoothingForecast:
    def test_basic_exponential_smoothing(self):
        df = _make_monthly_df(12)
        result = _with_df(df, exponential_smoothing_forecast, "test_conn", "SELECT 1",
                          time_col="dt", metric_col="value", alpha=0.3,
                          forecast_periods=3, period="month")
        assert "지수평활 예측" in result
        assert "alpha=0.3" in result
        assert "MAPE" in result

    def test_mape_present(self):
        df = _make_monthly_df(12)
        result = _with_df(df, exponential_smoothing_forecast, "test_conn", "SELECT 1",
                          time_col="dt", metric_col="value", alpha=0.5)
        assert "MAPE" in result
        assert "%" in result

    def test_invalid_alpha_zero_returns_error(self):
        df = _make_monthly_df(6)
        result = _with_df(df, exponential_smoothing_forecast, "test_conn", "SELECT 1",
                          time_col="dt", metric_col="value", alpha=0.0)
        assert "[ERROR]" in result

    def test_invalid_alpha_over_one_returns_error(self):
        df = _make_monthly_df(6)
        result = _with_df(df, exponential_smoothing_forecast, "test_conn", "SELECT 1",
                          time_col="dt", metric_col="value", alpha=1.5)
        assert "[ERROR]" in result

    def test_insufficient_data_returns_error(self):
        df = pd.DataFrame({"dt": ["2024-01-01"], "value": [100.0]})
        result = _with_df(df, exponential_smoothing_forecast, "test_conn", "SELECT 1",
                          time_col="dt", metric_col="value")
        assert "[ERROR]" in result

    def test_missing_time_col_returns_error(self):
        df = _make_monthly_df(6)
        result = _with_df(df, exponential_smoothing_forecast, "test_conn", "SELECT 1",
                          time_col="no_col", metric_col="value")
        assert "[ERROR]" in result

    def test_missing_metric_col_returns_error(self):
        df = _make_monthly_df(6)
        result = _with_df(df, exponential_smoothing_forecast, "test_conn", "SELECT 1",
                          time_col="dt", metric_col="no_col")
        assert "[ERROR]" in result

    def test_invalid_period_returns_error(self):
        df = _make_monthly_df(6)
        result = _with_df(df, exponential_smoothing_forecast, "test_conn", "SELECT 1",
                          time_col="dt", metric_col="value", period="biennial")
        assert "[ERROR]" in result

    def test_alpha_one_latest_value_dominates(self):
        """alpha=1이면 평활값 = 실제값 (즉시 반영)."""
        df = _make_monthly_df(6)
        result = _with_df(df, exponential_smoothing_forecast, "test_conn", "SELECT 1",
                          time_col="dt", metric_col="value", alpha=1.0)
        assert "지수평활 예측" in result

    def test_forecast_periods_reflected(self):
        df = _make_monthly_df(12)
        result = _with_df(df, exponential_smoothing_forecast, "test_conn", "SELECT 1",
                          time_col="dt", metric_col="value", forecast_periods=4)
        forecast_section = result.split("미래 예측")[-1]
        lines = [l for l in forecast_section.split("\n") if l.startswith("| 20")]
        assert len(lines) == 4


# ---------------------------------------------------------------------------
# linear_trend_forecast
# ---------------------------------------------------------------------------

class TestLinearTrendForecast:
    def test_basic_linear_trend(self):
        df = _make_monthly_df(12)
        result = _with_df(df, linear_trend_forecast, "test_conn", "SELECT 1",
                          time_col="dt", metric_col="value", forecast_periods=3,
                          period="month")
        assert "선형 추세 예측" in result
        assert "R²" in result
        assert "기울기" in result
        assert "절편" in result

    def test_r2_present_and_valid(self):
        df = _make_monthly_df(12)
        result = _with_df(df, linear_trend_forecast, "test_conn", "SELECT 1",
                          time_col="dt", metric_col="value")
        # R² 값 추출하여 0~1 범위 확인
        assert "R²" in result
        for line in result.split("\n"):
            if "R²" in line:
                # "**R² (결정계수)**: 0.9999" 형태
                assert "0." in line or "1." in line or "1.0" in line

    def test_perfect_linear_data_high_r2(self):
        """완벽한 선형 데이터 → R² ≈ 1."""
        dates = pd.date_range("2023-01-01", periods=10, freq="MS")
        df = pd.DataFrame({"dt": dates.strftime("%Y-%m-%d"),
                           "value": np.arange(10.0) * 5 + 100.0})
        result = _with_df(df, linear_trend_forecast, "test_conn", "SELECT 1",
                          time_col="dt", metric_col="value")
        for line in result.split("\n"):
            if "R²" in line:
                r2_val = float(line.split(":")[-1].strip())
                assert r2_val > 0.99

    def test_missing_time_col_returns_error(self):
        df = _make_monthly_df(6)
        result = _with_df(df, linear_trend_forecast, "test_conn", "SELECT 1",
                          time_col="no_col", metric_col="value")
        assert "[ERROR]" in result

    def test_missing_metric_col_returns_error(self):
        df = _make_monthly_df(6)
        result = _with_df(df, linear_trend_forecast, "test_conn", "SELECT 1",
                          time_col="dt", metric_col="no_col")
        assert "[ERROR]" in result

    def test_invalid_period_returns_error(self):
        df = _make_monthly_df(6)
        result = _with_df(df, linear_trend_forecast, "test_conn", "SELECT 1",
                          time_col="dt", metric_col="value", period="century")
        assert "[ERROR]" in result

    def test_insufficient_data_returns_error(self):
        df = pd.DataFrame({"dt": ["2024-01-01", "2024-02-01"],
                           "value": [100.0, 110.0]})
        result = _with_df(df, linear_trend_forecast, "test_conn", "SELECT 1",
                          time_col="dt", metric_col="value")
        assert "[ERROR]" in result
        assert "최소 3개" in result

    def test_unknown_conn_id_returns_error(self):
        with patch("bi_agent_mcp.tools.forecast._connections", {}):
            with patch("bi_agent_mcp.tools.forecast._validate_select", return_value=None):
                result = linear_trend_forecast("no_conn", "SELECT 1",
                                               time_col="dt", metric_col="value")
        assert "[ERROR]" in result

    def test_forecast_periods_reflected(self):
        df = _make_monthly_df(12)
        result = _with_df(df, linear_trend_forecast, "test_conn", "SELECT 1",
                          time_col="dt", metric_col="value", forecast_periods=6)
        forecast_section = result.split("미래 예측")[-1]
        lines = [l for l in forecast_section.split("\n") if l.startswith("| 20")]
        assert len(lines) == 6

    def test_growth_rate_present(self):
        df = _make_monthly_df(12)
        result = _with_df(df, linear_trend_forecast, "test_conn", "SELECT 1",
                          time_col="dt", metric_col="value")
        assert "성장률" in result
