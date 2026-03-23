# bi-agent-mcp 상세 설계 (DETAILED_SPEC.md)

> [ 🗺️ 전략/로드맵 (PLAN)](./PLAN.md) · **[ 🛠️ 상세 설계 ]** · [ 📋 현재 실행 (TODO)](./TODO.md) · [ 📜 변경 이력 (CHANGELOG)](./CHANGELOG.md)

---

**최종 수정:** 2026-03-20 (Phase 1 완료 반영)

---

## 1. 패키지 구조

```
bi_agent_mcp/
├── server.py              # FastMCP 인스턴스, tool 등록, 진입점
├── config.py              # 환경 변수, 상수 (QUERY_LIMIT, BQ_MAX_BYTES_BILLED 등)
├── setup_cli.py           # bi-agent-mcp-setup CLI 진입점
├── auth/
│   └── credentials.py     # mask_password 등 인증 헬퍼
├── config_manager.py      # ConfigManager — config.json + OS keyring 통합
└── tools/
    ├── db.py              # DB 연결 및 쿼리 도구 (PostgreSQL/MySQL/BigQuery/Snowflake)
    ├── files.py           # 파일 데이터 소스 도구 (CSV/Excel, DuckDB 기반)
    ├── ga4.py             # Google Analytics 4 도구
    ├── amplitude.py       # Amplitude 이벤트 도구
    ├── analysis.py        # 분석 및 리포트 도구
    ├── tableau.py         # Tableau TWBX 생성 도구
    └── setup.py           # 설정 관련 도구
```

---

## 2. 전체 MCP 도구 목록

| 그룹 | 도구명 | 설명 |
| --- | --- | --- |
| **v0 File Tools** | `connect_file` | CSV/XLSX/XLS 파일 로드, file_id 반환 |
| | `list_files` | 로드된 파일 목록 조회 |
| | `query_file` | DuckDB 기반 SELECT SQL 실행 |
| | `get_file_schema` | 컬럼 정보(타입, NULL수, 샘플값) 조회 |
| **v0 DB Tools** | `connect_db` | PostgreSQL/MySQL/BigQuery/Snowflake 연결, conn_id 반환 |
| | `list_connections` | 등록된 연결 목록 조회 |
| | `get_schema` | 테이블 목록 또는 컬럼·샘플 조회 |
| | `run_query` | SELECT 쿼리 실행, 마크다운 테이블 반환 |
| | `profile_table` | 컬럼별 NULL%, 유니크수, min/max 분석 |
| **v1 External** | `connect_ga4` | Google Analytics 4 연결 |
| | `get_ga4_report` | GA4 리포트 조회 |
| | `connect_amplitude` | Amplitude 연결 |
| | `get_amplitude_events` | Amplitude 이벤트 데이터 조회 |
| **v1-v2 Analysis** | `suggest_analysis` | 컨텍스트 기반 분석 제안 (question 파라미터, context/ 자동 탐색) |
| | `generate_report` | 분석 리포트 생성 |
| | `save_query` | 쿼리 저장 |
| | `list_saved_queries` | 저장된 쿼리 목록 조회 |
| | `load_domain_context` | context/ 마크다운 파일 로드, MCP 컨텍스트 주입 |
| | `list_query_history` | 쿼리 실행 이력 조회 (~/.config/bi-agent/query_history.json) |
| **v2 Output** | `generate_twbx` | Tableau TWBX 파일 생성 |
| **Setup** | `check_setup_status` | 설정 상태 확인 |
| | `configure_datasource` | 데이터 소스 설정 |
| | `test_datasource` | 데이터 소스 연결 테스트 |

**현재 등록된 도구 수: 21개**

---

## 3. 연결 영속성 설계

연결 정보는 서버 재시작 후에도 유지됩니다.

- **저장 경로:** `~/.config/bi-agent/connections.json`
- **저장 항목:** conn_id, db_type, host, port, database, user, project_id, dataset, account, warehouse, schema_ (비밀번호 제외)
- **복원:** `_load_connections()` — 모듈 임포트 시 자동 실행, `persisted=True` 플래그 설정
- `list_connections()` 결과에 "(저장됨)" 상태 표시

```json
{
  "conn_abc12345": {
    "conn_id": "conn_abc12345",
    "db_type": "postgresql",
    "host": "localhost",
    "port": 5432,
    "database": "mydb",
    "user": "analyst",
    "project_id": "",
    "dataset": "",
    "account": "",
    "warehouse": "",
    "schema_": ""
  }
}
```

---

## 4. 보안 아키텍처

### SELECT 전용 쿼리 검증

`_validate_select(sql)` — `run_query`, `query_file` 양쪽에 적용:
- SQL이 `SELECT`로 시작하지 않으면 거부
- `DROP`, `DELETE`, `INSERT`, `UPDATE`, `ALTER`, `CREATE`, `TRUNCATE` 키워드 포함 시 거부

### 식별자 검증

`_validate_identifier(name)` — 테이블명/컬럼명에 적용:
- 정규식 `^[a-zA-Z_][a-zA-Z0-9_$.]*$` 통과 시에만 허용
- SQL Injection 방어

### 테이블 존재 검증

`_validate_table_name(cur, table_name, db_type)`:
- `information_schema.tables` 파라미터 바인딩으로 실제 존재 여부 확인
- 존재하지 않으면 존재하는 테이블 목록과 함께 오류 반환

### 비밀번호 격리

- 비밀번호는 메모리(ConnectionInfo.password)에만 보관
- `connections.json`에 저장하지 않음
- `mask_password()` 유틸리티로 로그 출력 시 마스킹

---

## 5. ConfigManager

`bi_agent_mcp/config_manager.py`

비밀이 아닌 설정은 `~/.config/bi-agent/config.json`에, 비밀(API 키, 비밀번호)은 OS keyring에 저장하는 통합 설정 관리 계층입니다.

| 저장소 | 저장 항목 |
| --- | --- |
| `config.json` | 기본 DB 타입, BQ 프로젝트 ID, 기본 설정 등 비밀이 아닌 값 |
| OS keyring | API 키, 비밀번호 등 민감한 자격증명 |

---

## 6. 지원 데이터 소스

| 데이터 소스 | 연결 방식 | 도구 |
| --- | --- | --- |
| PostgreSQL | psycopg2-binary | `connect_db(db_type="postgresql", ...)` |
| MySQL | pymysql | `connect_db(db_type="mysql", ...)` |
| BigQuery | google-cloud-bigquery | `connect_db(db_type="bigquery", project_id=..., dataset=...)` |
| Snowflake | snowflake-connector-python | `connect_db(db_type="snowflake", account=..., warehouse=...)` |
| CSV | pandas + duckdb | `connect_file(path="data.csv")` |
| Excel (.xlsx/.xls) | pandas + openpyxl + duckdb | `connect_file(path="data.xlsx", sheet=...)` |

---

## 7. 비즈니스 도메인 지식 시스템 (`context/`)

`context/` 디렉토리는 사용자가 자신의 비즈니스 도메인 지식을 마크다운 파일로 작성해두면, MCP 서버가 이를 읽어 AI 분석 품질을 자동으로 높이는 시스템입니다.

| 파일명 | 내용 | 우선순위 |
| --- | --- | --- |
| `README.md` | 도메인 지식 시스템 사용 가이드 | — |
| `01_business_context.md` | 회사/팀/사업 개요, 핵심 목표 | 높음 |
| `02_data_sources.md` | 데이터 소스 및 테이블 설명, 관계 | 높음 |
| `03_kpi_dictionary.md` | KPI/지표 정의 사전 (SQL 포함) | 높음 |
| `04_analysis_patterns.md` | 트렌드/코호트/퍼널/RFM 분석 패턴 라이브러리 | 중간 |
| `05_glossary.md` | 비즈니스 용어사전 및 약어 사전 | 중간 |

### `load_domain_context` MCP 도구와의 연동

- `load_domain_context(sections=["all"])` 호출 시 context/ 디렉토리의 마크다운 파일을 읽어 MCP 컨텍스트로 주입
- `sections` 파라미터로 특정 파일만 선택 로드 가능 (예: `["kpi", "glossary"]`)
- `suggest_analysis` 호출 시 context/ 디렉토리를 자동 탐색하여 도메인 맥락 반영

---

## 8. BI 스킬 시스템 (`.claude/commands/`)

Claude Code 슬래시 커맨드로 등록된 BI 워크플로우 스킬입니다. MCP 도구 + 도메인 지식 + 재사용 가능한 프롬프트 패턴을 결합하여 반복 작업을 자동화합니다.

| 커맨드 | 목적 | 사용 MCP 도구 |
| --- | --- | --- |
| `/bi-connect` | 데이터 소스 연결 + 도메인 컨텍스트 로드 | `connect_db`, `connect_file`, `load_domain_context` |
| `/bi-explore` | 도메인 맥락 기반 데이터 탐색 및 비즈니스 언어 설명 | `get_schema`, `profile_table`, `load_domain_context` |
| `/bi-analyze` | 도메인 인식 기반 심층 분석 + 경영진 수준 보고서 | `run_query`, `suggest_analysis`, `generate_report` |
| `/bi-report` | KPI 정의 기반 정기 리포트 자동 생성 | `load_domain_context`, `run_query`, `generate_report` |
| `/bi-domain` | 도메인 컨텍스트 현황 확인 및 완성도 점수 | `load_domain_context` |

### 결합 구조

```
MCP 도구 (데이터 접근)
    +
도메인 지식 (context/ 마크다운)
    +
BI 스킬 (.claude/commands/ 슬래시 커맨드)
    =
개인화된 BI 분석 워크플로우
```

---

Copyright © 2026 BI-Agent Team. All rights reserved.
