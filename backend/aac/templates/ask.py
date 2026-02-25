"""ASK 스테이지 템플릿."""


def render(title: str, date: str, connection: str = "", probing_questions: str = "", **kwargs) -> str:
    return f"""\
# ASK - {title}

> 생성일: {date} | 연결: {connection or "(미설정)"}

## Probing Questions
{probing_questions or "1. 이 분석의 핵심 질문은 무엇인가요?\\n2. 어떤 기간/세그먼트에 집중할 것인가요?\\n3. 성공적인 분석 결과물은 어떤 형태인가요?"}

## Question
[이 분석에서 답하고자 하는 핵심 질문을 작성하세요]

## Scope
- 기간: [시작일] ~ [종료일]
- 단위: [일/주/월]
- 세그먼트: [분석 차원 목록]

## Hypothesis Tree
1. [가설 1]
2. [가설 2]
3. [가설 3]

## Success Criteria
- [성공적인 분석의 기준을 작성하세요]

## Data Requirements
- 테이블: [필요한 테이블 목록]
- 지표: [분석할 측정값]
- 차원: [분류 기준]
"""
