"""bi-agent MCP 서버 — FastMCP 인스턴스, tool 등록, 서버 실행."""
from mcp.server.fastmcp import FastMCP

from bi_agent_mcp.tools.db import (
    connect_db,
    list_connections,
    get_schema,
    run_query,
    profile_table,
    clear_cache,
)

mcp = FastMCP("bi-agent")

# v0 file tools — CSV/Excel 파일 데이터 소스
from bi_agent_mcp.tools.files import connect_file, list_files, query_file, get_file_schema

mcp.tool()(connect_file)
mcp.tool()(list_files)
mcp.tool()(query_file)
mcp.tool()(get_file_schema)

# v0 tools — DB 연결 및 쿼리
mcp.tool()(connect_db)
mcp.tool()(list_connections)
mcp.tool()(get_schema)
mcp.tool()(run_query)
mcp.tool()(profile_table)
mcp.tool()(clear_cache)

# v1 tools (External Data Sources)
from bi_agent_mcp.tools.ga4 import connect_ga4, get_ga4_report
from bi_agent_mcp.tools.amplitude import connect_amplitude, get_amplitude_events

mcp.tool()(connect_ga4)
mcp.tool()(get_ga4_report)
mcp.tool()(connect_amplitude)
mcp.tool()(get_amplitude_events)

# v1-v2 tools (Analysis & Reporting)
from bi_agent_mcp.tools.analysis import (
    suggest_analysis,
    generate_report,
    save_query,
    list_saved_queries,
    load_domain_context,
    list_query_history,
    search_saved_queries,
    run_saved_query,
    delete_saved_query,
)

mcp.tool()(suggest_analysis)
mcp.tool()(generate_report)
mcp.tool()(save_query)
mcp.tool()(list_saved_queries)
mcp.tool()(load_domain_context)
mcp.tool()(list_query_history)
mcp.tool()(search_saved_queries)
mcp.tool()(run_saved_query)
mcp.tool()(delete_saved_query)

# v2 tools (Output Generation)
from bi_agent_mcp.tools.tableau import generate_twbx

mcp.tool()(generate_twbx)

# dashboard tools
from bi_agent_mcp.tools.dashboard import generate_dashboard, chart_from_file

mcp.tool()(generate_dashboard)
mcp.tool()(chart_from_file)

# validation tools — 데이터 품질 검증
from bi_agent_mcp.tools.validation import validate_data, validate_query_result

mcp.tool()(validate_data)
mcp.tool()(validate_query_result)

# cross-source tools — 멀티 소스 조인 쿼리
from bi_agent_mcp.tools.cross_source import cross_query

mcp.tool()(cross_query)

# setup tools — agent 대화 기반 초기 설정
from bi_agent_mcp.tools.setup import (
    check_setup_status,
    configure_datasource,
    test_datasource,
)

mcp.tool()(check_setup_status)
mcp.tool()(configure_datasource)
mcp.tool()(test_datasource)

# context tools — 질문 기반 컨텍스트 및 테이블 관계
from bi_agent_mcp.tools.context import get_context_for_question, get_table_relationships

mcp.tool()(get_context_for_question)
mcp.tool()(get_table_relationships)

# alerts tools — SQL 기반 알림 등록/평가/관리
from bi_agent_mcp.tools.alerts import create_alert, check_alerts, list_alerts, delete_alert

mcp.tool()(create_alert)
mcp.tool()(check_alerts)
mcp.tool()(list_alerts)
mcp.tool()(delete_alert)

# compare tools — 두 쿼리 결과 비교
from bi_agent_mcp.tools.compare import compare_queries

mcp.tool()(compare_queries)

# text-to-sql tools — 자연어 → SQL 자동 생성
from bi_agent_mcp.tools.text_to_sql import generate_sql

mcp.tool()(generate_sql)

# analytics tools — BI 심층 분석
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

mcp.tool()(trend_analysis)
mcp.tool()(correlation_analysis)
mcp.tool()(distribution_analysis)
mcp.tool()(segment_analysis)
mcp.tool()(funnel_analysis)
mcp.tool()(cohort_analysis)
mcp.tool()(pivot_table)
mcp.tool()(top_n_analysis)

# orchestration tools — 분석 오케스트레이션 (플랜 기반 분석 워크플로우)
from bi_agent_mcp.tools.orchestration import (
    create_analysis_plan,
    get_analysis_plan,
    update_analysis_step,
    add_analysis_step,
    synthesize_findings,
    list_analysis_plans,
    complete_analysis_plan,
    delete_analysis_plan,
)

mcp.tool()(create_analysis_plan)
mcp.tool()(get_analysis_plan)
mcp.tool()(update_analysis_step)
mcp.tool()(add_analysis_step)
mcp.tool()(synthesize_findings)
mcp.tool()(list_analysis_plans)
mcp.tool()(complete_analysis_plan)
mcp.tool()(delete_analysis_plan)

# business tools — 비즈니스 분석
from bi_agent_mcp.tools.business import (
    revenue_analysis,
    rfm_analysis,
    ltv_analysis,
    churn_analysis,
    pareto_analysis,
    growth_analysis,
)

mcp.tool()(revenue_analysis)
mcp.tool()(rfm_analysis)
mcp.tool()(ltv_analysis)
mcp.tool()(churn_analysis)
mcp.tool()(pareto_analysis)
mcp.tool()(growth_analysis)

# product tools — 프로덕트 분석
from bi_agent_mcp.tools.product import (
    active_users,
    retention_curve,
    feature_adoption,
    ab_test_analysis,
    user_journey,
)

mcp.tool()(active_users)
mcp.tool()(retention_curve)
mcp.tool()(feature_adoption)
mcp.tool()(ab_test_analysis)
mcp.tool()(user_journey)

# marketing tools — 마케팅 분석
from bi_agent_mcp.tools.marketing import (
    campaign_performance,
    channel_attribution,
    cac_roas,
    conversion_funnel,
)

mcp.tool()(campaign_performance)
mcp.tool()(channel_attribution)
mcp.tool()(cac_roas)
mcp.tool()(conversion_funnel)

# forecast tools — 시계열 예측
from bi_agent_mcp.tools.forecast import (
    moving_average_forecast,
    exponential_smoothing_forecast,
    linear_trend_forecast,
)

mcp.tool()(moving_average_forecast)
mcp.tool()(exponential_smoothing_forecast)
mcp.tool()(linear_trend_forecast)

# anomaly tools — 이상치 탐지
from bi_agent_mcp.tools.anomaly import (
    iqr_anomaly_detection,
    zscore_anomaly_detection,
)

mcp.tool()(iqr_anomaly_detection)
mcp.tool()(zscore_anomaly_detection)

# stats tools — 통계 분석 (기술통계, 추론통계, 가설검정)
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

mcp.tool()(descriptive_stats)
mcp.tool()(percentile_analysis)
mcp.tool()(boxplot_summary)
mcp.tool()(confidence_interval)
mcp.tool()(sampling_error)
mcp.tool()(ttest_one_sample)
mcp.tool()(ttest_independent)
mcp.tool()(ttest_paired)
mcp.tool()(anova_one_way)
mcp.tool()(chi_square_test)
mcp.tool()(normality_test)

# helper tools — 분석/BI 헬퍼 (가설검증 가이드, 방법론 추천, 결과 해석, Tableau 안내)
from bi_agent_mcp.tools.helper import (
    hypothesis_helper,
    analysis_method_recommender,
    query_result_interpreter,
    tableau_viz_guide,
)

mcp.tool()(hypothesis_helper)
mcp.tool()(analysis_method_recommender)
mcp.tool()(query_result_interpreter)
mcp.tool()(tableau_viz_guide)

# viz_helper tools — 시각화 어드바이저
from bi_agent_mcp.tools.viz_helper import visualize_advisor, dashboard_design_guide

mcp.tool()(visualize_advisor)
mcp.tool()(dashboard_design_guide)

# bi_helper tools — BI 도구 선택 가이드
from bi_agent_mcp.tools.bi_helper import bi_tool_selector

mcp.tool()(bi_tool_selector)

# ab_test tools — A/B 테스트 전문 분석
from bi_agent_mcp.tools.ab_test import (
    ab_sample_size,
    ab_multivariate,
    ab_segment_breakdown,
    ab_time_decay,
)

mcp.tool()(ab_sample_size)
mcp.tool()(ab_multivariate)
mcp.tool()(ab_segment_breakdown)
mcp.tool()(ab_time_decay)

# amplitude tools — 강화 (퍼널/리텐션/코호트/사용자속성/Lexicon)
from bi_agent_mcp.tools.amplitude import (
    get_amplitude_funnel,
    get_amplitude_retention,
    get_amplitude_cohort,
    get_amplitude_user_properties,
    get_amplitude_event_types,
)

mcp.tool()(get_amplitude_funnel)
mcp.tool()(get_amplitude_retention)
mcp.tool()(get_amplitude_cohort)
mcp.tool()(get_amplitude_user_properties)
mcp.tool()(get_amplitude_event_types)

# mixpanel tools — 이벤트/퍼널/리텐션/코호트
from bi_agent_mcp.tools.mixpanel import (
    connect_mixpanel,
    get_mixpanel_events,
    get_mixpanel_funnel,
    get_mixpanel_retention,
    get_mixpanel_cohort_count,
)

mcp.tool()(connect_mixpanel)
mcp.tool()(get_mixpanel_events)
mcp.tool()(get_mixpanel_funnel)
mcp.tool()(get_mixpanel_retention)
mcp.tool()(get_mixpanel_cohort_count)

# metabase tools — 카드/대시보드/쿼리 실행
from bi_agent_mcp.tools.metabase import (
    connect_metabase,
    list_metabase_questions,
    run_metabase_question,
    list_metabase_dashboards,
)

mcp.tool()(connect_metabase)
mcp.tool()(list_metabase_questions)
mcp.tool()(run_metabase_question)
mcp.tool()(list_metabase_dashboards)

# superset tools — 차트/대시보드/SQL 실행
from bi_agent_mcp.tools.superset import (
    connect_superset,
    list_superset_charts,
    run_superset_sql,
    list_superset_dashboards,
)

mcp.tool()(connect_superset)
mcp.tool()(list_superset_charts)
mcp.tool()(run_superset_sql)
mcp.tool()(list_superset_dashboards)

# posthog tools — 이벤트/인사이트/피처플래그/실험
from bi_agent_mcp.tools.posthog import (
    connect_posthog,
    get_posthog_events,
    get_posthog_insights,
    get_posthog_feature_flags,
    get_posthog_experiments,
)

mcp.tool()(connect_posthog)
mcp.tool()(get_posthog_events)
mcp.tool()(get_posthog_insights)
mcp.tool()(get_posthog_feature_flags)
mcp.tool()(get_posthog_experiments)

# tableau_server tools — Tableau Server/Cloud REST API
from bi_agent_mcp.tools.tableau_server import (
    connect_tableau_server,
    list_tableau_workbooks,
    list_tableau_views,
    get_tableau_view_data,
    refresh_tableau_datasource,
)

mcp.tool()(connect_tableau_server)
mcp.tool()(list_tableau_workbooks)
mcp.tool()(list_tableau_views)
mcp.tool()(get_tableau_view_data)
mcp.tool()(refresh_tableau_datasource)

# powerbi tools — Power BI REST API
from bi_agent_mcp.tools.powerbi import (
    connect_powerbi,
    list_powerbi_workspaces,
    list_powerbi_reports,
    get_powerbi_dataset_tables,
    push_powerbi_rows,
)

mcp.tool()(connect_powerbi)
mcp.tool()(list_powerbi_workspaces)
mcp.tool()(list_powerbi_reports)
mcp.tool()(get_powerbi_dataset_tables)
mcp.tool()(push_powerbi_rows)

# quicksight tools — AWS QuickSight boto3 연동
from bi_agent_mcp.tools.quicksight import (
    connect_quicksight,
    list_quicksight_datasets,
    list_quicksight_analyses,
    list_quicksight_dashboards,
    get_quicksight_embed_url,
)

mcp.tool()(connect_quicksight)
mcp.tool()(list_quicksight_datasets)
mcp.tool()(list_quicksight_analyses)
mcp.tool()(list_quicksight_dashboards)
mcp.tool()(get_quicksight_embed_url)

# looker_studio tools — Google Sheets API 연동
from bi_agent_mcp.tools.looker_studio import (
    connect_looker_studio,
    get_sheet_data,
    list_sheets,
    append_sheet_data,
    get_spreadsheet_metadata,
)

mcp.tool()(connect_looker_studio)
mcp.tool()(get_sheet_data)
mcp.tool()(list_sheets)
mcp.tool()(append_sheet_data)
mcp.tool()(get_spreadsheet_metadata)

if __name__ == "__main__":
    mcp.run()
