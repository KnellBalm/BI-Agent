# /bi-report — 종합 BI 리포트 생성

도메인 지식과 KPI 정의를 기반으로 정기 BI 리포트를 자동 생성합니다.

## 실행 절차

1. **컨텍스트 로드**: `context/01_business_context.md`로 리포트 헤더 설정
2. **요청 파악**: $ARGUMENTS에서 리포트 주제, 기간, 대상 파악
   - 예: "월간 KPI 리포트", "주간 매출 현황", "Q1 전체 요약"
   - 기간이 없으면 "이번 달" 기준으로 처리
3. **KPI 수집**: `context/03_kpi_dictionary.md`의 핵심 KPI들을 순서대로 분석
4. **데이터 쿼리**: 각 KPI에 대해 `run_query` 실행하여 수치 수집
5. **비교 분석**: 전월/전년 동기 대비 변화율 계산
6. **리포트 생성**: `generate_report`로 마크다운 리포트 파일 생성 (~/Downloads/)
7. **인사이트 추가**: 눈에 띄는 변화나 이상치에 대한 코멘트 추가

## 리포트 구조
```
# [기간] BI 리포트 — [비즈니스명]
생성일: YYYY-MM-DD

## Executive Summary
[핵심 수치 3-5개 + 한 줄 해석]

## KPI 대시보드
[KPI별 실적 vs 목표 vs 전기비 표]

## 트렌드 분석
[주요 지표 추세]

## 이슈 & 기회
[주목할 변화 및 원인 추정]

## 권고사항
[데이터 기반 실행 과제]
```

## 사용법

```
/bi-report 월간 KPI 리포트
/bi-report 주간 매출 현황 2026-03-10~2026-03-16
/bi-report Q1 전체 요약
/bi-report 신규 가입자 분석 이번달
```

## 참조 파일
- `context/01_business_context.md` — 리포트 컨텍스트/헤더
- `context/03_kpi_dictionary.md` — KPI 정의 및 목표값
- `context/05_glossary.md` — 용어 통일

## 사용 MCP 도구
- `load_domain_context(sections="business,kpis")`
- `list_connections`
- `run_query(conn_id, sql)` (KPI별 반복)
- `generate_report(title, content)` — 마크다운 파일로 저장
- `list_saved_queries` — 저장된 쿼리 재활용
