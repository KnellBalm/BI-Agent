"""INVESTIGATE 스테이지 템플릿."""


def render(title: str, date: str, connection: str = "", probing_questions: str = "", **kwargs) -> str:
    return f"""\
# INVESTIGATE - {title}

> 날짜: {date}

## Probing Questions
{probing_questions or "1. 가설을 순차적으로 검증할까요, 병렬로 검증할까요?\\n2. 가설을 기각하기 위한 신뢰 수준은 얼마인가요?\\n3. 통제해야 할 교란 변수가 있나요?"}

## Context from Prior Stages
<!-- StageExecutor가 이전 스테이지 RESULT 블록을 자동 주입합니다 -->

## Hypothesis 1: [가설 제목]
<!-- BI-EXEC: {{"tool": "query_database", "args": {{"query_description": "가설 검증을 위한 SQL 쿼리 설명"}}}} -->
<!-- RESULT:START -->
<!-- RESULT:END -->

**Finding**: [분석 결과]
**Confidence**: [HIGH/MEDIUM/LOW]

## Hypothesis 2: [가설 제목]
<!-- BI-EXEC: {{"tool": "query_database", "args": {{"query_description": "가설 검증을 위한 SQL 쿼리 설명"}}}} -->
<!-- RESULT:START -->
<!-- RESULT:END -->

**Finding**: [분석 결과]
**Confidence**: [HIGH/MEDIUM/LOW]

## Synthesis
| 요인 | 영향도 | 신뢰도 |
|------|--------|--------|
| [요인 1] | [수치] | [HIGH/MEDIUM/LOW] |
| [요인 2] | [수치] | [HIGH/MEDIUM/LOW] |
"""
