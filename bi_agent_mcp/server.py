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

import os
LOAD_ALL = os.getenv("BI_AGENT_LOAD_ALL", "false").lower() == "true"

def register_tool(func, is_core=False):
    if is_core or LOAD_ALL:
        return mcp.tool()(func)
    return func


# v0 file tools — CSV/Excel 파일 데이터 소스
from bi_agent_mcp.tools.files import connect_file, list_files, query_file, get_file_schema

register_tool(connect_file, is_core=True)
register_tool(list_files, is_core=True)
register_tool(query_file, is_core=True)
register_tool(get_file_schema, is_core=False)

# v0 tools — DB 연결 및 쿼리
register_tool(connect_db, is_core=True)
register_tool(list_connections, is_core=True)
register_tool(get_schema, is_core=True)
register_tool(run_query, is_core=True)
register_tool(profile_table, is_core=True)
register_tool(clear_cache, is_core=False)

# v1 tools (External Data Sources)
from bi_agent_mcp.tools.ga4 import connect_ga4, get_ga4_report
from bi_agent_mcp.tools.amplitude import connect_amplitude, get_amplitude_events

register_tool(connect_ga4, is_core=True)
register_tool(get_ga4_report, is_core=True)
register_tool(connect_amplitude, is_core=False)
register_tool(get_amplitude_events, is_core=False)

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

register_tool(suggest_analysis, is_core=False)
register_tool(generate_report, is_core=True)
register_tool(save_query, is_core=False)
register_tool(list_saved_queries, is_core=False)
register_tool(load_domain_context, is_core=False)
register_tool(list_query_history, is_core=False)
register_tool(search_saved_queries, is_core=False)
register_tool(run_saved_query, is_core=False)
register_tool(delete_saved_query, is_core=False)

# v2 tools (Output Generation)
from bi_agent_mcp.tools.tableau import generate_twbx

register_tool(generate_twbx, is_core=False)

# dashboard tools
from bi_agent_mcp.tools.dashboard import generate_dashboard, chart_from_file

register_tool(generate_dashboard, is_core=True)
register_tool(chart_from_file, is_core=True)

# validation tools — 데이터 품질 검증
from bi_agent_mcp.tools.validation import validate_data, validate_query_result

register_tool(validate_data, is_core=False)
register_tool(validate_query_result, is_core=False)

# cross-source tools — 멀티 소스 조인 쿼리
from bi_agent_mcp.tools.cross_source import cross_query

register_tool(cross_query, is_core=False)

# setup tools — agent 대화 기반 초기 설정
from bi_agent_mcp.tools.setup import (
    check_setup_status,
    configure_datasource,
    test_datasource,
)

register_tool(check_setup_status, is_core=False)
register_tool(configure_datasource, is_core=False)
register_tool(test_datasource, is_core=False)

# context tools — 질문 기반 컨텍스트 및 테이블 관계
from bi_agent_mcp.tools.context import get_context_for_question, get_table_relationships

register_tool(get_context_for_question, is_core=False)
register_tool(get_table_relationships, is_core=False)

# alerts tools — SQL 기반 알림 등록/평가/관리
from bi_agent_mcp.tools.alerts import create_alert, check_alerts, list_alerts, delete_alert

register_tool(create_alert, is_core=False)
register_tool(check_alerts, is_core=False)
register_tool(list_alerts, is_core=False)
register_tool(delete_alert, is_core=False)

# compare tools — 두 쿼리 결과 비교
from bi_agent_mcp.tools.compare import compare_queries

register_tool(compare_queries, is_core=False)

# text-to-sql tools — 자연어 → SQL 자동 생성
from bi_agent_mcp.tools.text_to_sql import generate_sql

register_tool(generate_sql, is_core=False)

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

register_tool(trend_analysis, is_core=False)
register_tool(correlation_analysis, is_core=False)
register_tool(distribution_analysis, is_core=False)
register_tool(segment_analysis, is_core=False)
register_tool(funnel_analysis, is_core=False)
register_tool(cohort_analysis, is_core=False)
register_tool(pivot_table, is_core=False)
register_tool(top_n_analysis, is_core=False)

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

register_tool(create_analysis_plan, is_core=False)
register_tool(get_analysis_plan, is_core=False)
register_tool(update_analysis_step, is_core=False)
register_tool(add_analysis_step, is_core=False)
register_tool(synthesize_findings, is_core=False)
register_tool(list_analysis_plans, is_core=False)
register_tool(complete_analysis_plan, is_core=False)
register_tool(delete_analysis_plan, is_core=False)

# business tools — 비즈니스 분석
from bi_agent_mcp.tools.business import (
    revenue_analysis,
    rfm_analysis,
    ltv_analysis,
    churn_analysis,
    pareto_analysis,
    growth_analysis,
)

register_tool(revenue_analysis, is_core=False)
register_tool(rfm_analysis, is_core=False)
register_tool(ltv_analysis, is_core=False)
register_tool(churn_analysis, is_core=False)
register_tool(pareto_analysis, is_core=False)
register_tool(growth_analysis, is_core=False)

# product tools — 프로덕트 분석
from bi_agent_mcp.tools.product import (
    active_users,
    retention_curve,
    feature_adoption,
    ab_test_analysis,
    user_journey,
)

register_tool(active_users, is_core=False)
register_tool(retention_curve, is_core=False)
register_tool(feature_adoption, is_core=False)
register_tool(ab_test_analysis, is_core=False)
register_tool(user_journey, is_core=False)

# marketing tools — 마케팅 분석
from bi_agent_mcp.tools.marketing import (
    campaign_performance,
    channel_attribution,
    cac_roas,
    conversion_funnel,
)

register_tool(campaign_performance, is_core=False)
register_tool(channel_attribution, is_core=False)
register_tool(cac_roas, is_core=False)
register_tool(conversion_funnel, is_core=False)

# forecast tools — 시계열 예측
from bi_agent_mcp.tools.forecast import (
    moving_average_forecast,
    exponential_smoothing_forecast,
    linear_trend_forecast,
)

register_tool(moving_average_forecast, is_core=False)
register_tool(exponential_smoothing_forecast, is_core=False)
register_tool(linear_trend_forecast, is_core=False)

# anomaly tools — 이상치 탐지
from bi_agent_mcp.tools.anomaly import (
    iqr_anomaly_detection,
    zscore_anomaly_detection,
)

register_tool(iqr_anomaly_detection, is_core=False)
register_tool(zscore_anomaly_detection, is_core=False)

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

register_tool(descriptive_stats, is_core=False)
register_tool(percentile_analysis, is_core=False)
register_tool(boxplot_summary, is_core=False)
register_tool(confidence_interval, is_core=False)
register_tool(sampling_error, is_core=False)
register_tool(ttest_one_sample, is_core=False)
register_tool(ttest_independent, is_core=False)
register_tool(ttest_paired, is_core=False)
register_tool(anova_one_way, is_core=False)
register_tool(chi_square_test, is_core=False)
register_tool(normality_test, is_core=False)

# helper tools — 분석/BI 헬퍼 (가설검증 가이드, 방법론 추천, 결과 해석, Tableau 안내)
from bi_agent_mcp.tools.helper import (
    hypothesis_helper,
    analysis_method_recommender,
    query_result_interpreter,
    tableau_viz_guide,
)

register_tool(hypothesis_helper, is_core=False)
register_tool(analysis_method_recommender, is_core=False)
register_tool(query_result_interpreter, is_core=False)
register_tool(tableau_viz_guide, is_core=False)

# viz_helper tools — 시각화 어드바이저
from bi_agent_mcp.tools.viz_helper import visualize_advisor, dashboard_design_guide

register_tool(visualize_advisor, is_core=False)
register_tool(dashboard_design_guide, is_core=False)

# bi_helper tools — BI 도구 선택 가이드
from bi_agent_mcp.tools.bi_helper import bi_tool_selector

register_tool(bi_tool_selector, is_core=False)

# ab_test tools — A/B 테스트 전문 분석
from bi_agent_mcp.tools.ab_test import (
    ab_sample_size,
    ab_multivariate,
    ab_segment_breakdown,
    ab_time_decay,
)

register_tool(ab_sample_size, is_core=False)
register_tool(ab_multivariate, is_core=False)
register_tool(ab_segment_breakdown, is_core=False)
register_tool(ab_time_decay, is_core=False)

# amplitude tools — 강화 (퍼널/리텐션/코호트/사용자속성/Lexicon)
from bi_agent_mcp.tools.amplitude import (
    get_amplitude_funnel,
    get_amplitude_retention,
    get_amplitude_cohort,
    get_amplitude_user_properties,
    get_amplitude_event_types,
)

register_tool(get_amplitude_funnel, is_core=False)
register_tool(get_amplitude_retention, is_core=False)
register_tool(get_amplitude_cohort, is_core=False)
register_tool(get_amplitude_user_properties, is_core=False)
register_tool(get_amplitude_event_types, is_core=False)

# mixpanel tools — 이벤트/퍼널/리텐션/코호트
from bi_agent_mcp.tools.mixpanel import (
    connect_mixpanel,
    get_mixpanel_events,
    get_mixpanel_funnel,
    get_mixpanel_retention,
    get_mixpanel_cohort_count,
)

register_tool(connect_mixpanel, is_core=False)
register_tool(get_mixpanel_events, is_core=False)
register_tool(get_mixpanel_funnel, is_core=False)
register_tool(get_mixpanel_retention, is_core=False)
register_tool(get_mixpanel_cohort_count, is_core=False)

# metabase tools — 카드/대시보드/쿼리 실행
from bi_agent_mcp.tools.metabase import (
    connect_metabase,
    list_metabase_questions,
    run_metabase_question,
    list_metabase_dashboards,
)

register_tool(connect_metabase, is_core=False)
register_tool(list_metabase_questions, is_core=False)
register_tool(run_metabase_question, is_core=False)
register_tool(list_metabase_dashboards, is_core=False)

# superset tools — 차트/대시보드/SQL 실행
from bi_agent_mcp.tools.superset import (
    connect_superset,
    list_superset_charts,
    run_superset_sql,
    list_superset_dashboards,
)

register_tool(connect_superset, is_core=False)
register_tool(list_superset_charts, is_core=False)
register_tool(run_superset_sql, is_core=False)
register_tool(list_superset_dashboards, is_core=False)

# posthog tools — 이벤트/인사이트/피처플래그/실험
from bi_agent_mcp.tools.posthog import (
    connect_posthog,
    get_posthog_events,
    get_posthog_insights,
    get_posthog_feature_flags,
    get_posthog_experiments,
)

register_tool(connect_posthog, is_core=False)
register_tool(get_posthog_events, is_core=False)
register_tool(get_posthog_insights, is_core=False)
register_tool(get_posthog_feature_flags, is_core=False)
register_tool(get_posthog_experiments, is_core=False)

# tableau_server tools — Tableau Server/Cloud REST API
from bi_agent_mcp.tools.tableau_server import (
    connect_tableau_server,
    list_tableau_workbooks,
    list_tableau_views,
    get_tableau_view_data,
    refresh_tableau_datasource,
)

register_tool(connect_tableau_server, is_core=False)
register_tool(list_tableau_workbooks, is_core=False)
register_tool(list_tableau_views, is_core=False)
register_tool(get_tableau_view_data, is_core=False)
register_tool(refresh_tableau_datasource, is_core=False)

# powerbi tools — Power BI REST API
from bi_agent_mcp.tools.powerbi import (
    connect_powerbi,
    list_powerbi_workspaces,
    list_powerbi_reports,
    get_powerbi_dataset_tables,
    push_powerbi_rows,
)

register_tool(connect_powerbi, is_core=False)
register_tool(list_powerbi_workspaces, is_core=False)
register_tool(list_powerbi_reports, is_core=False)
register_tool(get_powerbi_dataset_tables, is_core=False)
register_tool(push_powerbi_rows, is_core=False)

# quicksight tools — AWS QuickSight boto3 연동
from bi_agent_mcp.tools.quicksight import (
    connect_quicksight,
    list_quicksight_datasets,
    list_quicksight_analyses,
    list_quicksight_dashboards,
    get_quicksight_embed_url,
)

register_tool(connect_quicksight, is_core=False)
register_tool(list_quicksight_datasets, is_core=False)
register_tool(list_quicksight_analyses, is_core=False)
register_tool(list_quicksight_dashboards, is_core=False)
register_tool(get_quicksight_embed_url, is_core=False)

# looker_studio tools — Google Sheets API 연동
from bi_agent_mcp.tools.looker_studio import (
    connect_looker_studio,
    get_sheet_data,
    list_sheets,
    append_sheet_data,
    get_spreadsheet_metadata,
)

register_tool(connect_looker_studio, is_core=False)
register_tool(get_sheet_data, is_core=False)
register_tool(list_sheets, is_core=False)
register_tool(append_sheet_data, is_core=False)
register_tool(get_spreadsheet_metadata, is_core=False)

# redash — Redash REST API 연동
from bi_agent_mcp.tools.redash import connect_redash, list_redash_queries, run_redash_query, list_redash_dashboards
register_tool(connect_redash, is_core=False)
register_tool(list_redash_queries, is_core=False)
register_tool(run_redash_query, is_core=False)
register_tool(list_redash_dashboards, is_core=False)

# dbt_cloud — dbt Cloud Admin API 연동
from bi_agent_mcp.tools.dbt_cloud import connect_dbt_cloud, list_dbt_jobs, get_dbt_run_results, list_dbt_models
register_tool(connect_dbt_cloud, is_core=False)
register_tool(list_dbt_jobs, is_core=False)
register_tool(get_dbt_run_results, is_core=False)
register_tool(list_dbt_models, is_core=False)

# grafana — Grafana HTTP API 연동
from bi_agent_mcp.tools.grafana import connect_grafana, list_grafana_dashboards, get_grafana_dashboard, query_grafana_datasource
register_tool(connect_grafana, is_core=False)
register_tool(list_grafana_dashboards, is_core=False)
register_tool(get_grafana_dashboard, is_core=False)
register_tool(query_grafana_datasource, is_core=False)


# segment — Segment Public API 연동
from bi_agent_mcp.tools.segment import connect_segment, get_segment_sources, get_segment_events, get_segment_traits

register_tool(connect_segment, is_core=False)
register_tool(get_segment_sources, is_core=False)
register_tool(get_segment_events, is_core=False)
register_tool(get_segment_traits, is_core=False)

# databricks — Databricks REST API 연동
from bi_agent_mcp.tools.databricks import connect_databricks, run_databricks_sql, list_databricks_clusters, list_databricks_jobs
register_tool(connect_databricks, is_core=False)
register_tool(run_databricks_sql, is_core=False)
register_tool(list_databricks_clusters, is_core=False)
register_tool(list_databricks_jobs, is_core=False)

# airbyte — Airbyte Config API 연동
from bi_agent_mcp.tools.airbyte import connect_airbyte, list_airbyte_sources, list_airbyte_connections, get_airbyte_sync_status
register_tool(connect_airbyte, is_core=False)
register_tool(list_airbyte_sources, is_core=False)
register_tool(list_airbyte_connections, is_core=False)
register_tool(get_airbyte_sync_status, is_core=False)

# heap — Heap Analytics 연동
from bi_agent_mcp.tools.heap import connect_heap, get_heap_events, get_heap_funnels, get_heap_user_properties
register_tool(connect_heap, is_core=False)
register_tool(get_heap_events, is_core=False)
register_tool(get_heap_funnels, is_core=False)
register_tool(get_heap_user_properties, is_core=False)

# orchestrator tools — BI 분석 진입점 (bi_start, bi_orchestrate)
from bi_agent_mcp.tools.orchestrator import bi_start, bi_orchestrate

register_tool(bi_start, is_core=True)
register_tool(bi_orchestrate, is_core=True)

if __name__ == "__main__":
    mcp.run()
