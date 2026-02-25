"""VOICE 스테이지 템플릿 (v1: 실행 없음, 순수 마크다운)."""


def render(title: str, date: str = "", **kwargs) -> str:
    return f"""\
# VOICE - {title}

> 날짜: {date}

## Executive Summary
[INVESTIGATE 스테이지의 핵심 발견사항을 요약하세요]

## Key Findings
1. [발견사항 1과 근거 데이터]
2. [발견사항 2와 근거 데이터]
3. [발견사항 3과 근거 데이터]

## Recommendations
1. [실행 가능한 권고사항 1]
2. [실행 가능한 권고사항 2]

## Appendix
[지원 차트, 표, 상세 데이터를 여기에 첨부하세요]
"""
