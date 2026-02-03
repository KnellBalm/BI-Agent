import asyncio
import os
import pandas as pd
from backend.agents.data_source.data_source_agent import DataSourceAgent
from dotenv import load_dotenv

load_dotenv()

async def test_excel_direct():
    print("\n--- Testing Excel Direct (Pandas) ---")
    agent = DataSourceAgent()
    excel_path = "tmp/sample.xlsx"
    
    # 샘플 파일이 없으면 생성
    if not os.path.exists(excel_path):
        df = pd.DataFrame({'Name': ['Alice', 'Bob'], 'Age': [25, 30]})
        df.to_excel(excel_path, index=False)
        
    df = await agent.read_excel(excel_path)
    print("Excel Data:")
    print(df)
    await agent.close_all()

async def test_excel_mcp():
    print("\n--- Testing Excel via MCP ---")
    agent = DataSourceAgent()
    connection_info = {
        "id": "excel_test",
        "type": "excel",
        "server_path": os.path.abspath("backend/mcp_servers/excel_server.js"),
        "file_path": os.path.abspath("tmp/sample.xlsx")
    }
    
    df = await agent.read_excel(connection_info)
    print("Excel Data (MCP):")
    print(df)
    await agent.close_all()

async def test_sql_generation():
    print("\n--- Testing SQL Generation ---")
    from backend.orchestrator import QuotaManager
    from backend.orchestrator.llm_provider import GeminiProvider
    
    quota_manager = QuotaManager()
    llm = GeminiProvider(quota_manager=quota_manager)
    agent = DataSourceAgent()
    agent.sql_generator.llm = llm # 주입
    
    connection_info = {
        "id": "pg_test",
        "type": "postgres",
        "server_path": os.path.abspath("backend/mcp_servers/postgres_server.js"),
        "config": {
            "DB_HOST": os.getenv("DB_HOST", "localhost"),
            "DB_PORT": os.getenv("DB_PORT", "5432"),
            "DB_NAME": os.getenv("DB_NAME", "postgres"),
            "DB_USER": os.getenv("DB_USER", "postgres"),
            "DB_PASSWORD": os.getenv("DB_PASSWORD", "")
        }
    }
    
    # 쿼리 시도 (DB가 떠있어야 함)
    try:
        df = await agent.query_database(connection_info, "모든 사용자 정보를 보여줘")
        print("DB Data:")
        print(df.head())
    except Exception as e:
        print(f"DB Query failed (maybe DB is down): {e}")
    finally:
        await agent.close_all()
        await quota_manager.close()

if __name__ == "__main__":
    if not os.path.exists("tmp"):
        os.makedirs("tmp")
    
    async def run_tests():
        await test_excel_direct()
        await test_excel_mcp()
        await test_sql_generation()
        
    asyncio.run(run_tests())
