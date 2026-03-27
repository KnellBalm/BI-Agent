"""bi_agent_mcp.tools.ab_test 단위 테스트 — ab_sample_size, ab_multivariate, ab_segment_breakdown, ab_time_decay."""
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from bi_agent_mcp.tools.ab_test import (
    ab_sample_size,
    ab_multivariate,
    ab_segment_breakdown,
    ab_time_decay,
)


# ---------------------------------------------------------------------------
# ab_sample_size
# ---------------------------------------------------------------------------

class TestAbSampleSize:
    def test_ab_sample_size_proportion(self):
        result = ab_sample_size(baseline_rate=0.05, mde=0.20)
        assert "그룹당 필요 샘플" in result
        assert "A/B 테스트 샘플 크기 계산" in result
        assert "5.00%" in result

    def test_ab_sample_size_mean(self):
        result = ab_sample_size(baseline_rate=100.0, mde=0.10, test_type="mean")
        assert "그룹당 필요 샘플" in result
        assert "A/B 테스트 샘플 크기 계산" in result
        assert "평균" in result

    def test_ab_sample_size_invalid_baseline(self):
        result = ab_sample_size(baseline_rate=-0.1, mde=0.20)
        assert "[ERROR]" in result

    def test_ab_sample_size_invalid_mde_zero(self):
        result = ab_sample_size(baseline_rate=0.05, mde=0.0)
        assert "[ERROR]" in result

    def test_ab_sample_size_invalid_mde_over_one(self):
        result = ab_sample_size(baseline_rate=0.05, mde=1.5)
        assert "[ERROR]" in result

    def test_ab_sample_size_invalid_test_type(self):
        result = ab_sample_size(baseline_rate=0.05, mde=0.20, test_type="unknown")
        assert "[ERROR]" in result

    def test_ab_sample_size_total_is_double_group(self):
        result = ab_sample_size(baseline_rate=0.10, mde=0.15)
        lines = result.splitlines()
        group_line = next(l for l in lines if "그룹당 필요 샘플 수" in l)
        total_line = next(l for l in lines if "전체 필요 샘플 수" in l)
        # 그룹당 수 추출
        group_n = int(group_line.split(":")[1].strip().replace("명", "").replace(",", ""))
        total_n = int(total_line.split(":")[1].strip().split("명")[0].replace(",", ""))
        assert total_n == group_n * 2


# ---------------------------------------------------------------------------
# ab_multivariate
# ---------------------------------------------------------------------------

class TestAbMultivariate:
    def _make_3group_df(self):
        return pd.DataFrame({
            "variant": ["A"] * 10 + ["B"] * 10 + ["C"] * 10,
            "metric": (
                [10.0, 11.0, 12.0, 10.5, 11.5, 10.0, 11.0, 12.0, 10.5, 11.5] +
                [15.0, 16.0, 17.0, 15.5, 16.5, 15.0, 16.0, 17.0, 15.5, 16.5] +
                [20.0, 21.0, 22.0, 20.5, 21.5, 20.0, 21.0, 22.0, 20.5, 21.5]
            ),
        })

    def test_ab_multivariate_3groups(self, with_df_ab_test):
        df = self._make_3group_df()
        result = with_df_ab_test(
            df, ab_multivariate,
            "test_conn", "SELECT 1",
            group_col="variant", metric_col="metric",
        )
        assert "다변형 A/B 테스트 분석" in result
        assert "ANOVA 결과" in result
        assert "쌍별 비교" in result
        assert "A vs B" in result

    def test_ab_multivariate_too_few_groups(self, with_df_ab_test):
        df = pd.DataFrame({
            "variant": ["A"] * 5 + ["B"] * 5,
            "metric": [1.0] * 10,
        })
        result = with_df_ab_test(
            df, ab_multivariate,
            "test_conn", "SELECT 1",
            group_col="variant", metric_col="metric",
        )
        assert "[ERROR]" in result
        assert "2그룹" in result

    def test_ab_multivariate_missing_group_col(self, with_df_ab_test):
        df = self._make_3group_df()
        result = with_df_ab_test(
            df, ab_multivariate,
            "test_conn", "SELECT 1",
            group_col="no_such_col", metric_col="metric",
        )
        assert "[ERROR]" in result

    def test_ab_multivariate_unknown_conn(self):
        result = ab_multivariate(
            "unknown_conn", "SELECT 1",
            group_col="variant", metric_col="metric",
        )
        assert "[ERROR]" in result

    def test_ab_multivariate_bonferroni_alpha_shown(self, with_df_ab_test):
        df = self._make_3group_df()
        result = with_df_ab_test(
            df, ab_multivariate,
            "test_conn", "SELECT 1",
            group_col="variant", metric_col="metric", alpha=0.05,
        )
        # 3그룹 → 3쌍 → α_adj = 0.05/3 ≈ 0.0167
        assert "0.0167" in result


# ---------------------------------------------------------------------------
# ab_segment_breakdown
# ---------------------------------------------------------------------------

class TestAbSegmentBreakdown:
    def _make_segment_df(self):
        """mobile 세그먼트는 유의미한 차이, desktop은 미미한 차이."""
        return pd.DataFrame({
            "group": (["A"] * 20 + ["B"] * 20),
            "value": (
                [0.05] * 10 + [0.05] * 10 +   # A: mobile, desktop
                [0.09] * 10 + [0.051] * 10     # B: mobile(큰차이), desktop(미미)
            ),
            "device": ["mobile"] * 10 + ["desktop"] * 10 + ["mobile"] * 10 + ["desktop"] * 10,
        })

    def test_ab_segment_breakdown_basic(self, with_df_ab_test):
        df = self._make_segment_df()
        result = with_df_ab_test(
            df, ab_segment_breakdown,
            "test_conn", "SELECT 1",
            group_col="group", metric_col="value", segment_col="device",
        )
        assert "## 세그먼트별 A/B 효과 분석" in result
        assert "세그먼트별 결과" in result
        assert "mobile" in result
        assert "desktop" in result

    def test_ab_segment_breakdown_invalid_groups(self, with_df_ab_test):
        df = pd.DataFrame({
            "group": ["A"] * 5 + ["B"] * 5 + ["C"] * 5,
            "value": [1.0] * 15,
            "device": ["mobile"] * 15,
        })
        result = with_df_ab_test(
            df, ab_segment_breakdown,
            "test_conn", "SELECT 1",
            group_col="group", metric_col="value", segment_col="device",
        )
        assert "[ERROR]" in result

    def test_ab_segment_breakdown_missing_col(self, with_df_ab_test):
        df = self._make_segment_df()
        result = with_df_ab_test(
            df, ab_segment_breakdown,
            "test_conn", "SELECT 1",
            group_col="group", metric_col="value", segment_col="no_such_col",
        )
        assert "[ERROR]" in result

    def test_ab_segment_breakdown_unknown_conn(self):
        result = ab_segment_breakdown(
            "unknown_conn", "SELECT 1",
            group_col="group", metric_col="value", segment_col="device",
        )
        assert "[ERROR]" in result

    def test_ab_segment_breakdown_overall_result(self, with_df_ab_test):
        df = self._make_segment_df()
        result = with_df_ab_test(
            df, ab_segment_breakdown,
            "test_conn", "SELECT 1",
            group_col="group", metric_col="value", segment_col="device",
        )
        assert "전체 결과" in result
        assert "Lift" in result


# ---------------------------------------------------------------------------
# ab_time_decay
# ---------------------------------------------------------------------------

class TestAbTimeDecay:
    def _make_time_df(self, novelty=False):
        """3개 주차 데이터. novelty=True면 초반 효과가 매우 크고 후반은 작음."""
        rows = []
        import datetime
        base = datetime.date(2024, 1, 1)
        for week in range(3):
            for i in range(20):
                date = base + datetime.timedelta(days=week * 7 + i % 7)
                group = "A" if i < 10 else "B"
                if novelty:
                    # 1주차: B가 50% 높음, 3주차: B가 거의 같음
                    if week == 0:
                        value = 0.10 if group == "B" else 0.05  # +100%
                    elif week == 1:
                        value = 0.07 if group == "B" else 0.05  # +40%
                    else:
                        value = 0.051 if group == "B" else 0.05  # +2%
                else:
                    value = 0.06 if group == "B" else 0.05
                rows.append({"group": group, "value": value, "date": str(date)})
        return pd.DataFrame(rows)

    def test_ab_time_decay_basic(self, with_df_ab_test):
        df = self._make_time_df()
        result = with_df_ab_test(
            df, ab_time_decay,
            "test_conn", "SELECT 1",
            group_col="group", metric_col="value", date_col="date",
        )
        assert "## A/B 효과 시간 변화 분석" in result
        assert "기간별 효과" in result

    def test_ab_time_decay_novelty(self, with_df_ab_test):
        df = self._make_time_df(novelty=True)
        result = with_df_ab_test(
            df, ab_time_decay,
            "test_conn", "SELECT 1",
            group_col="group", metric_col="value", date_col="date",
        )
        assert "Novelty Effect" in result

    def test_ab_time_decay_missing_col(self, with_df_ab_test):
        df = self._make_time_df()
        result = with_df_ab_test(
            df, ab_time_decay,
            "test_conn", "SELECT 1",
            group_col="group", metric_col="value", date_col="no_date_col",
        )
        assert "[ERROR]" in result

    def test_ab_time_decay_unknown_conn(self):
        result = ab_time_decay(
            "unknown_conn", "SELECT 1",
            group_col="group", metric_col="value", date_col="date",
        )
        assert "[ERROR]" in result

    def test_ab_time_decay_window_label(self, with_df_ab_test):
        df = self._make_time_df()
        result = with_df_ab_test(
            df, ab_time_decay,
            "test_conn", "SELECT 1",
            group_col="group", metric_col="value", date_col="date",
            window_days=7,
        )
        assert "주차" in result
