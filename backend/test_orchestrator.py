import asyncio
import os
from dotenv import load_dotenv
from backend.orchestrator.orchestrator import Orchestrator
from backend.agents.data_source.data_source_agent import DataSourceAgent
from backend.agents.bi_tool.bi_tool_agent import BIToolAgent
from backend.agents.bi_tool.json_parser import BIJsonParser

# .env 파일 로드
load_dotenv()

async def test_single_query(query: str):
    print(f"--- Query: {query} ---")
    
    # 에이전트 초기화
    data_agent = DataSourceAgent()
    bi_json_path = "backend/data/bi_solution.json"
    parser = BIJsonParser(bi_json_path)
    bi_agent = BIToolAgent(parser=parser)
    orchestrator = Orchestrator(data_agent=data_agent, bi_agent=bi_agent)
    
    # context 설정
    test_connection_info = {
        "id": "test_pg",
        "type": "postgres",
        "server_path": "backend/mcp_servers/postgres_server.js",
        "config": {
            "DB_HOST": os.getenv("DB_HOST", "localhost"),
            "DB_PORT": os.getenv("DB_PORT", "5432"),
            "DB_NAME": os.getenv("DB_NAME", "postgres"),
            "DB_USER": os.getenv("DB_USER", "postgres"),
            "DB_PASSWORD": os.getenv("DB_PASSWORD", "")
        }
    }
    context = {"connection_info": test_connection_info}

    try:
        result = await orchestrator.run(query, context=context)
        print(f"Intent: {result.get('intent')}")
        print(f"Response: {result.get('final_response')}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await data_agent.close_all()

if __name__ == "__main__":
    if not os.path.exists("backend/data"):
        os.makedirs("backend/data")
    
    queries = [
        "안녕? 넌 누구니?"
    ]
    
    for q in queries:
        asyncio.run(test_single_query(q))
