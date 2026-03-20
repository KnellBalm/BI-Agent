"""bi-agent MCP 서버 — FastMCP 인스턴스, tool 등록, 서버 실행."""
from mcp.server.fastmcp import FastMCP

from bi_agent_mcp.tools.db import (
    connect_db,
    list_connections,
    get_schema,
    run_query,
    profile_table,
)

mcp = FastMCP("bi-agent")

# v0 tools — DB 연결 및 쿼리
mcp.tool()(connect_db)
mcp.tool()(list_connections)
mcp.tool()(get_schema)
mcp.tool()(run_query)
mcp.tool()(profile_table)

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
    list_saved_queries
)

mcp.tool()(suggest_analysis)
mcp.tool()(generate_report)
mcp.tool()(save_query)
mcp.tool()(list_saved_queries)

# v2 tools (Output Generation)
from bi_agent_mcp.tools.tableau import generate_twbx

mcp.tool()(generate_twbx)

# setup tools — agent 대화 기반 초기 설정
from bi_agent_mcp.tools.setup import (
    check_setup_status,
    configure_datasource,
    test_datasource,
)

mcp.tool()(check_setup_status)
mcp.tool()(configure_datasource)
mcp.tool()(test_datasource)

if __name__ == "__main__":
    mcp.run()
