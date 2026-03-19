# bi-agent MCP 서버 구현 계획

> 버전: 0.1 | 작성일: 2026-03-18 | 상태: ✅ 구현 완료 (2026-03-19)
> 기반 문서: [DESIGN.md](./DESIGN.md)

---

## 목차

1. [역할 분담](#1-역할-분담)
2. [구현 순서 및 의존성 그래프](#2-구현-순서-및-의존성-그래프)
3. [태스크 목록](#3-태스크-목록)
4. [인터페이스 계약](#4-인터페이스-계약)
5. [파일 구조 및 생성 책임](#5-파일-구조-및-생성-책임)
6. [검증 체크리스트](#6-검증-체크리스트)
7. [주의사항 및 컨벤션](#7-주의사항-및-컨벤션)

---

## 1. 역할 분담

### Claude Code (이 세션)

**전문 영역: 인프라 · 보안 · 핵심 DB 레이어**

| 태스크 # | 작업 | 버전 |
|----------|------|------|
| #1 | 프로젝트 기반 구조 (pyproject.toml, server.py, config.py) | v0 |
| #2 | auth/credentials.py — OS 키체인 + 환경변수 자격증명 관리 | v0 |
| #3 | auth/oauth.py — Google OAuth 2.0 PKCE 흐름 | v0 |
| #4 | tools/db.py — connect_db, list_connections, get_schema, run_query, profile_table | v0 |
| #9 | docs/IMPLEMENTATION_PLAN.md (이 문서) | - |

**근거:** postgres_mcp.py의 패턴과 backend/core/tools.py의 DB 로직을 가장 잘 파악하고 있으며, 보안 모델(SELECT 전용, 자격증명 격리)의 설계 의도를 구현에 직접 반영할 수 있음.

---

### antigravity

**전문 영역: 외부 서비스 연동 · 아웃풋 생성**

| 태스크 # | 작업 | 버전 | 의존 |
|----------|------|------|------|
| #5 | tools/ga4.py — connect_ga4, get_ga4_report | v1 | #2, #3 완료 후 |
| #6 | tools/amplitude.py — connect_amplitude, get_amplitude_events | v1 | #2 완료 후 |
| #7 | tools/analysis.py — suggest_analysis, generate_report, save_query, list_saved_queries | v1-v2 | #4 완료 후 |
| #8 | tools/tableau.py — generate_twbx | v2 | #4 완료 후 |

**근거:** GA4 Data API, Amplitude REST API 등 외부 서비스 통합과 Tableau XML 구조에 대한 전문성 활용. backend/agents/bi_tool/ 의 기존 Tableau 엔진 재사용에 익숙함.

---

## 2. 구현 순서 및 의존성 그래프

```
[Phase 0] 인프라 (Claude Code 단독)
┌─────────────────────────────────────────────────────┐
│  #1 프로젝트 구조                                    │
│   ├── bi_agent_mcp/__init__.py                      │
│   ├── bi_agent_mcp/server.py (스켈레톤)             │
│   ├── bi_agent_mcp/config.py                        │
│   └── pyproject.toml                                │
└──────────────────┬──────────────────────────────────┘
                   │ (완료 후 병렬 진행)
         ┌─────────┴──────────┐
         ▼                    ▼
  #2 credentials.py      #4 tools/db.py
  (키체인 + 환경변수)    (DB 5종 도구)
         │
         ▼
  #3 oauth.py
  (PKCE 흐름)

[Phase 1] 외부 연동 (antigravity — #2,#3 완료 후)
┌─────────────────────────────────────────────────────┐
│  #5 ga4.py          ← auth/oauth.py, credentials.py │
│  #6 amplitude.py    ← auth/credentials.py           │
│  #7 analysis.py     ← tools/db.py 패턴 참조         │
└─────────────────────────────────────────────────────┘

[Phase 2] 아웃풋 생성 (antigravity — #4 완료 후)
┌─────────────────────────────────────────────────────┐
│  #8 tableau.py      ← TableauMetadataEngine 재사용  │
└─────────────────────────────────────────────────────┘

[완료] server.py에 모든 tool 등록
```

**병렬 가능한 작업:**
- `#2 credentials.py` + `#4 tools/db.py` → 동시 진행 가능
- `#5 ga4.py` + `#6 amplitude.py` → 동시 진행 가능

---

## 3. 태스크 목록

### Claude Code 담당

#### Task #1: 프로젝트 기반 구조

**생성 파일:**

```
bi_agent_mcp/
├── __init__.py
├── __main__.py             ← 필수: `python -m bi_agent_mcp` 진입점
├── server.py
├── config.py
└── tools/
    └── __init__.py
└── auth/
    └── __init__.py
pyproject.toml
```

**pyproject.toml 핵심 의존성:**
```toml
[project]
name = "bi-agent-mcp"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.0",               # from mcp.server.fastmcp import FastMCP (기존 codebase 통일)
    "psycopg2-binary>=2.9",
    "pymysql>=1.1",
    "keyring>=24.0",          # auth/credentials.py
    "google-auth>=2.0",       # v1
    "google-auth-oauthlib>=1.0",  # v1
    "google-analytics-data>=0.18", # v1 GA4
    "defusedxml>=0.7",        # v2 Tableau
    "httpx>=0.25",            # v1 Amplitude
]
```

**server.py 스켈레톤 패턴** (postgres_mcp.py 참조):
```python
from mcp.server.fastmcp import FastMCP  # 기존 backend/mcp_servers/ 패턴과 통일
from bi_agent_mcp.tools.db import connect_db, list_connections, get_schema, run_query, profile_table

mcp = FastMCP("bi-agent")

# v0 tools — @mcp.tool() 데코레이터 또는 mcp.tool()(fn) 둘 다 동작, 데코레이터 권장
@mcp.tool()
def _connect_db_tool(*args, **kwargs): return connect_db(*args, **kwargs)
# 또는 직접 등록: mcp.tool()(connect_db)
mcp.tool()(run_query)
mcp.tool()(profile_table)

# v1 tools (antigravity 구현 후 등록)
# mcp.tool()(connect_ga4)
# ...

if __name__ == "__main__":
    mcp.run()
```

---

#### Task #2: auth/credentials.py

**공개 인터페이스 (antigravity가 사용):**

```python
def store_secret(service: str, key: str, value: str) -> None:
    """OS 키체인에 비밀 저장. service="bi-agent", key="ga4_property_id"."""

def get_secret(service: str, key: str) -> Optional[str]:
    """OS 키체인에서 비밀 조회. 없으면 None."""

def get_env_or_secret(env_var: str, service: str, key: str) -> Optional[str]:
    """환경변수 우선 → 키체인 폴백."""

def mask_password(value: str) -> str:
    """비밀번호를 ****로 마스킹. list_connections 출력용."""
```

**구현 전략:**
- `keyring` 패키지 사용 (macOS/Linux/Windows 자동 선택)
- `keyring` 미설치 환경: 메모리 fallback (경고 로그)
- 로그에 절대 비밀값 출력 금지

---

#### Task #3: auth/oauth.py

> **재사용 원본:** `backend/orchestrator/managers/oauth_handler.py` (262줄, 완전 구현됨)
> PKCE 쌍 생성, 로컬 콜백 서버, token 교환, refresh 로직이 이미 구현되어 있음.
> 변경 필요 사항: credentials.json 파일 저장 → `credentials.store_secret()` OS 키체인으로 교체.

**공개 인터페이스 (ga4.py가 사용):**

```python
def run_oauth_flow(
    client_id: str,
    client_secret: str,
    scopes: List[str],
    service_name: str,
) -> google.oauth2.credentials.Credentials:
    """
    PKCE OAuth 2.0 흐름 실행. (oauth_handler.py의 google_oauth_login() 어댑터)
    1. code_verifier / code_challenge 생성
    2. 브라우저 열기
    3. localhost:8765/callback 에서 code 수신
    4. token 교환 → credentials 반환
    refresh_token은 credentials.store_secret()으로 저장.
    """

def get_credentials(service_name: str) -> Optional[google.oauth2.credentials.Credentials]:
    """저장된 refresh_token으로 credentials 복원."""
```

**포트 전략:** 8765 → 실패 시 8766, 8767 순서로 시도.

---

#### Task #4: tools/db.py

**연결 레지스트리:** 모듈 레벨 `dict` (서버 재시작 시 초기화)

```python
# 모듈 레벨 상태
_connections: Dict[str, ConnectionInfo] = {}

@dataclass
class ConnectionInfo:
    conn_id: str
    db_type: str   # "postgresql" | "mysql"
    host: str
    port: int
    database: str
    user: str
    password: str  # 메모리에만 보관
```

**SELECT 안전장치** (DESIGN.md 6절 참조):
```python
BLOCKED_KEYWORDS = {"DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "TRUNCATE"}

def _validate_select(sql: str) -> Optional[str]:
    """None=통과, str=거부 사유."""
    upper = sql.strip().upper()
    if not upper.startswith("SELECT"):
        return "보안 위반: SELECT 쿼리만 실행할 수 있습니다."
    for kw in BLOCKED_KEYWORDS:
        if kw in upper:
            return f"보안 위반: {kw} 키워드는 허용되지 않습니다."
    return None
```

**backend/core/tools.py 재사용 대상:**
- `query_database()` → `run_query()` 로직
- `analyze_schema()` → `get_schema()` 로직
- `list_connections()` → 패턴 참조

---

### antigravity 담당

#### Task #5: tools/ga4.py

**의존:** auth/oauth.py, auth/credentials.py (Task #2, #3 완료 필요)

```python
# 연결 레지스트리 (tools/db.py와 동일 패턴)
_ga4_connections: Dict[str, GA4ConnectionInfo] = {}

def connect_ga4(property_id: str) -> str:
    """
    1. get_credentials("ga4_{property_id}") 시도
    2. 없으면 run_oauth_flow() 호출
    3. _ga4_connections에 등록
    반환: "GA4 연결 완료: ga4_{property_id}\n  속성: ...\n  계정: ..."
    """

def get_ga4_report(
    property_id: str,
    metrics: List[str],
    dimensions: Optional[List[str]],
    date_range: Dict[str, str],
) -> str:
    """
    Google Analytics Data API v1 호출.
    google-analytics-data 패키지 사용.
    반환: 마크다운 테이블.
    """
```

**필요한 OAuth 스코프:**
```python
GA4_SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]
```

---

#### Task #6: tools/amplitude.py

**의존:** auth/credentials.py (Task #2 완료 필요)

```python
_amplitude_connections: Dict[str, AmplitudeConnectionInfo] = {}

def connect_amplitude(api_key: str, secret_key: str) -> str:
    """
    자격증명 메모리 등록 + env var 저장 안내.
    연결 테스트: GET /2/events/types 엔드포인트.
    """

def get_amplitude_events(
    event_name: str,
    date_range: Dict[str, str],
    filters: Optional[Dict] = None,
) -> str:
    """
    Amplitude Export API 또는 Dashboard REST API 호출.
    httpx 사용. Basic Auth (api_key:secret_key).
    반환: 마크다운 테이블.
    """
```

**Amplitude API 엔드포인트:**
- Export API: `https://amplitude.com/api/2/export`
- User Activity: `https://amplitude.com/api/2/useractivity`

---

#### Task #7: tools/analysis.py

**의존:** tools/db.py 패턴 참조 (Task #4 완료 필요)

```python
# 쿼리 저장소 위치
QUERIES_PATH = Path.home() / ".bi_agent" / "queries.json"

def suggest_analysis(data_context: str, question: str) -> str:
    """
    LLM 호출 없음. 규칙 기반 분석 방향 제안 텍스트 생성.
    템플릿: 정의 → 지표 → 비교 → 다음 단계 쿼리 초안.
    """

def generate_report(sections: List[Dict]) -> str:
    """
    sections: [{"title": str, "content": str, "data": str}]
    마크다운 .md 파일 생성 → ~/Downloads/{timestamp}_report.md
    반환: 파일 경로 + 섹션 요약.
    """

def save_query(name: str, sql: str, connection_id: str) -> str:
    """QUERIES_PATH JSON에 저장."""

def list_saved_queries() -> str:
    """QUERIES_PATH에서 읽어 마크다운 목록 반환."""
```

---

#### Task #8: tools/tableau.py

**의존:** tools/db.py (마크다운 결과 파싱, Task #4 완료 필요)

```python
def generate_twbx(
    query_result: str,   # run_query() 반환값 (마크다운 테이블)
    chart_type: str,     # "bar" | "line" | "scatter" | "heatmap"
    title: str,
) -> str:
    """
    1. 마크다운 테이블 파싱 → 데이터 추출
    2. TableauMetadataEngine (backend/agents/bi_tool/tableau_metadata.py) 재사용
    3. .twb XML 생성 (defusedxml)
    4. zipfile로 .twbx 패키징
    5. ~/Downloads/{title}.twbx 저장
    반환: 파일 경로 + 메타 정보.
    """
```

**재사용 경로:**
```
backend/agents/bi_tool/tableau_metadata.py   → TableauMetadataEngine
backend/agents/bi_tool/tableau_meta_schema.py → TableauMetaSchemaEngine
```

---

## 4. 인터페이스 계약

### auth 모듈 → tools 모듈

```python
# antigravity가 사용하는 credentials.py API
from bi_agent_mcp.auth.credentials import store_secret, get_secret, get_env_or_secret

# antigravity가 사용하는 oauth.py API
from bi_agent_mcp.auth.oauth import run_oauth_flow, get_credentials
```

### ConnectionInfo 공유 객체 (db.py → server.py)

```python
# tools/db.py에서 export
def get_connection(conn_id: str) -> Optional[ConnectionInfo]:
    """server.py 또는 다른 tool에서 연결 정보 조회용."""
```

### 마크다운 테이블 포맷 규약

모든 tool의 테이블 출력은 다음 형식을 따름:

```
**N건 반환** (SQL: `{query_preview}`)

| col1 | col2 | col3 |
| ---  | ---  | ---  |
| val1 | val2 | val3 |
...
(총 N건 중 M건 표시)
```

`generate_twbx`의 `query_result` 파라미터는 이 형식을 입력으로 받음.

### 에러 반환 규약

모든 tool은 에러 시 다음 형식으로 반환:

```python
# 사용자 에러 (잘못된 입력)
return f"[ERROR] {구체적 메시지}"

# 시스템 에러 (DB 연결 실패 등)
return f"[ERROR] {operation} 실패: {str(e)}"
```

---

## 5. 파일 구조 및 생성 책임

```
bi_agent_mcp/                   ← Task #1 (Claude Code)
├── __init__.py                 ← Task #1
├── server.py                   ← Task #1 (v0 tools 등록)
├── config.py                   ← Task #1
│
├── auth/                       ← Claude Code 전담
│   ├── __init__.py             ← Task #1
│   ├── credentials.py          ← Task #2
│   └── oauth.py                ← Task #3
│
└── tools/
    ├── __init__.py             ← Task #1
    ├── db.py                   ← Task #4 (Claude Code)
    ├── ga4.py                  ← Task #5 (antigravity)
    ├── amplitude.py            ← Task #6 (antigravity)
    ├── analysis.py             ← Task #7 (antigravity)
    └── tableau.py              ← Task #8 (antigravity)

pyproject.toml                  ← Task #1 (Claude Code)
README.md                       ← 별도 작업
docs/
├── DESIGN.md                   ← 읽기 전용 (설계 기준)
└── IMPLEMENTATION_PLAN.md      ← Task #9 (이 문서, Claude Code)
```

---

## 6. 검증 체크리스트

### v0 검증 (Claude Code 완료 후)

- [ ] `pip install -e .` 로 설치 가능
- [ ] `python -m bi_agent_mcp` 실행 시 MCP 서버 시작
- [ ] Claude Desktop에서 `list_connections` 호출 → 빈 목록 반환
- [ ] `connect_db(type="postgresql", ...)` → `conn_abc123` ID 반환
- [ ] `get_schema("conn_abc123")` → 테이블 목록 반환
- [ ] `get_schema("conn_abc123", "orders")` → 컬럼 + 샘플 반환
- [ ] `run_query("conn_abc123", "SELECT 1")` → 결과 반환
- [ ] `run_query("conn_abc123", "DELETE FROM ...")` → 거부 메시지 반환
- [ ] `profile_table("conn_abc123", "orders")` → NULL비율/유니크 등 반환
- [ ] OS 키체인에 비밀 저장/조회 동작 확인

### v0 E2E 통합 시나리오 (Phase 4)

실제 PostgreSQL 연결 기준 종단간 흐름 검증:

```
1. connect_db("postgresql", "localhost", 5432, "testdb", "user", "pass")
   → "연결 등록 완료: conn_xxxx"
2. list_connections()
   → conn_xxxx 항목 포함, 비밀번호 **** 마스킹 확인
3. get_schema("conn_xxxx")
   → 전체 테이블 목록 반환
4. get_schema("conn_xxxx", "some_table")
   → 컬럼 + 샘플 2행 반환
5. run_query("conn_xxxx", "SELECT * FROM some_table LIMIT 5")
   → 마크다운 테이블 반환
6. run_query("conn_xxxx", "DELETE FROM some_table")
   → "[ERROR] 보안 위반" 반환 확인
7. profile_table("conn_xxxx", "some_table")
   → NULL비율/유니크/min/max 반환
```

### v1 검증 (antigravity 완료 후)

- [ ] `connect_ga4("123456789")` → 브라우저 열림 → 인증 후 성공 메시지
- [ ] `get_ga4_report(...)` → 마크다운 테이블 반환
- [ ] `connect_amplitude(api_key, secret_key)` → 연결 성공 메시지
- [ ] `get_amplitude_events(...)` → 이벤트 데이터 반환
- [ ] `suggest_analysis(...)` → 분석 방향 텍스트 반환
- [ ] `save_query("daily_orders", "SELECT ...", "conn_abc123")` → 저장 확인
- [ ] `list_saved_queries()` → 저장된 쿼리 목록 반환

### v2 검증 (antigravity 완료 후)

- [ ] `generate_twbx(query_result, "bar", "월별 매출")` → .twbx 파일 생성
- [ ] Tableau Desktop에서 생성된 .twbx 열기 성공
- [ ] `generate_report([...])` → .md 파일 생성

---

## 7. 주의사항 및 컨벤션

### 보안

- **절대 금지:** 비밀번호/토큰을 로그 출력, 소스코드 하드코딩, 디스크 평문 저장
- `list_connections` 응답에서 password는 항상 `****` 마스킹
- `run_query` LIMIT 강제 적용: `SELECT * FROM ({sql}) AS sub LIMIT {QUERY_LIMIT}`
- 위험 키워드 체크: 대소문자 무관 (`sql.upper()` 로 체크)

### 코드 스타일

- 모든 tool 함수는 `str` 반환 (MCP 규약)
- 타입 힌트 필수 (파라미터 + 반환값)
- docstring 필수 (LLM이 tool 선택에 사용)
- 에러는 exception raise 금지 → 에러 문자열 반환

### postgres_mcp.py 패턴 준수

```python
# ✅ 올바른 패턴
mcp = FastMCP("bi-agent")
mcp.tool()(function_name)
mcp.run()  # stdio 모드

# ❌ 잘못된 패턴
@mcp.tool()  # 데코레이터 직접 사용 대신 mcp.tool()(fn) 권장
```

### 커밋 규약

```
feat(v0): tools/db.py — connect_db, get_schema 구현
feat(v1): tools/ga4.py — GA4 OAuth 연동 구현 (antigravity)
fix: run_query LIMIT 강제 적용 버그 수정
```

---

## 진행 상황

| 태스크 | 담당 | 상태 | 완료일 |
|--------|------|------|--------|
| #1 프로젝트 구조 | Claude Code | ✅ 완료 | 2026-03-18 |
| #2 credentials.py | Claude Code | ✅ 완료 | 2026-03-18 |
| #3 oauth.py | Claude Code | ✅ 완료 | 2026-03-18 |
| #4 tools/db.py | Claude Code | ✅ 완료 | 2026-03-18 |
| #5 tools/ga4.py | antigravity | ✅ 완료 | 2026-03-18 |
| #6 tools/amplitude.py | antigravity | ✅ 완료 | 2026-03-18 |
| #7 tools/analysis.py | antigravity | ✅ 완료 | 2026-03-18 |
| #8 tools/tableau.py | antigravity | ✅ 완료 | 2026-03-18 |
| #9 IMPLEMENTATION_PLAN.md | Claude Code | ✅ 완료 | 2026-03-18 |

---

*구현 중 발견된 제약이나 변경사항은 이 문서와 DESIGN.md에 함께 반영한다.*
