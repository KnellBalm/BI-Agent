# /bi-analyze — 도메인 인식 기반 심층 분석

비즈니스 도메인 지식을 풀 활용하여 데이터 분석을 수행하고 경영진 수준의 인사이트를 제공합니다.

## 실행 절차

1. **컨텍스트 로드**: `load_domain_context(sections="all")`로 전체 도메인 지식 로드
2. **질문 이해**: $ARGUMENTS로 받은 분석 질문/요청 파악
   - 질문이 없으면 "어떤 분석이 필요하신가요?" 질문
3. **KPI 매핑**: `context/03_kpi_dictionary.md`에서 질문과 관련된 KPI 식별
4. **패턴 선택**: `context/04_analysis_patterns.md`에서 적합한 분석 패턴 선택
5. **데이터 확인**: `list_connections`으로 필요한 데이터 소스 연결 확인
6. **분석 계획 수립**: `suggest_analysis(conn_id, table_name, question="...")`로 분석 플랜 생성
7. **쿼리 실행**: `run_query`로 필요한 SQL 쿼리 순차 실행
8. **결과 해석**: 수치를 `context/03_kpi_dictionary.md`의 목표값과 비교하여 해석
9. **용어 통일**: `context/05_glossary.md` 기준으로 용어 사용
10. **인사이트 도출**: 비즈니스 의미와 액션 아이템 제안
11. **쿼리 저장**: 재사용 가치 있는 쿼리는 `save_query`로 저장

## 출력 형식 (경영진 보고서 수준)
```
## 분석 요약
[핵심 발견 2-3줄]

## 주요 수치
[KPI 현황 vs 목표]

## 원인 분석
[데이터 기반 원인]

## 인사이트
[비즈니스적 해석]

## 권고 액션
[구체적 실행 방안 3개]
```

## 사용법

```
/bi-analyze 이번 달 매출이 왜 감소했을까?
/bi-analyze 어떤 고객 세그먼트가 가장 가치 있는가?
/bi-analyze 지난 분기 대비 MAU 변화 분석
```

## 참조 파일
- `context/` 전체 (분석 방향 결정)

## 사용 MCP 도구
- `load_domain_context(sections="all")`
- `list_connections`
- `suggest_analysis(conn_id, table_name, question)`
- `run_query(conn_id, sql)`
- `get_schema(conn_id, table_name)`
- `save_query(name, sql, description)`
- `list_query_history(limit=10)`
