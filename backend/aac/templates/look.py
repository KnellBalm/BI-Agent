"""LOOK 스테이지 템플릿."""


def render(title: str, date: str, connection: str = "", probing_questions: str = "", data_sources: list = None, **kwargs) -> str:
    sources = data_sources or []
    bi_exec_blocks = ""
    for table in sources:
        bi_exec_blocks += f'<!-- BI-EXEC: {{"tool": "analyze_schema", "args": {{"table_name": "{table}"}}}} -->\n<!-- RESULT:START -->\n<!-- RESULT:END -->\n\n'
    if not bi_exec_blocks:
        bi_exec_blocks = '<!-- BI-EXEC: {"tool": "analyze_schema", "args": {"table_name": "your_table"}} -->\n<!-- RESULT:START -->\n<!-- RESULT:END -->\n'
    return f"""\
# LOOK - {title}

> 날짜: {date}

## Probing Questions
{probing_questions or "1. 데이터 품질 문제가 있나요?\\n2. 주요 시간 차원 컬럼은 무엇인가요?\\n3. 프로파일링에서 제외할 테이블이 있나요?"}

## Context from Prior Stages
<!-- StageExecutor가 이전 스테이지 RESULT 블록을 자동 주입합니다 -->

## Schema Profile
{bi_exec_blocks}
## Data Quality
<!-- BI-EXEC: {{"tool": "query_database", "args": {{"query_description": "데이터 품질 확인 쿼리를 작성하세요 (NULL 체크, 날짜 범위 등)"}}}} -->
<!-- RESULT:START -->
<!-- RESULT:END -->

## Initial Observations
- [초기 관찰 결과를 작성하세요]

## Segments to Investigate
1. [주요 세그먼트 1]
2. [주요 세그먼트 2]
"""
