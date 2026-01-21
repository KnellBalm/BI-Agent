import os
from typing import List, Dict, Any, Optional
from backend.orchestrator.llm_provider import LLMProvider, GeminiProvider

class SQLGenerator:
    """
    자연어를 SQL 쿼리로 변환하는 클래스
    """
    def __init__(self, llm: Optional[LLMProvider] = None):
        # 외부에서 LLMProvider를 주입받거나 기본 GeminiProvider 사용
        self.llm = llm or GeminiProvider()

    async def generate_sql(self, user_query: str, db_type: str, schema_info: str) -> str:
        """
        사용자 쿼리와 스키마 정보를 바탕으로 SQL을 생성합니다.
        """
        prompt = f"""
당신은 SQL 전문가입니다. 사용자의 자연어 질문을 바탕으로 적절한 SQL 쿼리를 작성하세요.

데이터베이스 종류: {db_type}
스키마 정보:
{schema_info}

사용자 질문: "{user_query}"

규칙:
1. 오직 SQL 쿼리만 응답하세요. 다른 텍스트나 설명은 포함하지 마세요.
2. 쿼리는 마크다운 코드 블록(```sql ... ```)으로 감싸지 말고 순수 텍스트로만 작성하세요.
3. 데이터베이스 종류({db_type})의 문법을 엄격히 준수하세요.
4. 가능한 한 효율적인 쿼리를 작성하세요.

SQL:"""
        
        sql = await self.llm.generate(prompt)
        sql = sql.strip()
        
        # 가끔씩 LLM이 ```sql ... ``` 로 감싸는 경우가 있으므로 전처리
        if sql.startswith("```"):
            # ```sql 또는 ``` 가 올 수 있음
            lines = sql.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            sql = "\n".join(lines)
        
        return sql.strip()

if __name__ == "__main__":
    # 테스트 코드
    generator = SQLGenerator()
    test_schema = """
    Table: sales
    Columns: id (INT), product_name (TEXT), amount (FLOAT), sale_date (DATE)
    """
    test_query = "올해 가장 많이 팔린 제품 5개와 그 금액을 알려줘"
    
    try:
        sql = generator.generate_sql(test_query, "PostgreSQL", test_schema)
        print(f"Generated SQL:\n{sql}")
    except Exception as e:
        print(f"Error: {e}")
