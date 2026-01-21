"""
DataSourceAgent 테스트 스크립트
Docker PostgreSQL/MySQL 연결 테스트
"""
import asyncio
import os
import sys

# 프로젝트 루트를 path에 추가
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

async def test_postgres_mcp():
    """PostgreSQL MCP 서버 연결 테스트"""
    from backend.agents.data_source.mcp_client import MCPClient
    
    print("=" * 50)
    print("PostgreSQL MCP 서버 연결 테스트")
    print("=" * 50)
    
    # 환경변수 설정 (Docker 컨테이너용 - postgres_server.js 기대값)
    env = {
        "POSTGRES_HOST": os.getenv("DB_HOST", "localhost"),
        "POSTGRES_PORT": os.getenv("DB_PORT", "5433"),
        "POSTGRES_DB": os.getenv("DB_NAME", "biagent_test"),
        "POSTGRES_USER": os.getenv("DB_USER", "biagent"),
        "POSTGRES_PASSWORD": os.getenv("DB_PASSWORD", "biagent123"),
    }
    
    print(f"연결 정보: {env['POSTGRES_HOST']}:{env['POSTGRES_PORT']}/{env['POSTGRES_DB']}")
    
    server_path = os.path.join(project_root, "backend/mcp_servers/postgres_server.js")
    client = MCPClient(server_path, env=env)
    
    try:
        print("\n1. MCP 서버 연결 중...")
        await client.connect()
        print("   [OK] 연결 성공!")
        
        print("\n2. 사용 가능한 도구 목록:")
        tools = await client.list_tools()
        for tool in tools:
            print(f"   - {tool.name}")
        
        print("\n3. 테이블 목록 조회...")
        result = await client.call_tool("list_tables", {})
        if hasattr(result, 'content') and result.content:
            print(f"   {result.content[0].text}")
        
        print("\n4. 쿼리 실행 테스트...")
        query_result = await client.call_tool("query", {"sql": "SELECT * FROM sales LIMIT 3"})
        if hasattr(query_result, 'content') and query_result.content:
            print(f"   결과: {query_result.content[0].text[:500]}")
        
        print("\n[SUCCESS] PostgreSQL MCP 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await client.disconnect()

async def main():
    success = await test_postgres_mcp()
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
