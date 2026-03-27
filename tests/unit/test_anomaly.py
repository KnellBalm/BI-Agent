"""bi_agent_mcp.tools.anomaly 단위 테스트."""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

from bi_agent_mcp.tools.anomaly import iqr_anomaly_detection, zscore_anomaly_detection


# ---------------------------------------------------------------------------
# 공통 헬퍼
# ---------------------------------------------------------------------------

def _make_patches(df: pd.DataFrame):
    conn_info = MagicMock()
    mock_conn = MagicMock()
    return [
        patch("bi_agent_mcp.tools.anomaly._connections", {"test_conn": conn_info}),
        patch("bi_agent_mcp.tools.anomaly._get_conn", return_value=mock_conn),
        patch("bi_agent_mcp.tools.anomaly._validate_select", return_value=None),
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


def _make_normal_df(n=20, seed=42):
    """정규 분포 기반 정상 데이터 생성."""
    rng = np.random.default_rng(seed)
    values = rng.normal(loc=100.0, scale=10.0, size=n)
    return pd.DataFrame({"value": values})


def _make_anomaly_df():
    """명확한 이상치 포함 데이터."""
    values = [100.0, 102.0, 98.0, 101.0, 99.0, 97.0, 103.0, 500.0, -200.0, 100.0]
    return pd.DataFrame({"value": values})


# ---------------------------------------------------------------------------
# iqr_anomaly_detection
# ---------------------------------------------------------------------------

class TestIqrAnomalyDetection:
    def test_detects_anomalies(self):
        """명확한 이상치가 탐지되어야 한다."""
        df = _make_anomaly_df()
        result = _with_df(df, iqr_anomaly_detection, "test_conn", "SELECT 1",
                          metric_col="value")
        assert "IQR 이상치 탐지" in result
        assert "이상치 수" in result
        # 500.0과 -200.0은 이상치여야 함
        assert "500" in result or "이상치 목록" in result

    def test_no_anomalies_in_uniform_data(self):
        """균일 분포 데이터에서는 이상치가 없어야 한다."""
        df = pd.DataFrame({"value": [10.0, 10.0, 10.0, 10.0, 10.0]})
        # 모두 같은 값이면 IQR=0이므로 경계=10, 이상치 없음
        result = _with_df(df, iqr_anomaly_detection, "test_conn", "SELECT 1",
                          metric_col="value")
        assert "IQR 이상치 탐지" in result
        assert "이상치가 발견되지 않았습니다" in result

    def test_missing_metric_col_returns_error(self):
        """metric_col이 없으면 오류 반환."""
        df = pd.DataFrame({"other": [1.0, 2.0, 3.0, 4.0]})
        result = _with_df(df, iqr_anomaly_detection, "test_conn", "SELECT 1",
                          metric_col="value")
        assert "[ERROR]" in result

    def test_missing_group_col_returns_error(self):
        """group_col이 없으면 오류 반환."""
        df = _make_anomaly_df()
        result = _with_df(df, iqr_anomaly_detection, "test_conn", "SELECT 1",
                          metric_col="value", group_col="no_such_col")
        assert "[ERROR]" in result

    def test_insufficient_rows_returns_error(self):
        """4행 미만이면 오류 반환."""
        df = pd.DataFrame({"value": [1.0, 2.0, 3.0]})
        result = _with_df(df, iqr_anomaly_detection, "test_conn", "SELECT 1",
                          metric_col="value")
        assert "[ERROR]" in result
        assert "최소" in result

    def test_group_col_detection(self):
        """group_col 있으면 그룹별로 IQR 계산."""
        df = pd.DataFrame({
            "group": ["A", "A", "A", "A", "A", "B", "B", "B", "B", "B"],
            "value": [10.0, 11.0, 10.5, 10.2, 200.0, 50.0, 51.0, 49.0, 50.5, -100.0],
        })
        result = _with_df(df, iqr_anomaly_detection, "test_conn", "SELECT 1",
                          metric_col="value", group_col="group")
        assert "IQR 이상치 탐지" in result
        assert "그룹별 정상 범위" in result

    def test_validate_select_error_propagates(self):
        """_validate_select 오류가 전달되어야 한다."""
        with patch("bi_agent_mcp.tools.anomaly._validate_select", return_value="SELECT only"):
            result = iqr_anomaly_detection("test_conn", "DELETE FROM t", metric_col="value")
        assert "[ERROR]" in result

    def test_connection_not_found(self):
        """존재하지 않는 연결 ID면 오류 반환."""
        with patch("bi_agent_mcp.tools.anomaly._connections", {}), \
             patch("bi_agent_mcp.tools.anomaly._validate_select", return_value=None):
            result = iqr_anomaly_detection("missing_conn", "SELECT 1", metric_col="value")
        assert "[ERROR]" in result
        assert "찾을 수 없습니다" in result

    def test_custom_multiplier(self):
        """multiplier 변경 시 경계가 달라진다."""
        df = _make_anomaly_df()
        # multiplier=10이면 경계가 넓어 이상치 줄어듦
        result = _with_df(df, iqr_anomaly_detection, "test_conn", "SELECT 1",
                          metric_col="value", multiplier=10.0)
        assert "multiplier=10.0" in result

    def test_result_contains_normal_range(self):
        """정상 범위 정보가 포함되어야 한다."""
        df = _make_anomaly_df()
        result = _with_df(df, iqr_anomaly_detection, "test_conn", "SELECT 1",
                          metric_col="value")
        assert "정상 범위" in result or "하한" in result


# ---------------------------------------------------------------------------
# zscore_anomaly_detection
# ---------------------------------------------------------------------------

class TestZscoreAnomalyDetection:
    def test_detects_anomalies(self):
        """명확한 이상치가 탐지되어야 한다."""
        df = _make_anomaly_df()
        result = _with_df(df, zscore_anomaly_detection, "test_conn", "SELECT 1",
                          metric_col="value")
        assert "Z-Score 이상치 탐지" in result
        assert "이상치 수" in result

    def test_no_anomalies_in_tight_data(self):
        """Z-score가 threshold 미만이면 이상치 없음."""
        df = pd.DataFrame({"value": [100.0, 101.0, 99.0, 100.5, 99.5,
                                      100.2, 99.8, 100.1, 99.9, 100.0]})
        result = _with_df(df, zscore_anomaly_detection, "test_conn", "SELECT 1",
                          metric_col="value", threshold=3.0)
        assert "Z-Score 이상치 탐지" in result
        assert "이상치가 발견되지 않았습니다" in result

    def test_missing_metric_col_returns_error(self):
        """metric_col이 없으면 오류 반환."""
        df = pd.DataFrame({"other": [1.0, 2.0, 3.0]})
        result = _with_df(df, zscore_anomaly_detection, "test_conn", "SELECT 1",
                          metric_col="value")
        assert "[ERROR]" in result

    def test_insufficient_rows_returns_error(self):
        """3행 미만이면 오류 반환."""
        df = pd.DataFrame({"value": [1.0, 2.0]})
        result = _with_df(df, zscore_anomaly_detection, "test_conn", "SELECT 1",
                          metric_col="value")
        assert "[ERROR]" in result
        assert "최소" in result

    def test_zero_std_returns_error(self):
        """표준편차가 0이면 오류 반환."""
        df = pd.DataFrame({"value": [5.0, 5.0, 5.0, 5.0]})
        result = _with_df(df, zscore_anomaly_detection, "test_conn", "SELECT 1",
                          metric_col="value")
        assert "[ERROR]" in result
        assert "표준편차" in result

    def test_severity_classification(self):
        """심각도 분류(경고/심각/위험)가 포함되어야 한다."""
        # 큰 이상치 생성 (z > 3)
        base = [100.0] * 20
        df = pd.DataFrame({"value": base + [10000.0]})
        result = _with_df(df, zscore_anomaly_detection, "test_conn", "SELECT 1",
                          metric_col="value")
        assert "심각도" in result

    def test_time_col_period_context(self):
        """time_col + period 있으면 시계열 컨텍스트 포함."""
        dates = pd.date_range("2024-01-01", periods=30, freq="D")
        values = [100.0] * 28 + [5000.0, -5000.0]
        df = pd.DataFrame({"dt": dates, "value": values})
        result = _with_df(df, zscore_anomaly_detection, "test_conn", "SELECT 1",
                          metric_col="value", time_col="dt", period="month")
        assert "Z-Score 이상치 탐지" in result

    def test_missing_time_col_returns_error(self):
        """time_col이 지정되었지만 없으면 오류 반환."""
        df = _make_anomaly_df()
        result = _with_df(df, zscore_anomaly_detection, "test_conn", "SELECT 1",
                          metric_col="value", time_col="no_such_col")
        assert "[ERROR]" in result

    def test_validate_select_error_propagates(self):
        """_validate_select 오류가 전달되어야 한다."""
        with patch("bi_agent_mcp.tools.anomaly._validate_select", return_value="SELECT only"):
            result = zscore_anomaly_detection("test_conn", "DELETE FROM t", metric_col="value")
        assert "[ERROR]" in result

    def test_connection_not_found(self):
        """존재하지 않는 연결 ID면 오류 반환."""
        with patch("bi_agent_mcp.tools.anomaly._connections", {}), \
             patch("bi_agent_mcp.tools.anomaly._validate_select", return_value=None):
            result = zscore_anomaly_detection("missing_conn", "SELECT 1", metric_col="value")
        assert "[ERROR]" in result
        assert "찾을 수 없습니다" in result

    def test_custom_threshold(self):
        """threshold 변경 시 결과 헤더에 반영."""
        df = _make_anomaly_df()
        result = _with_df(df, zscore_anomaly_detection, "test_conn", "SELECT 1",
                          metric_col="value", threshold=2.0)
        assert "threshold=|Z|>2.0" in result

    def test_zscore_distribution_in_summary(self):
        """요약에 Z-Score 분포 정보 포함."""
        df = _make_anomaly_df()
        result = _with_df(df, zscore_anomaly_detection, "test_conn", "SELECT 1",
                          metric_col="value")
        assert "Z-Score 분포" in result
