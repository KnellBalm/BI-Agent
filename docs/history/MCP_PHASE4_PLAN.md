# MCP Phase 4 계획

**작성일:** 2026-03-24
**상태:** 계획 수립
**기반:** Phase 3 완료 (25개 도구, 303 테스트, 80.04% 커버리지)

---

## 현재 상태 (Phase 3 완료)

### 등록된 MCP 도구 (25개)

| 카테고리 | 도구 | 완성도 |
|----------|------|--------|
| **DB 핵심** (5) | connect_db, list_connections, get_schema, run_query, profile_table | 안정 |
| **파일 분석** (4) | connect_file, list_files, query_file, get_file_schema | 안정 |
| **외부 소스** (4) | connect_ga4, get_ga4_report, connect_amplitude, get_amplitude_events | 안정 |
| **분석/리포트** (6) | suggest_analysis, generate_report, save_query, list_saved_queries, load_domain_context, list_query_history | 안정 |
| **아웃풋** (3) | generate_twbx, generate_dashboard, chart_from_file | 안정 |
| **설정** (3) | check_setup_status, configure_datasource, test_datasource | 안정 |

### 지원 DB

PostgreSQL, MySQL, BigQuery, Snowflake (connector 설치됨)

### 테스트 현황

- 303개 단위 테스트, 커버리지 80.04%
- db.py 커버리지 51% (실제 DB 연결 코드로 단위 테스트 한계)

### 식별된 갭

1. **데이터 품질**: 쿼리 결과의 정합성/이상치를 검증하는 도구 없음
2. **자연어 쿼리**: 사용자가 SQL을 직접 작성해야 함 — LLM이 SQL을 생성하지만 스키마 컨텍스트 전달이 수동적
3. **쿼리 관리**: save_query/list_saved_queries가 있지만 태그, 검색, 공유 기능 부재
4. **멀티 소스 조인**: DB-파일, DB-DB 간 크로스 소스 쿼리 불가
5. **알림/스케줄링**: 반복 리포트 생성이나 임계값 알림 없음
6. **Snowflake**: connector 의존성은 있지만 connect_db에서 실제 연결 로직 미완성 가능성
7. **데이터 캐싱**: 동일 쿼리 반복 실행 시 캐싱 없음
8. **ERD/관계 시각화**: 테이블 간 관계를 파악하기 어려움

---

## Phase 4 비전

**"BI 분석가가 SQL 없이도 데이터 인사이트를 얻고, 데이터 품질을 신뢰할 수 있는 MCP 서버"**

Phase 1-3이 "데이터 접근과 시각화 기반"을 구축했다면, Phase 4는 **분석 생산성**과 **데이터 신뢰성**을 높이는 데 집중한다.

---

## 기능 후보 목록 (우선순위순)

### P0 (필수) — Phase 4 핵심 기능

#### 1. 데이터 품질 검증 도구 (`validate_data`)
- **설명**: 쿼리 결과 또는 테이블에 대해 NULL 비율, 유니크 제약, 범위 검증, 이상치 탐지 수행
- **동기**: BI 분석에서 데이터 품질 문제가 잘못된 의사결정으로 직결됨. profile_table이 기초 통계를 제공하지만, 규칙 기반 검증이 없음
- **구현 범위**:
  - `validate_data(conn_id, table, rules)` — 규칙 배열로 검증 (예: `{"column": "age", "check": "range", "min": 0, "max": 150}`)
  - `validate_query_result(conn_id, sql, rules)` — 쿼리 결과에 규칙 적용
  - 지원 규칙: not_null, unique, range, regex, enum, freshness (최신 데이터 타임스탬프 확인)
  - 결과: pass/fail 요약 + 위반 행 샘플
- **난이도**: 중
- **예상 도구 수**: 2개

#### 2. 스키마 컨텍스트 자동 주입 (`auto_context`)
- **설명**: LLM이 SQL을 생성할 때 필요한 스키마 정보를 자동으로 수집하고 구조화하여 제공
- **동기**: 현재 사용자가 get_schema를 수동 호출해야 함. LLM이 올바른 SQL을 생성하려면 테이블 관계, 컬럼 의미, 샘플 값이 필요
- **구현 범위**:
  - `get_context_for_question(conn_id, question)` — 자연어 질문에 관련된 테이블/컬럼을 추론하여 컨텍스트 반환
  - 내부적으로 get_schema + profile_table + load_domain_context를 조합
  - 테이블명/컬럼명 유사도 기반 관련 스키마 필터링
  - FK/관계 정보 자동 탐지 (information_schema 활용)
- **난이도**: 중
- **예상 도구 수**: 2개

#### 3. 쿼리 북마크 고도화 (`query_management`)
- **설명**: 기존 save_query/list_saved_queries를 태그, 검색, 설명, 파라미터화된 쿼리로 확장
- **동기**: 저장된 쿼리가 늘어날수록 관리가 어려워짐. 팀 공유나 재사용이 불편
- **구현 범위**:
  - `save_query` 확장: tags, description, parameters 필드 추가
  - `search_saved_queries(keyword, tags)` — 키워드/태그 기반 검색
  - `run_saved_query(query_id, params)` — 파라미터 바인딩 후 실행
  - `delete_saved_query(query_id)` — 쿼리 삭제
- **난이도**: 하
- **예상 도구 수**: 3개 (기존 2개 확장 + 신규 1개)

---

### P1 (중요) — 분석 생산성 향상

#### 4. 멀티 소스 조인 쿼리 (`cross_source_query`)
- **설명**: 서로 다른 데이터 소스(DB + 파일, DB + DB)의 데이터를 DuckDB를 통해 조인 쿼리
- **동기**: 실무에서 DB 데이터와 Excel 매핑 테이블을 조인하는 케이스가 빈번
- **구현 범위**:
  - `cross_query(sources, sql)` — sources에 conn_id/file_id 목록, DuckDB에 임시 테이블로 로드 후 조인 SQL 실행
  - DB 데이터는 SELECT로 가져와 DuckDB 임시 테이블에 삽입
  - 파일 데이터는 기존 파일 레지스트리에서 로드
  - 결과 행 수 제한 유지 (QUERY_LIMIT)
- **난이도**: 상
- **예상 도구 수**: 1개

#### 5. ERD / 테이블 관계 시각화 (`visualize_schema`)
- **설명**: 데이터베이스의 테이블 관계(FK, 참조)를 Mermaid ERD 다이어그램으로 생성
- **동기**: 새로운 DB에 접속했을 때 테이블 간 관계를 빠르게 파악하기 어려움
- **구현 범위**:
  - `visualize_schema(conn_id, tables?)` — information_schema에서 FK 관계 추출, Mermaid ERD 텍스트 생성
  - 선택적으로 특정 테이블만 필터링
  - LLM 클라이언트가 Mermaid를 렌더링할 수 있으므로 텍스트 반환으로 충분
- **난이도**: 중
- **예상 도구 수**: 1개

#### 6. 쿼리 결과 캐싱 (`query_cache`)
- **설명**: 동일한 쿼리의 반복 실행을 방지하는 인메모리 캐시
- **동기**: LLM이 같은 쿼리를 여러 번 실행하는 경우가 많음 (분석 반복, 차트 생성 등)
- **구현 범위**:
  - run_query 내부에 LRU 캐시 레이어 추가
  - `clear_cache(conn_id?)` — 수동 캐시 무효화 도구
  - TTL 기반 자동 만료 (기본 5분)
  - 캐시 히트/미스 통계 반환
- **난이도**: 하
- **예상 도구 수**: 1개

---

### P2 (보너스) — 확장 기능

#### 7. 알림/임계값 모니터링 (`alerts`)
- **설명**: 쿼리 결과가 특정 조건을 충족하면 알림 반환
- **동기**: 정기적인 데이터 모니터링 (매출 급감, 오류율 급증 등)을 자동화
- **구현 범위**:
  - `create_alert(conn_id, sql, condition, message)` — 알림 규칙 등록
  - `check_alerts()` — 등록된 알림 일괄 확인
  - `list_alerts()` / `delete_alert(alert_id)`
  - MCP 서버 특성상 push 불가 → LLM이 주기적으로 check_alerts 호출하는 패턴
- **난이도**: 중
- **예상 도구 수**: 4개

#### 8. 데이터 비교 도구 (`compare_data`)
- **설명**: 두 쿼리 결과 또는 시점 간 데이터 변화를 비교
- **동기**: "지난주 대비 매출이 얼마나 변했는지" 같은 비교 분석이 빈번
- **구현 범위**:
  - `compare_queries(conn_id, sql_a, sql_b, key_columns)` — 두 쿼리 결과의 diff 생성
  - 추가/삭제/변경된 행 요약
  - 수치 컬럼의 변화량/변화율 계산
- **난이도**: 중
- **예상 도구 수**: 1개

#### 9. Snowflake 연결 완성도 검증 및 보강
- **설명**: snowflake-connector-python 의존성은 있지만 connect_db의 Snowflake 경로 완성도 검증
- **동기**: pyproject.toml에 의존성이 있으므로 사용자가 Snowflake를 기대할 수 있음
- **구현 범위**:
  - connect_db Snowflake 분기 코드 검증
  - account, warehouse, schema 파라미터 처리
  - 통합 테스트 추가
- **난이도**: 하
- **예상 도구 수**: 0 (기존 도구 보강)

---

## 구현 로드맵

### Sprint 1 (1주차): 데이터 신뢰성 기반

| 작업 | 도구 | 난이도 | 산출물 |
|------|------|--------|--------|
| 데이터 품질 검증 | validate_data, validate_query_result | 중 | `tools/validation.py` |
| 쿼리 북마크 고도화 | search_saved_queries, run_saved_query, delete_saved_query | 하 | `tools/analysis.py` 확장 |
| 단위 테스트 작성 | - | - | `tests/unit/test_validation.py` |

### Sprint 2 (2주차): 분석 생산성

| 작업 | 도구 | 난이도 | 산출물 |
|------|------|--------|--------|
| 스키마 컨텍스트 자동 주입 | get_context_for_question, get_table_relationships | 중 | `tools/context.py` |
| 쿼리 결과 캐싱 | clear_cache (+ run_query 내부 캐시) | 하 | `tools/db.py` 수정 |
| 단위 테스트 작성 | - | - | `tests/unit/test_context.py`, `test_cache.py` |

### Sprint 3 (3주차): 크로스 소스 및 시각화

| 작업 | 도구 | 난이도 | 산출물 |
|------|------|--------|--------|
| 멀티 소스 조인 | cross_query | 상 | `tools/cross_source.py` |
| ERD 시각화 | visualize_schema | 중 | `tools/schema_viz.py` |
| Snowflake 검증 | - | 하 | `tools/db.py` 보강 |
| 단위 테스트 작성 | - | - | `tests/unit/test_cross_source.py` 등 |

### Sprint 4 (4주차): 확장 기능 + 안정화

| 작업 | 도구 | 난이도 | 산출물 |
|------|------|--------|--------|
| 알림 모니터링 (P2) | create_alert, check_alerts, list_alerts, delete_alert | 중 | `tools/alerts.py` |
| 데이터 비교 (P2) | compare_queries | 중 | `tools/compare.py` |
| 통합 테스트 + 커버리지 85% 목표 | - | - | `tests/` 전체 보강 |
| README 업데이트 | - | - | README.md |

---

## 성공 지표

| 지표 | 목표 |
|------|------|
| **총 MCP 도구 수** | 25 → 35+ |
| **테스트 커버리지** | 80% → 85% |
| **단위 테스트 수** | 303 → 450+ |
| **P0 기능 완료** | 3/3 (품질 검증, 스키마 컨텍스트, 쿼리 관리) |
| **P1 기능 완료** | 3/3 (크로스 소스, ERD, 캐싱) |
| **P2 기능 완료** | 2/3 이상 |
| **db.py 커버리지** | 51% → 65% |
| **신규 파일 모듈 커버리지** | 각 90% 이상 |

---

## 기술 원칙

1. **SELECT-only 원칙 유지** — 모든 신규 도구도 읽기 전용
2. **QUERY_LIMIT 적용** — 크로스 소스 조인 포함 모든 쿼리에 행 수 제한
3. **기존 아키텍처 준수** — tools/ 디렉토리에 모듈 추가, server.py에 등록
4. **테스트 우선** — 신규 도구는 반드시 단위 테스트 동반 (커버리지 게이트 유지)
5. **의존성 최소화** — 가능한 한 기존 의존성(DuckDB, pandas) 활용, 새 패키지 추가 최소화
