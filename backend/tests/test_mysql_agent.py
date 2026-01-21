
import asyncio
import os
import sys
import pandas as pd
from typing import Dict, Any
from dotenv import load_dotenv

# 환경 변수 로드 (GEMINI_API_KEY 등)
load_dotenv()

# backend 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.agents.data_source.data_source_agent import DataSourceAgent
from backend.orchestrator.connection_manager import ConnectionManager

async def test_mysql_agent():
    print("=== MySQL DataSourceAgent Verification ===")
    
    # 1. 초기화
    agent = DataSourceAgent()  # SQLGenerator가 내부적으로 GeminiProvider를 사용
    conn_manager = ConnectionManager()
    
    # 2. 연결 정보 가져오기
    conn_info = conn_manager.get_connection("test_mysql")
    if not conn_info:
        print("Error: 'test_mysql' connection not found in connections.json")
        return

    print(f"Connecting to MySQL: {conn_info['config']['MYSQL_DB']} at {conn_info['config']['MYSQL_HOST']}")

    # 3. 질의 테스트
    user_query = "최근 등록된 사용자 5명을 보여줘"
    print(f"User Query: {user_query}")
    
    try:
        df = await agent.query_database(conn_info, user_query)
        print("\n[Query Result]")
        if df.empty:
            print("No results returned.")
        else:
            print(df.to_string())
    except Exception as e:
        print(f"Error during query: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_mysql_agent())
