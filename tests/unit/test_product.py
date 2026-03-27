"""bi_agent_mcp.tools.product 단위 테스트."""
import sqlite3
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

from bi_agent_mcp.tools.product import (
    active_users,
    retention_curve,
    feature_adoption,
    ab_test_analysis,
    user_journey,
)


# ---------------------------------------------------------------------------
# 공통 헬퍼
# ---------------------------------------------------------------------------

def _make_patches(df: pd.DataFrame):
    conn_info = MagicMock()
    mock_conn = MagicMock()
    return [
        patch("bi_agent_mcp.tools.product._connections", {"test_conn": conn_info}),
        patch("bi_agent_mcp.tools.product._get_conn", return_value=mock_conn),
        patch("bi_agent_mcp.tools.product._validate_select", return_value=None),
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
# active_users
# ---------------------------------------------------------------------------

class TestActiveUsers:
    def test_dau_basic(self):
        df = pd.DataFrame({
            "user_id": ["u1", "u2", "u1", "u3"],
            "event_date": ["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-02"],
        })
        result = _with_df(df, active_users, "test_conn", "SELECT 1",
                          user_col="user_id", date_col="event_date", period="day")
        assert "활성 사용자 분석" in result
        assert "DAU" in result
        assert "2024-01-01" in result

    def test_mau_aggregation(self):
        df = pd.DataFrame({
            "user_id": ["u1", "u2", "u1", "u3", "u4"],
            "event_date": ["2024-01-05", "2024-01-10", "2024-02-01", "2024-02-15", "2024-02-20"],
        })
        result = _with_df(df, active_users, "test_conn", "SELECT 1",
                          user_col="user_id", date_col="event_date", period="month")
        assert "MAU" in result
        assert "평균" in result

    def test_unknown_conn_id(self):
        with patch("bi_agent_mcp.tools.product._connections", {}):
            with patch("bi_agent_mcp.tools.product._validate_select", return_value=None):
                result = active_users("no_conn", "SELECT 1", "user_id", "event_date")
        assert "[ERROR]" in result

    def test_invalid_period(self):
        df = pd.DataFrame({"user_id": ["u1"], "event_date": ["2024-01-01"]})
        result = _with_df(df, active_users, "test_conn", "SELECT 1",
                          user_col="user_id", date_col="event_date", period="year")
        assert "[ERROR]" in result

    def test_missing_user_col(self):
        df = pd.DataFrame({"event_date": ["2024-01-01"]})
        result = _with_df(df, active_users, "test_conn", "SELECT 1",
                          user_col="user_id", date_col="event_date")
        assert "[ERROR]" in result

    def test_wau_summary_stats(self):
        dates = pd.date_range("2024-01-01", periods=14, freq="D")
        df = pd.DataFrame({
            "user_id": [f"u{i % 5}" for i in range(14)],
            "event_date": [str(d.date()) for d in dates],
        })
        result = _with_df(df, active_users, "test_conn", "SELECT 1",
                          user_col="user_id", date_col="event_date", period="week")
        assert "WAU" in result
        assert "최대" in result


# ---------------------------------------------------------------------------
# retention_curve
# ---------------------------------------------------------------------------

class TestRetentionCurve:
    def test_auto_cohort_from_first_visit(self):
        df = pd.DataFrame({
            "user_id": ["u1", "u1", "u2", "u2"],
            "event_date": ["2024-01-01", "2024-01-08", "2024-01-01", "2024-01-15"],
        })
        result = _with_df(df, retention_curve, "test_conn", "SELECT 1",
                          user_col="user_id", date_col="event_date")
        assert "리텐션 곡선" in result
        assert "W+0" in result

    def test_explicit_cohort_col(self):
        df = pd.DataFrame({
            "user_id": ["u1", "u1", "u2"],
            "event_date": ["2024-01-08", "2024-01-15", "2024-01-08"],
            "cohort": ["2024-01-01", "2024-01-01", "2024-01-01"],
        })
        result = _with_df(df, retention_curve, "test_conn", "SELECT 1",
                          user_col="user_id", date_col="event_date", cohort_col="cohort")
        assert "리텐션 곡선" in result
        assert "코호트 크기" in result

    def test_unknown_conn_id(self):
        with patch("bi_agent_mcp.tools.product._connections", {}):
            with patch("bi_agent_mcp.tools.product._validate_select", return_value=None):
                result = retention_curve("no_conn", "SELECT 1", "user_id", "event_date")
        assert "[ERROR]" in result

    def test_missing_date_col(self):
        df = pd.DataFrame({"user_id": ["u1"]})
        result = _with_df(df, retention_curve, "test_conn", "SELECT 1",
                          user_col="user_id", date_col="event_date")
        assert "[ERROR]" in result

    def test_invalid_cohort_col(self):
        df = pd.DataFrame({
            "user_id": ["u1"],
            "event_date": ["2024-01-01"],
        })
        result = _with_df(df, retention_curve, "test_conn", "SELECT 1",
                          user_col="user_id", date_col="event_date", cohort_col="no_col")
        assert "[ERROR]" in result

    def test_single_user_single_event(self):
        df = pd.DataFrame({
            "user_id": ["u1"],
            "event_date": ["2024-01-01"],
        })
        result = _with_df(df, retention_curve, "test_conn", "SELECT 1",
                          user_col="user_id", date_col="event_date")
        assert "리텐션 곡선" in result
        assert "100%" in result


# ---------------------------------------------------------------------------
# feature_adoption
# ---------------------------------------------------------------------------

class TestFeatureAdoption:
    def test_basic_adoption(self):
        df = pd.DataFrame({
            "user_id": ["u1", "u2", "u3", "u1", "u2"],
            "feature": ["search", "search", "checkout", "checkout", "search"],
        })
        result = _with_df(df, feature_adoption, "test_conn", "SELECT 1",
                          user_col="user_id", feature_col="feature")
        assert "기능 도입률 분석" in result
        assert "search" in result
        assert "checkout" in result

    def test_with_date_col_trend(self):
        df = pd.DataFrame({
            "user_id": ["u1", "u2", "u1", "u3"],
            "feature": ["search", "search", "checkout", "search"],
            "event_date": ["2024-01-10", "2024-01-15", "2024-02-01", "2024-02-20"],
        })
        result = _with_df(df, feature_adoption, "test_conn", "SELECT 1",
                          user_col="user_id", feature_col="feature", date_col="event_date")
        assert "트렌드" in result
        assert "2024-01" in result

    def test_unknown_conn_id(self):
        with patch("bi_agent_mcp.tools.product._connections", {}):
            with patch("bi_agent_mcp.tools.product._validate_select", return_value=None):
                result = feature_adoption("no_conn", "SELECT 1", "user_id", "feature")
        assert "[ERROR]" in result

    def test_missing_feature_col(self):
        df = pd.DataFrame({"user_id": ["u1"]})
        result = _with_df(df, feature_adoption, "test_conn", "SELECT 1",
                          user_col="user_id", feature_col="feature")
        assert "[ERROR]" in result

    def test_top_bottom_summary(self):
        df = pd.DataFrame({
            "user_id": ["u1", "u2", "u3", "u1"],
            "feature": ["A", "A", "A", "B"],
        })
        result = _with_df(df, feature_adoption, "test_conn", "SELECT 1",
                          user_col="user_id", feature_col="feature")
        assert "최고 도입 기능" in result
        assert "최저 도입 기능" in result


# ---------------------------------------------------------------------------
# ab_test_analysis
# ---------------------------------------------------------------------------

class TestAbTestAnalysis:
    def test_significant_difference(self):
        rng = np.random.default_rng(42)
        control = rng.normal(10.0, 1.0, 100)
        treatment = rng.normal(12.0, 1.0, 100)
        df = pd.DataFrame({
            "group": ["control"] * 100 + ["treatment"] * 100,
            "metric": np.concatenate([control, treatment]),
        })
        result = _with_df(df, ab_test_analysis, "test_conn", "SELECT 1",
                          group_col="group", metric_col="metric")
        assert "A/B 테스트 분석" in result
        assert "유의미한 차이 있음" in result
        assert "p-value" in result

    def test_no_significant_difference(self):
        rng = np.random.default_rng(0)
        g1 = rng.normal(10.0, 1.0, 50)
        g2 = rng.normal(10.05, 1.0, 50)
        df = pd.DataFrame({
            "group": ["A"] * 50 + ["B"] * 50,
            "metric": np.concatenate([g1, g2]),
        })
        result = _with_df(df, ab_test_analysis, "test_conn", "SELECT 1",
                          group_col="group", metric_col="metric", confidence=0.95)
        assert "A/B 테스트 분석" in result
        # 통계 필드 존재 확인
        assert "Z-통계량" in result

    def test_three_groups_returns_error(self):
        df = pd.DataFrame({
            "group": ["A", "B", "C"],
            "metric": [1.0, 2.0, 3.0],
        })
        result = _with_df(df, ab_test_analysis, "test_conn", "SELECT 1",
                          group_col="group", metric_col="metric")
        assert "[ERROR]" in result

    def test_unknown_conn_id(self):
        with patch("bi_agent_mcp.tools.product._connections", {}):
            with patch("bi_agent_mcp.tools.product._validate_select", return_value=None):
                result = ab_test_analysis("no_conn", "SELECT 1", "group", "metric")
        assert "[ERROR]" in result

    def test_missing_metric_col(self):
        df = pd.DataFrame({"group": ["A", "B"]})
        result = _with_df(df, ab_test_analysis, "test_conn", "SELECT 1",
                          group_col="group", metric_col="value")
        assert "[ERROR]" in result

    def test_no_scipy_dependency(self):
        """scipy 없이도 동작 확인 — scipy import 차단 후 테스트."""
        import sys
        original = sys.modules.get("scipy")
        sys.modules["scipy"] = None  # type: ignore
        sys.modules["scipy.stats"] = None  # type: ignore
        try:
            df = pd.DataFrame({
                "group": ["A"] * 20 + ["B"] * 20,
                "metric": list(range(20)) + list(range(10, 30)),
            })
            result = _with_df(df, ab_test_analysis, "test_conn", "SELECT 1",
                              group_col="group", metric_col="metric")
            assert "[ERROR]" not in result
            assert "p-value" in result
        finally:
            if original is None:
                sys.modules.pop("scipy", None)
                sys.modules.pop("scipy.stats", None)
            else:
                sys.modules["scipy"] = original

    def test_single_group_insufficient_data(self):
        df = pd.DataFrame({
            "group": ["A", "B"],
            "metric": [1.0, 2.0],
        })
        result = _with_df(df, ab_test_analysis, "test_conn", "SELECT 1",
                          group_col="group", metric_col="metric")
        assert "[ERROR]" in result


# ---------------------------------------------------------------------------
# user_journey
# ---------------------------------------------------------------------------

class TestUserJourney:
    def test_basic_sequence_and_transition(self):
        df = pd.DataFrame({
            "user_id": ["u1", "u1", "u1", "u2", "u2"],
            "event": ["login", "search", "checkout", "login", "checkout"],
            "ts": ["2024-01-01 10:00", "2024-01-01 10:05", "2024-01-01 10:10",
                   "2024-01-01 11:00", "2024-01-01 11:05"],
        })
        result = _with_df(df, user_journey, "test_conn", "SELECT 1",
                          user_col="user_id", event_col="event", time_col="ts")
        assert "사용자 여정 분석" in result
        assert "시퀀스 패턴" in result
        assert "전환 매트릭스" in result

    def test_transition_matrix_values(self):
        df = pd.DataFrame({
            "user_id": ["u1", "u1", "u1"],
            "event": ["A", "B", "A"],
            "ts": ["2024-01-01 10:00", "2024-01-01 10:01", "2024-01-01 10:02"],
        })
        result = _with_df(df, user_journey, "test_conn", "SELECT 1",
                          user_col="user_id", event_col="event", time_col="ts")
        # A→B, B→A 전환이 있어야 함
        assert "A" in result
        assert "B" in result

    def test_unknown_conn_id(self):
        with patch("bi_agent_mcp.tools.product._connections", {}):
            with patch("bi_agent_mcp.tools.product._validate_select", return_value=None):
                result = user_journey("no_conn", "SELECT 1", "user_id", "event", "ts")
        assert "[ERROR]" in result

    def test_missing_event_col(self):
        df = pd.DataFrame({
            "user_id": ["u1"],
            "ts": ["2024-01-01"],
        })
        result = _with_df(df, user_journey, "test_conn", "SELECT 1",
                          user_col="user_id", event_col="event", time_col="ts")
        assert "[ERROR]" in result

    def test_max_steps_respected(self):
        df = pd.DataFrame({
            "user_id": ["u1"] * 10,
            "event": ["A", "B", "C", "D", "E", "A", "B", "C", "D", "E"],
            "ts": [f"2024-01-01 10:0{i}" for i in range(10)],
        })
        result = _with_df(df, user_journey, "test_conn", "SELECT 1",
                          user_col="user_id", event_col="event", time_col="ts", max_steps=3)
        assert "Top 3 시퀀스 패턴" in result

    def test_single_event_per_user(self):
        df = pd.DataFrame({
            "user_id": ["u1", "u2", "u3"],
            "event": ["login", "login", "login"],
            "ts": ["2024-01-01", "2024-01-02", "2024-01-03"],
        })
        result = _with_df(df, user_journey, "test_conn", "SELECT 1",
                          user_col="user_id", event_col="event", time_col="ts")
        # 단일 이벤트는 전환 없음, 에러 없이 처리
        assert "사용자 여정 분석" in result
