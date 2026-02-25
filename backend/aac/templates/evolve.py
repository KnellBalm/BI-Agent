"""EVOLVE 스테이지 템플릿 (v1: 실행 없음, 순수 마크다운)."""


def render(title: str, date: str = "", **kwargs) -> str:
    return f"""\
# EVOLVE - {title}

> 날짜: {date}

## Questions Answered
- [ASK의 원래 질문] → [INVESTIGATE의 답변]

## New Questions Raised
1. [후속 질문 1]
2. [후속 질문 2]

## Suggested Next Analyses
- [분석 아이디어 1]: /analysis-new "[제목]"
- [분석 아이디어 2]: /analysis-new "[제목]"

## Impact Tracking
| 권고사항 | 구현 여부 | 실제 영향 |
|---------|----------|---------|
| [권고사항 1] | [미구현/구현중/완료] | [측정된 영향] |
"""
