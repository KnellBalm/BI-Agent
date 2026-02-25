"""Quick 분석 단일 파일 템플릿."""
from datetime import datetime


def render(question: str = "", connection: str = "", id: str = "", **kwargs) -> str:
    date = datetime.now().strftime("%Y-%m-%d")
    return f"""\
# Quick Analysis - {question or "빠른 분석"}

> ID: {id} | 날짜: {date} | 연결: {connection or "(미설정)"} | Status: active

## ASK
{question or "[분석 질문을 입력하세요]"}

## LOOK
<!-- BI-EXEC: {{"tool": "analyze_schema", "args": {{"table_name": "your_table"}}}} -->
<!-- RESULT:START -->
<!-- RESULT:END -->

## INVESTIGATE
<!-- BI-EXEC: {{"tool": "query_database", "args": {{"query_description": "[분석 쿼리를 설명하세요]"}}}} -->
<!-- RESULT:START -->
<!-- RESULT:END -->

## VOICE
[분석 결과를 요약하세요]

## EVOLVE
- [다음에 분석할 것]
"""
