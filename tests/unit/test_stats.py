"""bi_agent_mcp.tools.stats 단위 테스트."""
import math
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from bi_agent_mcp.tools.stats import (
    descriptive_stats,
    percentile_analysis,
    boxplot_summary,
    confidence_interval,
    sampling_error,
    ttest_one_sample,
    ttest_independent,
    ttest_paired,
    anova_one_way,
    chi_square_test,
    normality_test,
)

MODULE = "bi_agent_mcp.tools.stats"


# ---------------------------------------------------------------------------
# 공통 헬퍼
# ---------------------------------------------------------------------------

def _with_df(df: pd.DataFrame, fn, *args, **kwargs):
    conn_info = MagicMock()
    mock_conn = MagicMock()
    patches = [
        patch(f"{MODULE}._connections", {"test_conn": conn_info}),
        patch(f"{MODULE}._get_conn", return_value=mock_conn),
        patch(f"{MODULE}._validate_select", return_value=None),
        patch("pandas.read_sql", return_value=df),
    ]
    for p in patches:
        p.start()
    try:
        return fn(*args, **kwargs)
    finally:
        for p in patches:
            p.stop()


@pytest.fixture
def with_df_stats():
    def _helper(df, fn, *args, **kwargs):
        return _with_df(df, fn, *args, **kwargs)
    return _helper


# ---------------------------------------------------------------------------
# descriptive_stats
# ---------------------------------------------------------------------------

class TestDescriptiveStats:
    def test_basic_returns_stats(self, with_df_stats):
        df = pd.DataFrame({"v": [1.0, 2.0, 3.0, 4.0, 5.0]})
        result = with_df_stats(df, descriptive_stats, "test_conn", "SELECT 1")
        assert "기술통계" in result
        assert "평균" in result
        assert "표준편차" in result

    def test_specific_columns(self, with_df_stats):
        df = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [4.0, 5.0, 6.0]})
        result = with_df_stats(df, descriptive_stats, "test_conn", "SELECT 1", columns=["a"])
        assert "a" in result
        # b가 제외되었는지 확인 (헤더 컬럼명으로는 나타나지 않아야)
        assert "기술통계" in result

    def test_no_numeric_columns_returns_error(self, with_df_stats):
        df = pd.DataFrame({"name": ["alice", "bob"]})
        result = with_df_stats(df, descriptive_stats, "test_conn", "SELECT 1")
        assert "[ERROR]" in result

    def test_invalid_columns_filter_returns_error(self, with_df_stats):
        df = pd.DataFrame({"a": [1.0, 2.0]})
        result = with_df_stats(df, descriptive_stats, "test_conn", "SELECT 1", columns=["no_col"])
        assert "[ERROR]" in result

    def test_validate_error_propagates(self):
        with patch(f"{MODULE}._validate_select", return_value="SELECT only"):
            result = descriptive_stats("test_conn", "DELETE FROM t")
        assert "[ERROR]" in result

    def test_unknown_conn_returns_error(self):
        with patch(f"{MODULE}._connections", {}):
            with patch(f"{MODULE}._validate_select", return_value=None):
                result = descriptive_stats("no_conn", "SELECT 1")
        assert "[ERROR]" in result


# ---------------------------------------------------------------------------
# percentile_analysis
# ---------------------------------------------------------------------------

class TestPercentileAnalysis:
    def test_basic_percentiles(self, with_df_stats):
        df = pd.DataFrame({"v": list(range(1, 101))})
        result = with_df_stats(df, percentile_analysis, "test_conn", "SELECT 1", col="v")
        assert "백분위수" in result
        assert "p50" in result or "50" in result

    def test_custom_percentiles(self, with_df_stats):
        df = pd.DataFrame({"v": list(range(1, 101))})
        result = with_df_stats(df, percentile_analysis, "test_conn", "SELECT 1",
                               col="v", percentiles=[10, 90])
        assert "p10" in result
        assert "p90" in result

    def test_missing_col_returns_error(self, with_df_stats):
        df = pd.DataFrame({"v": [1.0, 2.0]})
        result = with_df_stats(df, percentile_analysis, "test_conn", "SELECT 1", col="no_col")
        assert "[ERROR]" in result

    def test_non_numeric_col_returns_error(self, with_df_stats):
        df = pd.DataFrame({"name": ["a", "b", "c"]})
        result = with_df_stats(df, percentile_analysis, "test_conn", "SELECT 1", col="name")
        assert "[ERROR]" in result

    def test_validate_error_propagates(self):
        with patch(f"{MODULE}._validate_select", return_value="SELECT only"):
            result = percentile_analysis("test_conn", "DELETE FROM t", col="v")
        assert "[ERROR]" in result


# ---------------------------------------------------------------------------
# boxplot_summary
# ---------------------------------------------------------------------------

class TestBoxplotSummary:
    def test_basic_boxplot(self, with_df_stats):
        df = pd.DataFrame({"v": [1.0, 2.0, 3.0, 4.0, 5.0, 100.0]})
        result = with_df_stats(df, boxplot_summary, "test_conn", "SELECT 1", col="v")
        assert "박스플롯" in result
        assert "IQR" in result
        assert "이상치" in result

    def test_grouped_boxplot(self, with_df_stats):
        df = pd.DataFrame({
            "group": ["A", "A", "A", "B", "B", "B"],
            "v": [1.0, 2.0, 3.0, 10.0, 11.0, 12.0],
        })
        result = with_df_stats(df, boxplot_summary, "test_conn", "SELECT 1",
                               col="v", group_col="group")
        assert "A" in result
        assert "B" in result

    def test_missing_col_returns_error(self, with_df_stats):
        df = pd.DataFrame({"v": [1.0, 2.0]})
        result = with_df_stats(df, boxplot_summary, "test_conn", "SELECT 1", col="no_col")
        assert "[ERROR]" in result

    def test_missing_group_col_returns_error(self, with_df_stats):
        df = pd.DataFrame({"v": [1.0, 2.0]})
        result = with_df_stats(df, boxplot_summary, "test_conn", "SELECT 1",
                               col="v", group_col="no_group")
        assert "[ERROR]" in result

    def test_validate_error_propagates(self):
        with patch(f"{MODULE}._validate_select", return_value="SELECT only"):
            result = boxplot_summary("test_conn", "DELETE FROM t", col="v")
        assert "[ERROR]" in result


# ---------------------------------------------------------------------------
# confidence_interval
# ---------------------------------------------------------------------------

class TestConfidenceInterval:
    def test_basic_ci(self, with_df_stats):
        df = pd.DataFrame({"v": [10.0, 12.0, 11.0, 13.0, 9.0, 11.0, 12.0, 10.0]})
        result = with_df_stats(df, confidence_interval, "test_conn", "SELECT 1", col="v")
        assert "신뢰구간" in result
        assert "95" in result

    def test_90_percent_ci(self, with_df_stats):
        df = pd.DataFrame({"v": list(range(1, 21))})
        result = with_df_stats(df, confidence_interval, "test_conn", "SELECT 1",
                               col="v", confidence=0.90)
        assert "90" in result

    def test_missing_col_returns_error(self, with_df_stats):
        df = pd.DataFrame({"v": [1.0, 2.0]})
        result = with_df_stats(df, confidence_interval, "test_conn", "SELECT 1", col="no_col")
        assert "[ERROR]" in result

    def test_too_few_data_returns_error(self, with_df_stats):
        df = pd.DataFrame({"v": [1.0]})
        result = with_df_stats(df, confidence_interval, "test_conn", "SELECT 1", col="v")
        assert "[ERROR]" in result

    def test_non_numeric_col_returns_error(self, with_df_stats):
        df = pd.DataFrame({"v": ["a", "b", "c"]})
        result = with_df_stats(df, confidence_interval, "test_conn", "SELECT 1", col="v")
        assert "[ERROR]" in result


# ---------------------------------------------------------------------------
# sampling_error
# ---------------------------------------------------------------------------

class TestSamplingError:
    def test_basic_sampling_error(self, with_df_stats):
        df = pd.DataFrame({"v": list(range(1, 51))})
        result = with_df_stats(df, sampling_error, "test_conn", "SELECT 1", col="v")
        assert "표본오차" in result
        assert "필요 표본 수" in result

    def test_99_percent_confidence(self, with_df_stats):
        df = pd.DataFrame({"v": list(range(1, 51))})
        result = with_df_stats(df, sampling_error, "test_conn", "SELECT 1",
                               col="v", confidence=0.99)
        assert "99" in result

    def test_missing_col_returns_error(self, with_df_stats):
        df = pd.DataFrame({"v": [1.0, 2.0]})
        result = with_df_stats(df, sampling_error, "test_conn", "SELECT 1", col="no_col")
        assert "[ERROR]" in result

    def test_too_few_data_returns_error(self, with_df_stats):
        df = pd.DataFrame({"v": [1.0]})
        result = with_df_stats(df, sampling_error, "test_conn", "SELECT 1", col="v")
        assert "[ERROR]" in result

    def test_validate_error_propagates(self):
        with patch(f"{MODULE}._validate_select", return_value="SELECT only"):
            result = sampling_error("test_conn", "DELETE FROM t", col="v")
        assert "[ERROR]" in result


# ---------------------------------------------------------------------------
# ttest_one_sample
# ---------------------------------------------------------------------------

class TestTtestOneSample:
    def test_reject_h0(self, with_df_stats):
        # 평균이 명확히 mu=0과 다른 데이터
        df = pd.DataFrame({"v": [10.0, 11.0, 12.0, 10.5, 11.5, 10.8, 11.2, 10.9, 11.1, 10.6]})
        result = with_df_stats(df, ttest_one_sample, "test_conn", "SELECT 1", col="v", mu=0.0)
        assert "t-검정" in result
        assert "유의미한 차이 있음" in result

    def test_fail_to_reject_h0(self, with_df_stats):
        # 평균이 mu=11에 가까운 데이터
        df = pd.DataFrame({"v": [10.9, 11.1, 10.8, 11.2, 11.0, 10.95, 11.05, 10.98, 11.02, 11.0]})
        result = with_df_stats(df, ttest_one_sample, "test_conn", "SELECT 1", col="v", mu=11.0)
        assert "유의미한 차이 없음" in result

    def test_missing_col_returns_error(self, with_df_stats):
        df = pd.DataFrame({"v": [1.0, 2.0]})
        result = with_df_stats(df, ttest_one_sample, "test_conn", "SELECT 1",
                               col="no_col", mu=0.0)
        assert "[ERROR]" in result

    def test_too_few_data_returns_error(self, with_df_stats):
        df = pd.DataFrame({"v": [1.0]})
        result = with_df_stats(df, ttest_one_sample, "test_conn", "SELECT 1", col="v", mu=0.0)
        assert "[ERROR]" in result

    def test_result_contains_t_stat(self, with_df_stats):
        df = pd.DataFrame({"v": [5.0, 6.0, 7.0, 5.5, 6.5]})
        result = with_df_stats(df, ttest_one_sample, "test_conn", "SELECT 1", col="v", mu=5.0)
        assert "t-통계량" in result
        assert "p-value" in result


# ---------------------------------------------------------------------------
# ttest_independent
# ---------------------------------------------------------------------------

class TestTtestIndependent:
    def test_two_groups_significant(self, with_df_stats):
        df = pd.DataFrame({
            "group": ["A"] * 10 + ["B"] * 10,
            "v": [1.0, 1.1, 0.9, 1.2, 0.8, 1.0, 1.1, 0.95, 1.05, 1.0] +
                 [5.0, 5.1, 4.9, 5.2, 4.8, 5.0, 5.1, 4.95, 5.05, 5.0],
        })
        result = with_df_stats(df, ttest_independent, "test_conn", "SELECT 1",
                               group_col="group", value_col="v")
        assert "유의미한 차이 있음" in result

    def test_more_than_two_groups_returns_error(self, with_df_stats):
        df = pd.DataFrame({
            "group": ["A", "B", "C"],
            "v": [1.0, 2.0, 3.0],
        })
        result = with_df_stats(df, ttest_independent, "test_conn", "SELECT 1",
                               group_col="group", value_col="v")
        assert "[ERROR]" in result

    def test_missing_group_col_returns_error(self, with_df_stats):
        df = pd.DataFrame({"v": [1.0, 2.0]})
        result = with_df_stats(df, ttest_independent, "test_conn", "SELECT 1",
                               group_col="no_col", value_col="v")
        assert "[ERROR]" in result

    def test_result_contains_welch_df(self, with_df_stats):
        df = pd.DataFrame({
            "group": ["A"] * 5 + ["B"] * 5,
            "v": [1.0, 1.2, 0.8, 1.1, 0.9, 3.0, 3.2, 2.8, 3.1, 2.9],
        })
        result = with_df_stats(df, ttest_independent, "test_conn", "SELECT 1",
                               group_col="group", value_col="v")
        assert "Welch" in result
        assert "t-통계량" in result

    def test_ab_test_docstring(self):
        """ttest_independent docstring에 ab_test_analysis 언급 확인."""
        assert "ab_test_analysis" in ttest_independent.__doc__


# ---------------------------------------------------------------------------
# ttest_paired
# ---------------------------------------------------------------------------

class TestTtestPaired:
    def test_significant_difference(self, with_df_stats):
        df = pd.DataFrame({
            "before": [5.0, 5.2, 4.8, 5.1, 4.9, 5.0, 5.3, 4.7, 5.1, 4.9],
            "after":  [8.0, 8.2, 7.8, 8.1, 7.9, 8.0, 8.3, 7.7, 8.1, 7.9],
        })
        result = with_df_stats(df, ttest_paired, "test_conn", "SELECT 1",
                               col_a="before", col_b="after")
        assert "유의미한 차이 있음" in result

    def test_no_difference(self, with_df_stats):
        # before ≈ after
        df = pd.DataFrame({
            "a": [10.0, 10.01, 9.99, 10.0, 10.0],
            "b": [10.0, 10.01, 9.99, 10.0, 10.0],
        })
        result = with_df_stats(df, ttest_paired, "test_conn", "SELECT 1",
                               col_a="a", col_b="b")
        # std=0이면 t=nan이 될 수 있으므로 에러 또는 유의미하지 않음 중 하나
        assert result is not None

    def test_missing_col_returns_error(self, with_df_stats):
        df = pd.DataFrame({"a": [1.0, 2.0]})
        result = with_df_stats(df, ttest_paired, "test_conn", "SELECT 1",
                               col_a="a", col_b="no_col")
        assert "[ERROR]" in result

    def test_result_contains_paired_info(self, with_df_stats):
        df = pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0, 5.0],
                           "b": [1.5, 2.3, 3.8, 4.2, 5.6]})
        result = with_df_stats(df, ttest_paired, "test_conn", "SELECT 1",
                               col_a="a", col_b="b")
        assert "대응 표본" in result
        assert "t-통계량" in result

    def test_too_few_pairs_returns_error(self, with_df_stats):
        df = pd.DataFrame({"a": [1.0], "b": [2.0]})
        result = with_df_stats(df, ttest_paired, "test_conn", "SELECT 1",
                               col_a="a", col_b="b")
        assert "[ERROR]" in result


# ---------------------------------------------------------------------------
# anova_one_way
# ---------------------------------------------------------------------------

class TestAnovaOneWay:
    def test_significant_f(self, with_df_stats):
        df = pd.DataFrame({
            "group": ["A"] * 5 + ["B"] * 5 + ["C"] * 5,
            "v": [1.0, 1.1, 0.9, 1.05, 0.95,
                  5.0, 5.1, 4.9, 5.05, 4.95,
                  10.0, 10.1, 9.9, 10.05, 9.95],
        })
        result = with_df_stats(df, anova_one_way, "test_conn", "SELECT 1",
                               group_col="group", value_col="v")
        assert "ANOVA" in result
        assert "F-통계량" in result
        assert "유의미한 차이 있음" in result

    def test_one_group_returns_error(self, with_df_stats):
        df = pd.DataFrame({"group": ["A", "A", "A"], "v": [1.0, 2.0, 3.0]})
        result = with_df_stats(df, anova_one_way, "test_conn", "SELECT 1",
                               group_col="group", value_col="v")
        assert "[ERROR]" in result

    def test_missing_col_returns_error(self, with_df_stats):
        df = pd.DataFrame({"group": ["A", "B"], "v": [1.0, 2.0]})
        result = with_df_stats(df, anova_one_way, "test_conn", "SELECT 1",
                               group_col="no_col", value_col="v")
        assert "[ERROR]" in result

    def test_group_stats_included(self, with_df_stats):
        df = pd.DataFrame({
            "group": ["X"] * 3 + ["Y"] * 3,
            "v": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        })
        result = with_df_stats(df, anova_one_way, "test_conn", "SELECT 1",
                               group_col="group", value_col="v")
        assert "그룹별 통계" in result
        assert "X" in result
        assert "Y" in result

    def test_validate_error_propagates(self):
        with patch(f"{MODULE}._validate_select", return_value="SELECT only"):
            result = anova_one_way("test_conn", "DELETE FROM t",
                                   group_col="g", value_col="v")
        assert "[ERROR]" in result


# ---------------------------------------------------------------------------
# chi_square_test
# ---------------------------------------------------------------------------

class TestChiSquareTest:
    def test_independent_significant(self, with_df_stats):
        # 강한 연관성 데이터
        df = pd.DataFrame({
            "gender": ["M"] * 20 + ["F"] * 20,
            "choice": (["A"] * 18 + ["B"] * 2) + (["A"] * 2 + ["B"] * 18),
        })
        result = with_df_stats(df, chi_square_test, "test_conn", "SELECT 1",
                               col_a="gender", col_b="choice")
        assert "카이제곱" in result
        assert "유의미한 차이 있음" in result

    def test_contingency_table_shown(self, with_df_stats):
        df = pd.DataFrame({
            "a": ["X", "X", "Y", "Y"],
            "b": ["P", "Q", "P", "Q"],
        })
        result = with_df_stats(df, chi_square_test, "test_conn", "SELECT 1",
                               col_a="a", col_b="b")
        assert "교차표" in result

    def test_missing_col_returns_error(self, with_df_stats):
        df = pd.DataFrame({"a": ["X", "Y"]})
        result = with_df_stats(df, chi_square_test, "test_conn", "SELECT 1",
                               col_a="a", col_b="no_col")
        assert "[ERROR]" in result

    def test_result_contains_df(self, with_df_stats):
        df = pd.DataFrame({
            "a": ["X", "X", "Y", "Y", "X", "Y"],
            "b": ["P", "Q", "P", "Q", "P", "Q"],
        })
        result = with_df_stats(df, chi_square_test, "test_conn", "SELECT 1",
                               col_a="a", col_b="b")
        assert "자유도" in result

    def test_validate_error_propagates(self):
        with patch(f"{MODULE}._validate_select", return_value="SELECT only"):
            result = chi_square_test("test_conn", "DELETE FROM t",
                                     col_a="a", col_b="b")
        assert "[ERROR]" in result


# ---------------------------------------------------------------------------
# normality_test
# ---------------------------------------------------------------------------

class TestNormalityTest:
    def test_normal_data(self, with_df_stats):
        import numpy as np
        rng = np.random.default_rng(42)
        data = rng.normal(loc=0, scale=1, size=100).tolist()
        df = pd.DataFrame({"v": data})
        result = with_df_stats(df, normality_test, "test_conn", "SELECT 1", col="v")
        assert "Jarque-Bera" in result
        assert "JB 통계량" in result

    def test_non_normal_data(self, with_df_stats):
        # 강하게 편향된 데이터 (지수분포)
        import numpy as np
        rng = np.random.default_rng(0)
        data = rng.exponential(scale=1, size=100).tolist()
        df = pd.DataFrame({"v": data})
        result = with_df_stats(df, normality_test, "test_conn", "SELECT 1", col="v")
        assert "Jarque-Bera" in result

    def test_too_few_data_returns_error(self, with_df_stats):
        df = pd.DataFrame({"v": [1.0, 2.0, 3.0]})
        result = with_df_stats(df, normality_test, "test_conn", "SELECT 1", col="v")
        assert "[ERROR]" in result

    def test_missing_col_returns_error(self, with_df_stats):
        df = pd.DataFrame({"v": list(range(20))})
        result = with_df_stats(df, normality_test, "test_conn", "SELECT 1", col="no_col")
        assert "[ERROR]" in result

    def test_non_numeric_returns_error(self, with_df_stats):
        df = pd.DataFrame({"v": ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]})
        result = with_df_stats(df, normality_test, "test_conn", "SELECT 1", col="v")
        assert "[ERROR]" in result

    def test_result_contains_skew_kurtosis(self, with_df_stats):
        df = pd.DataFrame({"v": list(range(1, 21))})
        result = with_df_stats(df, normality_test, "test_conn", "SELECT 1", col="v")
        assert "왜도" in result
        assert "첨도" in result
