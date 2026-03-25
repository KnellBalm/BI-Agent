"""bi_agent_mcp.tools.analytics 단위 테스트."""
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

import bi_agent_mcp.tools.analytics as analytics_module
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
from bi_agent_mcp.tools.db import ConnectionInfo


def _make_conn(conn_id: str) -> ConnectionInfo:
    return ConnectionInfo(
        conn_id=conn_id,
        db_type="postgresql",
        host="localhost",
        port=5432,
        database="testdb",
        user="user",
        password="pass",
    )


# ──────────────────────────────────────────────────────────────
# TestTrendAnalysis
# ──────────────────────────────────────────────────────────────

class TestTrendAnalysis:
    def _patch(self, df):
        conn = _make_conn("c1")
        mock_conn_obj = MagicMock()
        return (
            patch.object(analytics_module, "_connections", {"c1": conn}),
            patch.object(analytics_module, "_get_conn", return_value=mock_conn_obj),
            patch("pandas.read_sql", return_value=df),
        )

    def test_basic_monthly_trend(self):
        df = pd.DataFrame({
            "dt": pd.date_range("2024-01-01", periods=6, freq="MS"),
            "sales": [100.0, 200.0, 150.0, 300.0, 250.0, 400.0],
        })
        p1, p2, p3 = self._patch(df)
        with p1, p2, p3:
            result = trend_analysis("c1", "SELECT * FROM t", "dt", ["sales"], period="month")
        assert "트렌드 분석" in result
        assert "sales" in result
        assert "[ERROR]" not in result

    def test_invalid_time_col(self):
        df = pd.DataFrame({"sales": [100.0, 200.0]})
        p1, p2, p3 = self._patch(df)
        with p1, p2, p3:
            result = trend_analysis("c1", "SELECT * FROM t", "nonexistent", ["sales"])
        assert "[ERROR]" in result

    def test_unknown_conn_id(self):
        with patch.object(analytics_module, "_connections", {}):
            result = trend_analysis("missing", "SELECT * FROM t", "dt", ["sales"])
        assert "[ERROR]" in result


# ──────────────────────────────────────────────────────────────
# TestCorrelationAnalysis
# ──────────────────────────────────────────────────────────────

class TestCorrelationAnalysis:
    def _patch(self, df):
        conn = _make_conn("c1")
        mock_conn_obj = MagicMock()
        return (
            patch.object(analytics_module, "_connections", {"c1": conn}),
            patch.object(analytics_module, "_get_conn", return_value=mock_conn_obj),
            patch("pandas.read_sql", return_value=df),
        )

    def test_basic_correlation(self):
        df = pd.DataFrame({
            "a": [1.0, 2.0, 3.0, 4.0, 5.0],
            "b": [2.0, 4.0, 6.0, 8.0, 10.0],
            "c": [5.0, 4.0, 3.0, 2.0, 1.0],
        })
        p1, p2, p3 = self._patch(df)
        with p1, p2, p3:
            result = correlation_analysis("c1", "SELECT * FROM t")
        assert "상관관계 분석" in result
        assert "[ERROR]" not in result

    def test_strong_correlation_detected(self):
        df = pd.DataFrame({
            "x": [1.0, 2.0, 3.0, 4.0, 5.0],
            "y": [1.0, 2.0, 3.0, 4.0, 5.0],
        })
        p1, p2, p3 = self._patch(df)
        with p1, p2, p3:
            result = correlation_analysis("c1", "SELECT * FROM t")
        assert "강한 상관관계" in result

    def test_unknown_conn_id(self):
        with patch.object(analytics_module, "_connections", {}):
            result = correlation_analysis("missing", "SELECT * FROM t")
        assert "[ERROR]" in result


# ──────────────────────────────────────────────────────────────
# TestDistributionAnalysis
# ──────────────────────────────────────────────────────────────

class TestDistributionAnalysis:
    def _patch(self, df):
        conn = _make_conn("c1")
        mock_conn_obj = MagicMock()
        return (
            patch.object(analytics_module, "_connections", {"c1": conn}),
            patch.object(analytics_module, "_get_conn", return_value=mock_conn_obj),
            patch("pandas.read_sql", return_value=df),
        )

    def test_basic_distribution(self):
        df = pd.DataFrame({
            "amount": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0],
        })
        p1, p2, p3 = self._patch(df)
        with p1, p2, p3:
            result = distribution_analysis("c1", "SELECT * FROM t", "amount", bins=5)
        assert "분포 분석" in result
        assert "amount" in result
        assert "[ERROR]" not in result

    def test_invalid_column(self):
        df = pd.DataFrame({"amount": [10.0, 20.0]})
        p1, p2, p3 = self._patch(df)
        with p1, p2, p3:
            result = distribution_analysis("c1", "SELECT * FROM t", "nonexistent")
        assert "[ERROR]" in result

    def test_unknown_conn_id(self):
        with patch.object(analytics_module, "_connections", {}):
            result = distribution_analysis("missing", "SELECT * FROM t", "amount")
        assert "[ERROR]" in result


# ──────────────────────────────────────────────────────────────
# TestSegmentAnalysis
# ──────────────────────────────────────────────────────────────

class TestSegmentAnalysis:
    def _patch(self, df):
        conn = _make_conn("c1")
        mock_conn_obj = MagicMock()
        return (
            patch.object(analytics_module, "_connections", {"c1": conn}),
            patch.object(analytics_module, "_get_conn", return_value=mock_conn_obj),
            patch("pandas.read_sql", return_value=df),
        )

    def test_basic_segment(self):
        df = pd.DataFrame({
            "region": ["Seoul", "Seoul", "Busan", "Busan", "Daegu"],
            "revenue": [100.0, 200.0, 150.0, 50.0, 300.0],
        })
        p1, p2, p3 = self._patch(df)
        with p1, p2, p3:
            result = segment_analysis("c1", "SELECT * FROM t", "region", "revenue", agg="sum")
        assert "세그먼트 분석" in result
        assert "Seoul" in result
        assert "[ERROR]" not in result

    def test_invalid_group_col(self):
        df = pd.DataFrame({"revenue": [100.0, 200.0]})
        p1, p2, p3 = self._patch(df)
        with p1, p2, p3:
            result = segment_analysis("c1", "SELECT * FROM t", "nonexistent", "revenue")
        assert "[ERROR]" in result

    def test_unknown_conn_id(self):
        with patch.object(analytics_module, "_connections", {}):
            result = segment_analysis("missing", "SELECT * FROM t", "region", "revenue")
        assert "[ERROR]" in result


# ──────────────────────────────────────────────────────────────
# TestFunnelAnalysis
# ──────────────────────────────────────────────────────────────

class TestFunnelAnalysis:
    def test_basic_funnel(self):
        conn = _make_conn("c1")
        mock_conn_obj = MagicMock()
        dfs = [
            pd.DataFrame({"cnt": [1000]}),
            pd.DataFrame({"cnt": [500]}),
            pd.DataFrame({"cnt": [200]}),
        ]
        steps = [
            {"name": "방문", "sql": "SELECT COUNT(*) AS cnt FROM visit"},
            {"name": "회원가입", "sql": "SELECT COUNT(*) AS cnt FROM signup"},
            {"name": "구매", "sql": "SELECT COUNT(*) AS cnt FROM purchase"},
        ]
        with patch.object(analytics_module, "_connections", {"c1": conn}), \
             patch.object(analytics_module, "_get_conn", return_value=mock_conn_obj), \
             patch("pandas.read_sql", side_effect=dfs):
            result = funnel_analysis("c1", steps)
        assert "퍼널 분석" in result
        assert "방문" in result
        assert "50.0%" in result
        assert "[ERROR]" not in result

    def test_empty_steps(self):
        result = funnel_analysis("c1", [])
        assert "[ERROR]" in result


# ──────────────────────────────────────────────────────────────
# TestCohortAnalysis
# ──────────────────────────────────────────────────────────────

class TestCohortAnalysis:
    def test_basic_cohort(self):
        conn = _make_conn("c1")
        mock_conn_obj = MagicMock()
        df = pd.DataFrame({
            "user_id": [1, 1, 2, 2, 3, 3, 4],
            "cohort_date": [
                "2024-01-01", "2024-01-01",
                "2024-01-01", "2024-01-01",
                "2024-02-01", "2024-02-01",
                "2024-02-01",
            ],
            "activity_date": [
                "2024-01-15", "2024-02-10",
                "2024-01-20", "2024-03-05",
                "2024-02-10", "2024-03-15",
                "2024-02-20",
            ],
        })
        with patch.object(analytics_module, "_connections", {"c1": conn}), \
             patch.object(analytics_module, "_get_conn", return_value=mock_conn_obj), \
             patch("pandas.read_sql", return_value=df):
            result = cohort_analysis("c1", "SELECT * FROM t", "user_id", "cohort_date", "activity_date")
        assert "코호트 리텐션 분석" in result
        assert "[ERROR]" not in result

    def test_missing_column(self):
        conn = _make_conn("c1")
        mock_conn_obj = MagicMock()
        df = pd.DataFrame({"user_id": [1, 2], "cohort_date": ["2024-01-01", "2024-01-01"]})
        with patch.object(analytics_module, "_connections", {"c1": conn}), \
             patch.object(analytics_module, "_get_conn", return_value=mock_conn_obj), \
             patch("pandas.read_sql", return_value=df):
            result = cohort_analysis("c1", "SELECT * FROM t", "user_id", "cohort_date", "nonexistent")
        assert "[ERROR]" in result


# ──────────────────────────────────────────────────────────────
# TestPivotTable
# ──────────────────────────────────────────────────────────────

class TestPivotTable:
    def _patch(self, df):
        conn = _make_conn("c1")
        mock_conn_obj = MagicMock()
        return (
            patch.object(analytics_module, "_connections", {"c1": conn}),
            patch.object(analytics_module, "_get_conn", return_value=mock_conn_obj),
            patch("pandas.read_sql", return_value=df),
        )

    def test_basic_pivot(self):
        df = pd.DataFrame({
            "region": ["Seoul", "Seoul", "Busan", "Busan"],
            "product": ["A", "B", "A", "B"],
            "sales": [100.0, 200.0, 150.0, 250.0],
        })
        p1, p2, p3 = self._patch(df)
        with p1, p2, p3:
            result = pivot_table("c1", "SELECT * FROM t", "region", "product", "sales", aggfunc="sum")
        assert "피벗 테이블" in result
        assert "Seoul" in result
        assert "[ERROR]" not in result

    def test_unknown_conn_id(self):
        with patch.object(analytics_module, "_connections", {}):
            result = pivot_table("missing", "SELECT * FROM t", "region", "product", "sales")
        assert "[ERROR]" in result


# ──────────────────────────────────────────────────────────────
# TestTopNAnalysis
# ──────────────────────────────────────────────────────────────

class TestTopNAnalysis:
    def _patch(self, df):
        conn = _make_conn("c1")
        mock_conn_obj = MagicMock()
        return (
            patch.object(analytics_module, "_connections", {"c1": conn}),
            patch.object(analytics_module, "_get_conn", return_value=mock_conn_obj),
            patch("pandas.read_sql", return_value=df),
        )

    def test_basic_top_n(self):
        df = pd.DataFrame({
            "product": ["A", "B", "C", "D", "E"],
            "sales": [500.0, 300.0, 800.0, 100.0, 600.0],
        })
        p1, p2, p3 = self._patch(df)
        with p1, p2, p3:
            result = top_n_analysis("c1", "SELECT * FROM t", "sales", n=3)
        assert "Top-3 분석" in result
        assert "[ERROR]" not in result

    def test_unknown_conn_id(self):
        with patch.object(analytics_module, "_connections", {}):
            result = top_n_analysis("missing", "SELECT * FROM t", "sales", n=5)
        assert "[ERROR]" in result
