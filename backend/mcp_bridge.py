#!/usr/bin/env python3
"""
MCP Bridge for BI-Agent

Node.js MCP 서버에서 Python Orchestrator를 호출하기 위한 브릿지 스크립트입니다.
stdin으로 JSON 요청을 받아 처리하고 stdout으로 결과를 반환합니다.

사용법:
    echo '{"action": "query_data", "params": {"query": "매출 보여줘"}}' | python mcp_bridge.py
"""

import asyncio
import json
import sys
import os

# 프로젝트 루트를 path에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, '.env'))

from backend.orchestrator import Orchestrator, ConnectionManager, GeminiProvider
from backend.agents.data_source.data_source_agent import DataSourceAgent
from backend.agents.bi_tool.bi_tool_agent import BIToolAgent
from backend.agents.bi_tool.json_parser import BIJsonParser


class MCPBridge:
    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.llm = GeminiProvider()
        self.data_agent = DataSourceAgent()
        
        bi_json_path = os.path.join(project_root, "backend/data/bi_solution.json")
        self.parser = BIJsonParser(bi_json_path)
        self.bi_agent = BIToolAgent(parser=self.parser)
        
        self.orchestrator = Orchestrator(
            llm=self.llm,
            data_agent=self.data_agent,
            bi_agent=self.bi_agent,
            connection_manager=self.connection_manager
        )

    async def handle_action(self, action: str, params: dict) -> dict:
        """액션에 따라 적절한 처리를 수행합니다."""
        
        if action == "query_data":
            query = params.get("query", "")
            connection_id = params.get("connection_id")
            
            context = {}
            if connection_id:
                context["connection_id"] = connection_id
            
            result = await self.orchestrator.run(query, context=context)
            return {
                "success": True,
                "response": result.get("final_response", ""),
                "data": result.get("data_result")
            }
        
        elif action == "modify_bi":
            action_text = params.get("action", "")
            result = await self.orchestrator.run(action_text, context={})
            return {
                "success": True,
                "response": result.get("final_response", "")
            }
        
        elif action == "list_connections":
            connections = self.connection_manager.list_connections()
            return {
                "success": True,
                "connections": [
                    {"id": c.get("id"), "type": c.get("type")}
                    for c in connections
                ]
            }
        
        elif action == "register_connection":
            conn_id = params.get("id")
            conn_type = params.get("type")
            config = params.get("config", {})
            
            # Use Python MCP servers by default (set MCP_USE_PYTHON=false to use JavaScript)
            use_python = os.getenv("MCP_USE_PYTHON", "true").lower() == "true"
            extension = ".py" if use_python else ".js"

            server_paths = {
                "postgres": os.path.join(project_root, f"backend/mcp_servers/postgres_server{extension}"),
                "mysql": os.path.join(project_root, f"backend/mcp_servers/mysql_server{extension}"),
                "excel": os.path.join(project_root, f"backend/mcp_servers/excel_server{extension}"),
                "bigquery": os.path.join(project_root, f"backend/mcp_servers/bigquery_server{extension}"),
                "snowflake": os.path.join(project_root, f"backend/mcp_servers/snowflake_server{extension}"),
                "gcp_manager": os.path.join(project_root, f"backend/mcp_servers/gcp_manager_server{extension}"),
            }
            
            conn_info = {
                "type": conn_type,
                "server_path": server_paths.get(conn_type, ""),
                "config": config
            }
            
            self.connection_manager.register_connection(conn_id, conn_info)
            return {
                "success": True,
                "message": f"Connection '{conn_id}' registered successfully."
            }
        
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}"
            }

    async def cleanup(self):
        """리소스 정리"""
        await self.data_agent.close_all()


async def main():
    # stdin에서 JSON 요청 읽기
    input_data = sys.stdin.read()
    
    try:
        request = json.loads(input_data)
    except json.JSONDecodeError as e:
        print(json.dumps({"success": False, "error": f"Invalid JSON: {e}"}))
        return
    
    action = request.get("action", "")
    params = request.get("params", {})
    
    bridge = MCPBridge()
    
    try:
        result = await bridge.handle_action(action, params)
        print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
    finally:
        await bridge.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
