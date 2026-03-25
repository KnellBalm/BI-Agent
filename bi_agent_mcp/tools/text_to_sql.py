"""자연어 → SQL 자동 생성 도구 — generate_sql."""
from __future__ import annotations

from bi_agent_mcp.tools.context import get_context_for_question
from bi_agent_mcp.tools.db import _connections

_SQL_GENERATION_RULES = """\
아래 규칙에 따라 SQL을 생성해주세요:

1. **SELECT 전용** — INSERT / UPDATE / DELETE / DROP 등 데이터 변경 구문은 절대 사용하지 마세요.
2. **스키마 준수** — 위 스키마에 명시된 테이블과 컬럼만 사용하세요.
3. **결과 형식** — 다음 형식으로 응답하세요:

```sql
SELECT ...
```

**설명:** 이 쿼리는 ...를 조회합니다.

**사용된 테이블:** table1, table2

4. 생성한 SQL은 `run_query` 도구로 실행할 수 있습니다.\
"""


def generate_sql(conn_id: str, question: str) -> str:
    """자연어 질문에 맞는 SQL 생성을 위한 스키마 컨텍스트와 지시문을 반환합니다.

    DB 스키마를 자동으로 수집하여 SQL 생성에 필요한 컨텍스트를 구성합니다.
    이 도구의 결과를 받은 LLM이 직접 SQL을 생성하며, 어떤 LLM provider에서도 동작합니다.
    생성된 SQL은 run_query 도구로 실행하세요.

    Args:
        conn_id: connect_db로 등록한 연결 ID
        question: 자연어 질문 (예: "지난 달 매출 상위 10개 상품을 알려줘")

    Returns:
        스키마 컨텍스트 + SQL 생성 지시문이 포함된 Markdown 문자열
    """
    # 연결 확인
    if conn_id not in _connections:
        return f"[ERROR] 연결을 찾을 수 없습니다: {conn_id}"

    # 스키마 컨텍스트 수집
    schema_context = get_context_for_question(conn_id, question)
    if schema_context.startswith("[ERROR]"):
        return schema_context

    db_type = _connections[conn_id].db_type

    return "\n".join([
        f"## SQL 생성 요청",
        f"",
        f"**질문:** {question}",
        f"**DB 타입:** {db_type}",
        f"",
        schema_context,
        f"",
        f"---",
        f"",
        _SQL_GENERATION_RULES,
    ])
