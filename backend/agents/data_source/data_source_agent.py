import pandas as pd
from typing import Dict, Any, Optional
from .mcp_client import MCPClient
from .sql_generator import SQLGenerator

class DataSourceAgent:
    """
    데이터 소스(DB, Excel)에서 데이터를 조회하고 분석하기 좋게 가공하는 Agent
    """
    def __init__(self, sql_generator: Optional[SQLGenerator] = None):
        self.sql_generator = sql_generator or SQLGenerator()
        self.clients: Dict[str, MCPClient] = {}

    async def get_client(self, connection_info: Dict[str, Any]) -> MCPClient:
        """
        연결 정보를 바탕으로 MCP 클라이언트를 생성하거나 가져옵니다.
        connection_info 예시:
        {
            "id": "user_db_1",
            "type": "postgres",
            "server_path": "backend/mcp_servers/postgres_server.js",
            "config": {
                "host": "localhost",
                "user": "...",
                "password": "..."
            }
        }
        """
        conn_id = connection_info.get("id")
        if conn_id not in self.clients:
            client = MCPClient(
                server_path=connection_info["server_path"],
                env=connection_info.get("config")
            )
            await client.connect()
            self.clients[conn_id] = client
        return self.clients[conn_id]

    async def query_database(self, connection_info: Dict[str, Any], user_query: str) -> pd.DataFrame:
        """
        자연어 질문을 받아 DB에 쿼리하고 결과를 DataFrame으로 반환합니다.
        """
        client = await self.get_client(connection_info)
        config = connection_info.get("config", {})
        
        # 1. 스키마 정보 가져오기 (MCP 도구 활용)
        # SaaS 공급자는 list_tables에 특정 인자(database, schema 등)가 필요할 수 있음
        schema_args = {k: v for k, v in config.items() if k not in ['server_path']}
        schema_result = await client.call_tool("list_tables", schema_args)
        
        schema_info = ""
        if hasattr(schema_result, 'content') and len(schema_result.content) > 0:
            schema_info = schema_result.content[0].text
        
        # 2. SQL 생성
        sql = await self.sql_generator.generate_sql(
            user_query, 
            connection_info["type"], 
            schema_info
        )
        
        # 3. SQL 실행
        query_args = {**schema_args, "sql": sql}
        query_result = await client.call_tool("query", query_args)
        
        # 4. pandas DataFrame으로 변환
        data = []
        if hasattr(query_result, 'content') and len(query_result.content) > 0:
            import json
            result_text = query_result.content[0].text
            try:
                parsed_result = json.loads(result_text)
                data = parsed_result.get("rows", [])
            except json.JSONDecodeError:
                print(f"Failed to parse query result: {result_text}")
            
        df = pd.DataFrame(data)
        return self._truncate_dataframe(df)

    async def read_excel(self, file_path_or_info: Any, user_query: Optional[str] = None) -> pd.DataFrame:
        """
        Excel 파일을 읽어 DataFrame으로 반환합니다. 
        user_query가 제공되면 LLM을 사용하여 데이터를 필터링/분석합니다.
        """
        df = pd.DataFrame()
        if isinstance(file_path_or_info, str):
            df = pd.read_excel(file_path_or_info)
        elif isinstance(file_path_or_info, dict):
            client = await self.get_client(file_path_or_info)
            params = {
                "file_path": file_path_or_info.get("file_path"),
                "sheet_name": file_path_or_info.get("sheet_name")
            }
            result = await client.call_tool("read_excel", {k: v for k, v in params.items() if v})
            
            data = []
            if hasattr(result, 'content') and len(result.content) > 0:
                import json
                parsed = json.loads(result.content[0].text)
                data = parsed.get("rows", [])
            df = pd.DataFrame(data)
        
        if df.empty:
            return df

        if user_query:
            # 자연어 쿼리가 있는 경우 LLM을 사용하여 데이터를 분석/필터링
            df = await self._analyze_dataframe_with_llm(df, user_query)
            
        return self._truncate_dataframe(df)

    async def _analyze_dataframe_with_llm(self, df: pd.DataFrame, user_query: str) -> pd.DataFrame:
        """LLM을 사용하여 DataFrame을 분석하거나 필터링합니다."""
        if not self.sql_generator or not self.sql_generator.llm:
            return df
            
        # 데이터프레임의 요약 정보 준비
        df_info = f"Columns: {list(df.columns)}\nSample Data (top 3):\n{df.head(3).to_string()}"
        
        prompt = f"""
다음 데이터프레임 정보를 바탕으로 사용자의 요청에 답하기 위한 데이터를 추출하거나 요약하세요.
데이터 정보:
{df_info}

사용자 요청: "{user_query}"

규칙:
1. 결과가 목록 형태라면 JSON 배열 형식으로 응답하세요.
2. 요약이나 인사이트가 필요하다면 텍스트로 응답하되, JSON 형식(`{{"type": "text", "content": "..."}}`)으로 감싸세요.
3. 데이터 필터링이 필요하다면 필터링된 결과 행들을 포함하는 JSON(`{{"type": "rows", "rows": [...]}}`)을 응답하세요.

응답:"""
        
        res = await self.sql_generator.llm.generate(prompt)
        try:
            import json
            clean_res = res.strip()
            if "{" in clean_res:
                clean_res = clean_res[clean_res.find("{"):clean_res.rfind("}")+1]
            analysis = json.loads(clean_res)
            
            if analysis.get("type") == "rows":
                return pd.DataFrame(analysis.get("rows", []))
            elif analysis.get("type") == "text":
                # 텍스트 결과인 경우 단일 행 DataFrame으로 변환하여 전달
                return pd.DataFrame([{"analysis_result": analysis.get("content")}])
        except:
            # 파싱 실패 시 원본 반환 또는 에러 로그
            pass
        return df

    def _truncate_dataframe(self, df: pd.DataFrame, max_rows: int = 50) -> pd.DataFrame:
        """LLM 컨텍스트 보호를 위해 데이터프레임 크기를 제한합니다."""
        if len(df) > max_rows:
            print(f"Warning: Result too large ({len(df)} rows). Truncating to top {max_rows}.")
            return df.head(max_rows)
        return df

    async def close_all(self):
        """모든 클라이언트 연결을 종료합니다."""
        for client in self.clients.values():
            await client.disconnect()
        self.clients = {}
