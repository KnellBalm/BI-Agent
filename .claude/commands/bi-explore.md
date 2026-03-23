# /bi-explore — 도메인 맥락 기반 데이터 탐색

비즈니스 도메인 지식을 활용하여 데이터를 탐색하고 비즈니스 언어로 설명합니다.

## 실행 절차

1. `context/` 디렉토리의 파일들을 읽어 도메인 컨텍스트 파악
   - `context/01_business_context.md` — 비즈니스 개요
   - `context/02_data_sources.md` — 데이터 소스 정의
   - `context/03_kpi_dictionary.md` — KPI 정의
2. `list_connections`으로 현재 연결된 소스 확인 (미연결이면 `/bi-connect` 안내)
3. $ARGUMENTS로 받은 테이블명/파일ID에 대해:
   - `get_schema(conn_id, table_name)` — 컬럼 구조 파악
   - `profile_table(conn_id, table_name)` — 데이터 품질 분석 (NULL율, 분포)
4. `context/02_data_sources.md`의 테이블 설명과 매핑하여 비즈니스 의미 설명
5. `context/03_kpi_dictionary.md`의 KPI와 연관된 컬럼 자동 식별
6. `context/04_analysis_patterns.md` 참조하여 이 데이터로 할 수 있는 분석 TOP 3 제안
7. 흥미로운 데이터 패턴이나 이상치 발견 시 강조 표시

## 출력 형식
- **데이터 개요**: 테이블 규모, 기간, 주요 컬럼
- **비즈니스 의미**: 이 데이터가 비즈니스에서 의미하는 것
- **KPI 연결**: 이 테이블로 측정 가능한 KPI 목록
- **주목할 점**: 데이터 품질 이슈, 이상치, 특이사항
- **추천 분석**: 이 데이터로 할 수 있는 분석 제안

## 사용법

```
/bi-explore orders          # orders 테이블 탐색
/bi-explore file_abc12345   # 로드된 파일 탐색
/bi-explore                 # 전체 연결된 소스 개요
```

## 참조 파일
- `context/01_business_context.md`
- `context/02_data_sources.md`
- `context/03_kpi_dictionary.md`
- `context/04_analysis_patterns.md`

## 사용 MCP 도구
- `list_connections` / `list_files`
- `get_schema(conn_id, table_name)`
- `profile_table(conn_id, table_name)`
- `load_domain_context(sections="data_sources,kpis")`
