import os
from fastmcp import FastMCP
import psycopg2
import psycopg2.extras

# 1. MCP 서버 초기화 (서버 이름 지정)
mcp = FastMCP("Antigravity_PostgreSQL")

# 2. DB 연결 설정 (환경 변수로 관리)
DB_CONFIG = {
    "dbname": os.environ.get("PG_DBNAME", "suwon"),
    "user": os.environ.get("PG_USER", "odp"),
    "password": os.environ.get("PG_PASSWORD", ""),
    "host": os.environ.get("PG_HOST", "localhost"),
    "port": int(os.environ.get("PG_PORT", "5432")),
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

# 3. 도구(Tool) 정의: AI가 데이터베이스 구조를 파악할 수 있도록 제공
@mcp.tool()
def get_table_schema() -> str:
    """PostgreSQL 데이터베이스의 테이블 목록과 컬럼(스키마) 정보를 반환합니다."""
    query = """
        SELECT table_name, column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        ORDER BY table_name, ordinal_position;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(query)
                rows = cur.fetchall()
                
                # AI가 읽기 쉽게 텍스트로 포매팅
                schema_info = "테이블 및 컬럼 정보:\n"
                for row in rows:
                    schema_info += f"- {row['table_name']}.{row['column_name']} ({row['data_type']})\n"
                return schema_info
    except Exception as e:
        return f"스키마 조회 중 오류 발생: {str(e)}"

# 4. 도구(Tool) 정의: AI가 작성한 쿼리를 실행 (보안을 위해 SELECT만 허용)
@mcp.tool()
def run_select_query(query: str) -> str:
    """작성된 SELECT SQL 쿼리를 실행하고 최대 100건의 결과를 반환합니다."""
    
    # [안전장치] SELECT 구문만 실행되도록 하드 블락
    if not query.strip().upper().startswith("SELECT"):
        return "보안 위반: SELECT 쿼리만 실행할 수 있습니다. 데이터를 수정하거나 삭제할 수 없습니다."
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # [안전장치] 대량 데이터 반환 방지 (LIMIT 강제 적용)
                safe_query = f"SELECT * FROM ({query}) AS sub LIMIT 100"
                cur.execute(safe_query)
                rows = cur.fetchall()
                
                if not rows:
                    return "쿼리 결과가 없습니다."
                
                # 결과를 문자열로 반환하여 LLM이 파싱하게 함
                return str([dict(row) for row in rows])
    except Exception as e:
        return f"쿼리 실행 중 오류 발생: {str(e)}"

# 5. 표준 입력/출력(stdio)을 통해 MCP 서버 실행
if __name__ == "__main__":
    mcp.run()