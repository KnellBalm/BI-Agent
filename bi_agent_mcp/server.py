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

if __name__ == "__main__":
    mcp.run()
