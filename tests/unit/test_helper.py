"""tests/unit/test_helper.py — helper.py 순수 함수 단위 테스트."""
import pytest
from bi_agent_mcp.tools.helper import (
    hypothesis_helper,
    analysis_method_recommender,
    query_result_interpreter,
    tableau_viz_guide,
)


# ---------------------------------------------------------------------------
# hypothesis_helper
# ---------------------------------------------------------------------------


class TestHypothesisHelper:
    def test_revenue_decline_returns_framework(self):
        result = hypothesis_helper("revenue_decline")
        assert "매출 하락" in result
        assert "가설 1" in result
        assert "revenue_analysis" in result or "trend_analysis" in result

    def test_churn_increase_returns_framework(self):
        result = hypothesis_helper("churn_increase")
        assert "이탈 증가" in result
        assert "churn_analysis" in result

    def test_conversion_drop_returns_framework(self):
        result = hypothesis_helper("conversion_drop")
        assert "전환율 하락" in result
        assert "conversion_funnel" in result or "funnel_analysis" in result

    def test_user_growth_returns_framework(self):
        result = hypothesis_helper("user_growth")
        assert "사용자 성장" in result
        assert "growth_analysis" in result

    def test_product_performance_returns_framework(self):
        result = hypothesis_helper("product_performance")
        assert "프로덕트 성과" in result
        assert "trend_analysis" in result or "cohort_analysis" in result

    def test_marketing_effectiveness_returns_framework(self):
        result = hypothesis_helper("marketing_effectiveness")
        assert "마케팅 효과성" in result
        assert "revenue_analysis" in result or "segment_analysis" in result

    def test_general_returns_framework(self):
        result = hypothesis_helper("general")
        assert "일반 비즈니스" in result
        assert "가설 1" in result

    def test_unknown_type_falls_back_to_general(self):
        result = hypothesis_helper("unknown_problem_xyz")
        assert "일반 비즈니스" in result

    def test_with_data_context_included_in_output(self):
        result = hypothesis_helper("revenue_decline", data_context="B2B SaaS 구독 서비스")
        assert "B2B SaaS 구독 서비스" in result

    def test_with_available_tables_included_in_output(self):
        result = hypothesis_helper("churn_increase", available_tables="orders, customers")
        assert "orders, customers" in result

    def test_sql_pattern_present(self):
        result = hypothesis_helper("revenue_decline")
        assert "```sql" in result

    def test_interpret_guide_present(self):
        result = hypothesis_helper("churn_increase")
        assert "해석 가이드" in result


# ---------------------------------------------------------------------------
# analysis_method_recommender
# ---------------------------------------------------------------------------


class TestAnalysisMethodRecommender:
    def test_group_comparison_recommends_ttest(self):
        result = analysis_method_recommender("두 그룹 비교 분석")
        assert "ttest_independent" in result or "anova_one_way" in result

    def test_trend_analysis_recommends_tools(self):
        result = analysis_method_recommender("시계열 트렌드 분석")
        assert "trend_analysis" in result

    def test_correlation_recommends_tools(self):
        result = analysis_method_recommender("두 변수 간 상관관계 분석")
        assert "correlation_analysis" in result

    def test_forecast_recommends_tools(self):
        result = analysis_method_recommender("내년 매출 예측")
        assert "linear_trend_forecast" in result or "exponential_smoothing_forecast" in result

    def test_churn_recommends_tools(self):
        result = analysis_method_recommender("이탈 고객 분석")
        assert "churn_analysis" in result

    def test_funnel_recommends_tools(self):
        result = analysis_method_recommender("퍼널 전환율 분석")
        assert "conversion_funnel" in result or "funnel_analysis" in result

    def test_segmentation_recommends_tools(self):
        result = analysis_method_recommender("고객 세분화")
        assert "segment_analysis" in result or "rfm_analysis" in result

    def test_distribution_recommends_tools(self):
        result = analysis_method_recommender("데이터 분포 확인")
        assert "distribution_analysis" in result or "descriptive_stats" in result

    def test_unknown_goal_returns_eda(self):
        result = analysis_method_recommender("알 수 없는 분석 목적 xyz")
        assert "descriptive_stats" in result or "distribution_analysis" in result

    def test_sample_size_small_note(self):
        result = analysis_method_recommender("그룹 비교", sample_size=20)
        assert "소규모" in result or "비모수" in result

    def test_sample_size_large_note(self):
        result = analysis_method_recommender("시계열 트렌드", sample_size=5000)
        assert "대규모" in result or "중심극한정리" in result

    def test_data_types_included(self):
        result = analysis_method_recommender("상관관계 분석", data_types="연속형, 범주형")
        assert "연속형, 범주형" in result


# ---------------------------------------------------------------------------
# query_result_interpreter
# ---------------------------------------------------------------------------


class TestQueryResultInterpreter:
    def test_basic_overview_present(self):
        result = query_result_interpreter(["user_id", "revenue", "created_at"], 100)
        assert "컬럼 수" in result
        assert "행 수" in result

    def test_zero_row_count_warning(self):
        result = query_result_interpreter(["user_id", "amount"], 0)
        assert "없습니다" in result or "주의" in result

    def test_columns_listed_in_output(self):
        cols = ["customer_id", "total_revenue", "churn_date"]
        result = query_result_interpreter(cols, 50)
        for col in cols:
            assert col in result

    def test_date_column_detected(self):
        result = query_result_interpreter(["event_date", "count"], 200)
        assert "날짜" in result or "시간" in result

    def test_numeric_column_detected(self):
        result = query_result_interpreter(["category", "total_revenue"], 30)
        assert "수치형" in result

    def test_revenue_column_suggests_tool(self):
        result = query_result_interpreter(["month", "revenue"], 12)
        assert "revenue_analysis" in result

    def test_churn_column_suggests_tool(self):
        result = query_result_interpreter(["user_id", "churned_at"], 500)
        assert "churn_analysis" in result

    def test_date_column_suggests_cohort(self):
        result = query_result_interpreter(["created_at", "amount"], 300)
        assert "cohort_analysis" in result

    def test_sample_values_included(self):
        result = query_result_interpreter(["id", "value"], 10, sample_values="1, 2, 3")
        assert "1, 2, 3" in result

    def test_question_included_in_output(self):
        result = query_result_interpreter(["id", "revenue"], 100, question="매출 현황은?")
        assert "매출 현황은?" in result

    def test_caution_section_present(self):
        result = query_result_interpreter(["id", "amount"], 50)
        assert "주의사항" in result

    def test_large_row_count_note(self):
        result = query_result_interpreter(["id", "value"], 200000)
        assert "많습니다" in result or "샘플링" in result


# ---------------------------------------------------------------------------
# tableau_viz_guide
# ---------------------------------------------------------------------------


class TestTableauVizGuide:
    def test_trend_recommends_line_chart(self):
        result = tableau_viz_guide("월별 매출 트렌드")
        assert "line" in result
        assert "꺾은선형" in result or "Line" in result

    def test_comparison_recommends_bar_chart(self):
        result = tableau_viz_guide("카테고리별 매출 비교")
        assert "bar" in result
        assert "막대" in result

    def test_scatter_for_correlation(self):
        result = tableau_viz_guide("두 지표 간 상관관계 산점도")
        assert "scatter" in result
        assert "산점도" in result or "Scatter" in result

    def test_distribution_histogram(self):
        result = tableau_viz_guide("주문 금액 분포 히스토그램")
        assert "히스토그램" in result or "Histogram" in result

    def test_map_for_region(self):
        result = tableau_viz_guide("지역별 매출 지도")
        assert "map" in result
        assert "지도" in result or "Map" in result

    def test_generate_twbx_reminder_present(self):
        result = tableau_viz_guide("월별 트렌드")
        assert "generate_twbx" in result

    def test_basic_detail_level_has_steps(self):
        result = tableau_viz_guide("매출 비교", detail_level="basic")
        assert "핵심 단계" in result or "기본" in result

    def test_advanced_detail_level_includes_lod(self):
        result = tableau_viz_guide("월별 트렌드", detail_level="advanced")
        assert "LOD" in result or "FIXED" in result or "고급" in result

    def test_data_columns_included_in_output(self):
        result = tableau_viz_guide("매출 비교", data_columns=["category", "revenue"])
        assert "category" in result
        assert "revenue" in result

    def test_unknown_goal_returns_default(self):
        result = tableau_viz_guide("알 수 없는 시각화 목표 xyz")
        assert "generate_twbx" in result
        assert "bar" in result or "막대" in result

    def test_chart_type_value_format(self):
        """generate_twbx chart_type 값이 결과에 명시되어야 합니다."""
        result = tableau_viz_guide("트렌드 분석")
        assert 'chart_type' in result or '"line"' in result or "line" in result
