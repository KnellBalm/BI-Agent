# MCP 서버 가이드

Model Context Protocol (MCP) 서버는 AI Agent가 데이터 소스에 접근할 수 있도록 하는 표준화된 인터페이스입니다.

## Python vs JavaScript MCP 서버

BI-Agent는 **Python**과 **JavaScript** 두 가지 구현을 지원합니다:

| 특징 | Python 구현 (.py) | JavaScript 구현 (.js) |
|------|------------------|---------------------|
| **상태** | ✅ **기본값 (권장)** | 레거시 (하위 호환용) |
| **통합** | 네이티브 (FastAPI, langgraph) | Node.js 런타임 필요 |
| **성능** | 빠름 (asyncio) | 빠름 (Promise) |
| **SDK** | mcp>=1.23.0 (FastMCP) | @modelcontextprotocol/sdk@0.5.0 |
| **타입 안전성** | Pydantic 모델 | TypeScript |

**기본적으로 Python 서버가 사용됩니다.** JavaScript 서버로 전환하려면:
```bash
export MCP_USE_PYTHON=false
```

## 설치된 MCP 서버

모든 MCP 서버는 Python (.py)과 JavaScript (.js) 두 가지 버전으로 제공됩니다.

### 1. PostgreSQL MCP 서버

**위치**:
- Python: `backend/mcp_servers/postgres_server.py` (기본값)
- JavaScript: `backend/mcp_servers/postgres_server.js` (레거시)

**기능**:
- PostgreSQL 데이터베이스 쿼리 실행 (읽기 전용)
- 테이블 목록 조회
- 테이블 스키마 확인

**사용 가능한 도구**:
- `query`: SQL SELECT 쿼리 실행
- `list_tables`: 모든 테이블 목록
- `describe_table`: 테이블 스키마 정보

**실행**:
```bash
# Python 버전 (기본값)
npm run mcp:postgres

# JavaScript 버전 (레거시)
npm run mcp:postgres:js
```

**환경 변수** (.env 파일):
```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=your_database
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password
```

**예시**:
```json
{
  "tool": "query",
  "arguments": {
    "sql": "SELECT * FROM users LIMIT 10"
  }
}
```

---

### 2. MySQL MCP 서버

**위치**:
- Python: `backend/mcp_servers/mysql_server.py` (기본값)
- JavaScript: `backend/mcp_servers/mysql_server.js` (레거시)

**기능**:
- MySQL/MariaDB 데이터베이스 쿼리 실행 (읽기 전용)
- 테이블 목록 조회
- 테이블 스키마 확인

**사용 가능한 도구**:
- `query`: SQL SELECT 쿼리 실행
- `list_tables`: 모든 테이블 목록
- `describe_table`: 테이블 스키마 정보

**실행**:
```bash
# Python 버전 (기본값)
npm run mcp:mysql

# JavaScript 버전 (레거시)
npm run mcp:mysql:js
```

**환경 변수** (.env 파일):
```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DB=your_database
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
```

**예시**:
```json
{
  "tool": "list_tables",
  "arguments": {}
}
```

---

### 3. Excel MCP 서버

**위치**:
- Python: `backend/mcp_servers/excel_server.py` (기본값)
- JavaScript: `backend/mcp_servers/excel_server.js` (레거시)

**기능**:
- Excel 파일 읽기 (.xlsx, .xls)
- Excel 파일 쓰기
- 시트 목록 조회
- 특정 범위 읽기

**사용 가능한 도구**:
- `read_excel`: Excel 파일 데이터 읽기
- `list_sheets`: 시트 이름 목록
- `write_excel`: Excel 파일 생성/수정

**실행**:
```bash
# Python 버전 (기본값)
npm run mcp:excel

# JavaScript 버전 (레거시)
npm run mcp:excel:js
```

**예시 - 파일 읽기**:
```json
{
  "tool": "read_excel",
  "arguments": {
    "file_path": "/path/to/file.xlsx",
    "sheet_name": "Sheet1",
    "range": "A1:D10"
  }
}
```

**예시 - 파일 쓰기**:
```json
{
  "tool": "write_excel",
  "arguments": {
    "file_path": "/path/to/output.xlsx",
    "data": [
      {"name": "John", "age": 30},
      {"name": "Jane", "age": 25}
    ],
    "sheet_name": "Users"
  }
}
```

---

### 4. BigQuery MCP 서버

**위치**:
- Python: `backend/mcp_servers/bigquery_server.py` (기본값)
- JavaScript: `backend/mcp_servers/bigquery_server.js` (레거시)

**기능**:
- Google BigQuery 쿼리 실행
- 데이터셋 목록 조회
- 테이블 목록 조회

**사용 가능한 도구**:
- `query`: BigQuery SQL 실행
- `list_datasets`: 프로젝트 내 데이터셋 목록
- `list_tables`: 데이터셋 내 테이블 목록

**실행**:
```bash
# Python 버전 (기본값)
npm run mcp:bigquery

# JavaScript 버전 (레거시)
npm run mcp:bigquery:js
```

---

### 5. Snowflake MCP 서버

**위치**:
- Python: `backend/mcp_servers/snowflake_server.py` (기본값)
- JavaScript: `backend/mcp_servers/snowflake_server.js` (레거시)

**기능**:
- Snowflake 데이터 웨어하우스 쿼리 실행
- 테이블 목록 조회

**사용 가능한 도구**:
- `query`: Snowflake SQL 실행
- `list_tables`: 스키마 내 테이블 목록

**실행**:
```bash
# Python 버전 (기본값)
npm run mcp:snowflake

# JavaScript 버전 (레거시)
npm run mcp:snowflake:js
```

**환경 변수**:
```env
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_WAREHOUSE=your_warehouse
SNOWFLAKE_DATABASE=your_database
SNOWFLAKE_SCHEMA=your_schema
SNOWFLAKE_ROLE=your_role
```

---

### 6. GCP Manager MCP 서버

**위치**:
- Python: `backend/mcp_servers/gcp_manager_server.py` (기본값)
- JavaScript: `backend/mcp_servers/gcp_manager_server.js` (레거시)

**기능**:
- GCP 쿼터 사용량 조회
- GCP 빌링 정보 조회

**사용 가능한 도구**:
- `get_quota_usage`: 서비스별 쿼터 사용량
- `get_billing_info`: 프로젝트 빌링 정보

**실행**:
```bash
# Python 버전 (기본값)
npm run mcp:gcp

# JavaScript 버전 (레거시)
npm run mcp:gcp:js
```

---

## MCP 프로토콜 구조

### 요청 형식

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "tool_name",
    "arguments": {
      "param1": "value1"
    }
  },
  "id": 1
}
```

### 응답 형식

```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"rows\": [...], \"rowCount\": 10}"
      }
    ]
  },
  "id": 1
}
```

---

## Python에서 MCP 서버 사용

MCP 클라이언트를 사용하여 Python Agent에서 MCP 서버를 호출할 수 있습니다.

### 설치

```bash
pip install mcp>=1.23.0
```

### Python MCP 서버 사용 (권장)

```python
import asyncio
from backend.agents.data_source.mcp_client import MCPClient

async def query_postgres():
    # MCPClient가 자동으로 .py/.js 감지
    client = MCPClient("backend/mcp_servers/postgres_server.py")

    try:
        await client.connect()

        # 도구 호출
        result = await client.call_tool("query", {
            "sql": "SELECT * FROM users LIMIT 10"
        })

        print(result.content[0].text)
    finally:
        await client.disconnect()

# 실행
asyncio.run(query_postgres())
```

### JavaScript MCP 서버 사용 (레거시)

```python
import asyncio
from backend.agents.data_source.mcp_client import MCPClient

async def query_postgres_js():
    # .js 파일을 전달하면 자동으로 node 명령어 사용
    client = MCPClient("backend/mcp_servers/postgres_server.js")

    try:
        await client.connect()
        result = await client.call_tool("query", {
            "sql": "SELECT * FROM users LIMIT 10"
        })
        print(result.content[0].text)
    finally:
        await client.disconnect()

asyncio.run(query_postgres_js())
```

**MCPClient의 자동 감지 기능**:
- `.py` 파일 → Python 실행 (`sys.executable`), `PYTHONUNBUFFERED=1`, `PYTHONIOENCODING=utf-8` 설정
- `.js` 파일 → Node.js 실행 (`node` 명령어)

---

## 보안 고려사항

### 읽기 전용 제약

PostgreSQL과 MySQL MCP 서버는 **SELECT 쿼리만 허용**합니다. INSERT, UPDATE, DELETE 등의 쓰기 작업은 차단됩니다.

```javascript
// 서버 코드에서 검증
if (!sql.trim().toLowerCase().startsWith('select')) {
  throw new Error('Only SELECT queries are allowed');
}
```

### 환경 변수 관리

데이터베이스 비밀번호 등 민감한 정보는 `.env` 파일에 저장하고 Git에 커밋하지 마세요.

```bash
# .env.example을 복사하여 사용
cp .env.example .env

# .env 파일 편집
nano .env
```

### SQL Injection 방지

- PostgreSQL: `pg` 라이브러리의 파라미터화된 쿼리 사용
- MySQL: `mysql2`의 `escapeId()` 사용
- Excel: 파일 경로 검증

---

## 트러블슈팅

### MCP 서버가 시작되지 않음

**증상**:
```bash
npm run mcp:postgres
# 아무 출력 없음 또는 에러
```

**해결**:
1. 환경 변수 확인: `.env` 파일이 존재하고 올바른 값이 설정되어 있는지 확인
2. 데이터베이스 연결 확인: `psql` 또는 `mysql` 명령어로 직접 연결 테스트
3. Node.js 버전 확인: `node --version` (18 이상 필요)

### "Only SELECT queries are allowed" 에러

**원인**: INSERT, UPDATE, DELETE 등의 쓰기 쿼리를 실행하려고 함

**해결**: POC 단계에서는 읽기 전용이므로 SELECT 쿼리만 사용하세요. 쓰기가 필요하면 서버 코드를 수정하거나 별도의 API를 구현하세요.

### Excel 파일을 찾을 수 없음

**원인**: 파일 경로가 잘못되었거나 파일이 존재하지 않음

**해결**:
1. 절대 경로 사용: `/Users/zokr/python_workspace/BI-Agent/tmp/data.xlsx`
2. 파일 존재 확인: `ls -la /path/to/file.xlsx`
3. 권한 확인: 파일 읽기 권한이 있는지 확인

---

## 다음 단계

MCP 서버가 설정되었으면 다음을 진행하세요:

1. **Python MCP 클라이언트 구현**: `backend/agents/data_source/mcp_client.py`
2. **Data Source Agent 구현**: MCP 클라이언트를 사용하여 데이터 조회
3. **테스트 작성**: `tests/test_mcp_servers.py`

자세한 내용은 [PLAN.md](PLAN.md)를 참고하세요.
