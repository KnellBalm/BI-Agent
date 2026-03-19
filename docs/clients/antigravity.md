# Antigravity에서 bi-agent 사용하기

bi-agent MCP 서버를 Antigravity LLM 클라이언트에 연결하는 방법을 안내합니다.

> **Antigravity**는 AI 기반 코딩 어시스턴트로서 MCP(Model Context Protocol)를 지원하는 현대적인 LLM 클라이언트입니다. bi-agent를 Antigravity에 연결하면 자연어로 데이터 조회, 쿼리 작성, 분석 보고서 생성 등 BI 작업을 수행할 수 있습니다.

---

## 목차

1. [사전 준비](#사전-준비)
2. [설치](#설치)
3. [Antigravity MCP 서버 등록](#antigravity-mcp-서버-등록)
4. [환경 변수 설정](#환경-변수-설정)
5. [연결 테스트](#연결-테스트)
6. [지원 기능](#지원-기능)
7. [트러블슈팅](#트러블슈팅)

---

## 사전 준비

### 필수 요구사항

- **Python 3.11 이상** (설치 확인: `python --version`)
- **Antigravity** (최신 버전 설치)
- 데이터베이스 접근 권한 (PostgreSQL, MySQL, BigQuery 중 하나 이상)

### 선택 사항

- **Google 계정** (GA4 데이터 조회 시 필요)
- **Amplitude API 키** (Amplitude 데이터 조회 시 필요)

---

## 설치

### 1단계: Python 가상환경 생성 (권장)

```bash
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
# 또는
.venv\Scripts\activate           # Windows
```

### 2단계: bi-agent-mcp 설치

```bash
pip install bi-agent-mcp
```

설치 확인:

```bash
python -m bi_agent_mcp --version
```

---

## Antigravity MCP 서버 등록

### Antigravity 설정 파일 위치

Antigravity는 MCP 서버 설정을 다음 경로에서 읽습니다:

- **macOS / Linux**: `~/.gemini/antigravity/mcp_config.json`

설정 디렉토리가 없으면 생성하세요:

```bash
mkdir -p ~/.gemini/antigravity
```

### 설정 파일 작성

`~/.gemini/antigravity/mcp_config.json` 파일을 열고 `mcpServers` 객체에 `bi-agent` 항목을 추가합니다.

**새로 파일을 생성하는 경우:**

```json
{
  "mcpServers": {
    "bi-agent": {
      "command": "python",
      "args": ["-m", "bi_agent_mcp"],
      "env": {
        "BI_AGENT_PG_HOST": "db.company.com",
        "BI_AGENT_PG_PORT": "5432",
        "BI_AGENT_PG_DBNAME": "analytics",
        "BI_AGENT_PG_USER": "bi_agent_user",
        "BI_AGENT_PG_PASSWORD": "your_postgres_password"
      }
    }
  }
}
```

**이미 다른 MCP 서버가 등록된 경우:**

기존 `mcp_config.json`의 `mcpServers` 객체에 `"bi-agent"` 항목을 추가합니다:

```json
{
  "mcpServers": {
    "기존-서버": { "...기존 설정..." },
    "bi-agent": {
      "command": "python",
      "args": ["-m", "bi_agent_mcp"],
      "env": {
        "BI_AGENT_PG_HOST": "db.company.com",
        "BI_AGENT_PG_DBNAME": "analytics",
        "BI_AGENT_PG_USER": "bi_agent_user",
        "BI_AGENT_PG_PASSWORD": "your_password"
      }
    }
  }
}
```

> **팁**: 가상환경을 사용하는 경우 `command`에 가상환경의 Python 경로를 지정하세요:
> ```json
> "command": "/path/to/your/project/.venv/bin/python"
> ```

Antigravity 애플리케이션을 재시작하면 설정이 적용됩니다.

---

## 환경 변수 설정

### PostgreSQL 설정

```json
"env": {
  "BI_AGENT_PG_HOST": "db.company.com",
  "BI_AGENT_PG_PORT": "5432",
  "BI_AGENT_PG_DBNAME": "analytics",
  "BI_AGENT_PG_USER": "bi_agent_user",
  "BI_AGENT_PG_PASSWORD": "your_password"
}
```

### MySQL 설정

```json
"env": {
  "BI_AGENT_MYSQL_HOST": "mysql.company.com",
  "BI_AGENT_MYSQL_PORT": "3306",
  "BI_AGENT_MYSQL_DBNAME": "analytics",
  "BI_AGENT_MYSQL_USER": "bi_agent_user",
  "BI_AGENT_MYSQL_PASSWORD": "your_password"
}
```

### BigQuery 설정

```json
"env": {
  "BI_AGENT_BQ_PROJECT_ID": "my-project-id",
  "BI_AGENT_BQ_DATASET": "analytics",
  "BI_AGENT_BQ_CREDENTIALS_PATH": "/path/to/service-account-key.json"
}
```

> **주의**: Windows에서는 경로에 백슬래시를 사용할 경우 이스케이프 처리하세요: `"C:\\path\\to\\key.json"`

### Amplitude 설정

```json
"env": {
  "BI_AGENT_AMPLITUDE_API_KEY": "your_api_key",
  "BI_AGENT_AMPLITUDE_SECRET_KEY": "your_secret_key"
}
```

### GA4 설정 (OAuth)

```json
"env": {
  "BI_AGENT_GOOGLE_CLIENT_ID": "your_client_id.apps.googleusercontent.com",
  "BI_AGENT_GOOGLE_CLIENT_SECRET": "your_client_secret"
}
```

GA4는 `connect_ga4` 도구 사용 시 브라우저에서 Google 로그인을 통해 권한을 허용합니다.

### 일반 설정

```json
"env": {
  "BI_AGENT_QUERY_LIMIT": "500"
}
```

| 변수명 | 설명 | 기본값 | 필수 |
|--------|------|--------|------|
| `BI_AGENT_PG_HOST` | PostgreSQL 호스트 | `localhost` | N |
| `BI_AGENT_PG_PORT` | PostgreSQL 포트 | `5432` | N |
| `BI_AGENT_PG_DBNAME` | PostgreSQL 데이터베이스명 | - | Y (PG 사용 시) |
| `BI_AGENT_PG_USER` | PostgreSQL 사용자명 | - | Y (PG 사용 시) |
| `BI_AGENT_PG_PASSWORD` | PostgreSQL 비밀번호 | - | Y (PG 사용 시) |
| `BI_AGENT_MYSQL_HOST` | MySQL 호스트 | `localhost` | N |
| `BI_AGENT_MYSQL_PORT` | MySQL 포트 | `3306` | N |
| `BI_AGENT_MYSQL_DBNAME` | MySQL 데이터베이스명 | - | Y (MySQL 사용 시) |
| `BI_AGENT_MYSQL_USER` | MySQL 사용자명 | - | Y (MySQL 사용 시) |
| `BI_AGENT_MYSQL_PASSWORD` | MySQL 비밀번호 | - | Y (MySQL 사용 시) |
| `BI_AGENT_BQ_PROJECT_ID` | BigQuery 프로젝트 ID | - | Y (BQ 사용 시) |
| `BI_AGENT_BQ_DATASET` | BigQuery 데이터셋명 | - | Y (BQ 사용 시) |
| `BI_AGENT_BQ_CREDENTIALS_PATH` | BigQuery 서비스 계정 키 경로 | - | Y (BQ 사용 시) |
| `BI_AGENT_AMPLITUDE_API_KEY` | Amplitude API Key | - | Y (Amplitude 사용 시) |
| `BI_AGENT_AMPLITUDE_SECRET_KEY` | Amplitude Secret Key | - | Y (Amplitude 사용 시) |
| `BI_AGENT_GOOGLE_CLIENT_ID` | Google OAuth Client ID | - | Y (GA4 사용 시) |
| `BI_AGENT_GOOGLE_CLIENT_SECRET` | Google OAuth Client Secret | - | Y (GA4 사용 시) |
| `BI_AGENT_QUERY_LIMIT` | 쿼리 결과 최대 행 수 | `500` | N |

### 보안 권장사항

- **환경 변수 파일 사용**: `.env` 파일로 민감한 정보를 관리하고 `.gitignore`에 추가하세요.
- **읽기 전용 계정**: DB 접속용 사용자는 SELECT 권한만 부여하세요.
  ```sql
  CREATE USER bi_agent_user WITH PASSWORD 'secure_password';
  GRANT SELECT ON ALL TABLES IN SCHEMA public TO bi_agent_user;
  ```
- **토큰 저장**: OAuth 토큰은 자동으로 OS 키체인에 저장되며 설정 파일에 저장되지 않습니다.

---

## 연결 테스트

### 1단계: Antigravity에서 MCP 도구 확인

Antigravity를 열고 채팅창에서 다음과 같이 입력합니다:

```
bi-agent 도구들을 모두 보여줘
```

또는 수동으로 도구 목록 호출:

```
@bi-agent 도구 목록
```

정상적으로 연결되었다면 다음과 같은 도구 목록이 표시됩니다:

```
Available tools:
- connect_db
- list_connections
- get_schema
- run_query
- profile_table
```

### 2단계: DB 연결 테스트

```
@bi-agent orders 테이블의 스키마를 보여줘
```

> **주의**: 먼저 `connect_db` 또는 환경 변수로 DB 연결을 설정해야 합니다.

설정 파일에 이미 PostgreSQL 설정을 했다면, 자동으로 연결되어 스키마가 표시됩니다.

### 3단계: 쿼리 실행 테스트

```
@bi-agent 지난 7일간의 일별 주문 수를 조회해줄래?
```

LLM이 자동으로 적절한 쿼리를 생성하고 실행합니다.

---

## 지원 기능

### v0 — 핵심 DB 기능

| 도구명 | 설명 | 사용 예 |
|--------|------|--------|
| `connect_db` | DB 연결 등록 | `connect_db(type="postgresql", host="db.company.com", ...)` |
| `list_connections` | 등록된 연결 목록 조회 | `list_connections()` |
| `get_schema` | 테이블 스키마 조회 | `get_schema(connection_id="conn_abc", table_name="orders")` |
| `run_query` | SELECT 쿼리 실행 | `run_query(connection_id="conn_abc", sql="SELECT ...")` |
| `profile_table` | 테이블 데이터 프로파일 | `profile_table(connection_id="conn_abc", table_name="orders")` |

**사용 예시:**

```
@bi-agent orders 테이블의 null 비율과 유니크 값 분포를 분석해줘
```

→ `profile_table` 도구가 자동 실행되어 각 컬럼의 데이터 품질 정보를 반환합니다.

### v1 — 외부 데이터 소스 (GA4, Amplitude)

| 도구명 | 설명 | 사용 예 |
|--------|------|--------|
| `connect_ga4` | Google Analytics 4 연결 | `connect_ga4(property_id="123456789")` |
| `get_ga4_report` | GA4 데이터 조회 | `get_ga4_report(property_id="...", metrics=["sessions", ...])` |
| `connect_amplitude` | Amplitude 프로젝트 연결 | `connect_amplitude(api_key="...", secret_key="...")` |
| `get_amplitude_events` | Amplitude 이벤트 조회 | `get_amplitude_events(event_name="purchase_complete", ...)` |
| `suggest_analysis` | 분석 방향 제안 | `suggest_analysis(data_context="...", question="...")` |

**사용 예시:**

```
@bi-agent 지난 30일 GA4 세션 수와 사용자 수를 날짜별로 보여줘
```

→ GA4 API를 통해 데이터를 자동으로 조회합니다.

### v2 — 아웃풋 생성 (Tableau, 보고서)

| 도구명 | 설명 | 사용 예 |
|--------|------|--------|
| `generate_twbx` | Tableau 워크북 초안 생성 | `generate_twbx(query_result="...", chart_type="bar", ...)` |
| `generate_report` | 마크다운 보고서 초안 생성 | `generate_report(sections=[...])` |
| `save_query` | 쿼리 저장 | `save_query(name="daily_orders", sql="...", ...)` |
| `list_saved_queries` | 저장된 쿼리 목록 | `list_saved_queries()` |

**사용 예시:**

```
@bi-agent 월별 매출 추이를 보여주는 Tableau 초안을 만들어줄래?
```

→ `.twbx` 파일이 생성되어 다운로드됩니다.

---

## 트러블슈팅

### 문제: "MCP 서버에 연결할 수 없습니다" 오류

**원인**: Antigravity가 `mcp_config.json` 설정 파일을 찾거나 읽을 수 없음

**해결 방법**:

1. 설정 파일 경로 확인
   ```bash
   cat ~/.gemini/antigravity/mcp_config.json
   ```

2. 파일이 없으면 생성
   ```bash
   mkdir -p ~/.gemini/antigravity
   # 위의 "설정 파일 작성" 섹션 내용을 파일에 작성
   ```

3. JSON 문법 오류 확인 (쉼표, 괄호 등)

4. Antigravity 애플리케이션 재시작

### 문제: "python: command not found" 오류

**원인**: Python이 PATH 환경변수에 없음

**해결 방법**:

1. Python 설치 경로 확인
   ```bash
   which python3        # macOS / Linux
   where python         # Windows
   ```

2. `mcp.json`에서 `python` 대신 전체 경로 사용
   ```json
   "command": "/usr/bin/python3"   # macOS / Linux
   "command": "C:\\Python39\\python.exe"  # Windows
   ```

3. 또는 가상환경의 python 사용
   ```json
   "command": "/Users/yourname/.venv/bin/python"
   ```

### 문제: DB 연결 실패 "연결을 찾을 수 없습니다"

**원인**: 환경 변수가 설정되지 않았거나 DB 자격증명이 잘못됨

**해결 방법**:

1. 환경 변수 확인
   ```bash
   echo $BI_AGENT_PG_HOST          # macOS / Linux
   ```

2. `mcp_config.json`에서 모든 필수 변수를 설정했는지 확인
   - PostgreSQL: `BI_AGENT_PG_HOST`, `BI_AGENT_PG_DBNAME`, `BI_AGENT_PG_USER`, `BI_AGENT_PG_PASSWORD` 필수
   - MySQL: `BI_AGENT_MYSQL_HOST`, `BI_AGENT_MYSQL_DBNAME`, `BI_AGENT_MYSQL_USER`, `BI_AGENT_MYSQL_PASSWORD` 필수

3. DB 자격증명 테스트
   ```bash
   psql -h db.company.com -U bi_agent_user -d analytics -c "SELECT 1"
   ```

4. Antigravity 재시작

### 문제: "DML 쿼리 실행 불가" 오류

**원인**: SELECT 이외의 쿼리(INSERT, UPDATE, DELETE, DROP 등) 실행 시도

**해결 방법**:

bi-agent는 보안상 SELECT 쿼리만 실행 가능합니다. 데이터 수정이 필요한 경우:

- 데이터베이스 관리 도구 사용 (pgAdmin, MySQL Workbench 등)
- 별도의 쓰기 권한이 있는 연결 설정 필요 (권장하지 않음)

### 문제: "쿼리 결과가 너무 많습니다" 또는 시간 초과

**원인**: 쿼리 결과 행이 기본 500행 제한을 초과하거나 대용량 데이터

**해결 방법**:

1. SQL WHERE 절로 필터링
   ```
   @bi-agent 2024년 1월의 주문만 조회해줄래?
   ```

2. LIMIT 값 증가 (필요시만)
   ```json
   "env": {
     "BI_AGENT_QUERY_LIMIT": "1000"
   }
   ```

3. GROUP BY 또는 집계로 행 수 줄이기
   ```
   @bi-agent 월별 주문 수를 집계해줄래?
   ```

### 문제: GA4 연결 시 "Google OAuth 흐름 실패"

**원인**: Google OAuth 클라이언트 ID/Secret이 잘못되었거나 리다이렉트 URI 설정 불일치

**해결 방법**:

1. Google Cloud Console에서 OAuth 자격증명 확인
   - https://console.cloud.google.com/apis/credentials

2. 리다이렉트 URI에 `http://localhost:8080` 또는 `http://localhost:9999` 포함 확인

3. `BI_AGENT_GOOGLE_CLIENT_ID`와 `BI_AGENT_GOOGLE_CLIENT_SECRET` 다시 확인

4. 권한 스코프 확인 (GA4 읽기 권한 필요)

### 문제: "OS 키체인 접근 실패"

**원인**: 시스템 키체인이 잠겨있거나 접근 권한 없음

**해결 방법**:

1. macOS: Keychain Access 앱에서 bi-agent 항목 확인
2. Linux: `libsecret` 설치 확인: `apt-get install libsecret-1-dev`
3. Windows: Windows Credential Manager 접근 권한 확인

### 더 많은 도움이 필요한 경우

- **GitHub Issues**: https://github.com/yourusername/bi-agent/issues
- **공식 문서**: `/Users/zokr/python_workspace/BI-Agent/docs/DESIGN.md`
- **로그 확인**: Antigravity 애플리케이션 로그 디렉토리 확인

---

## 추가 정보

### 다른 클라이언트 설정

bi-agent는 MCP를 지원하는 모든 클라이언트에서 사용 가능합니다.
Claude Desktop, Cursor, VSCode Copilot 설정은 [README](../../README.md#클라이언트-설정)를 참고하세요.

### 보안 및 프라이버시

- 모든 쿼리와 데이터는 로컬 머신에서만 처리됩니다.
- 외부 LLM API(Anthropic, OpenAI 등)로는 결과 텍스트만 전송되며, 원본 데이터베이스 자격증명은 절대 전송되지 않습니다.
- OAuth 토큰은 OS 키체인에만 저장되므로, 설정 파일에는 민감한 정보가 저장되지 않습니다.

### 성능 최적화

- **대용량 쿼리**: `BI_AGENT_QUERY_LIMIT` 값을 적절히 조정하세요. 너무 크면 응답 시간이 길어질 수 있습니다.
- **스키마 캐싱**: 자주 사용하는 스키마 정보는 별도 파일로 저장할 수 있습니다.
- **연결 재사용**: 같은 DB에 여러 쿼리를 실행할 때 같은 `connection_id`를 사용하세요.

---

*이 문서는 bi-agent v0.1.0 기준입니다. 최종 수정: 2026-03-19.*
