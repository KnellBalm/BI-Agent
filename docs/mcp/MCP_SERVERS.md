# MCP 서버 가이드

Model Context Protocol (MCP) 서버는 AI Agent가 데이터 소스에 접근할 수 있도록 하는 표준화된 인터페이스입니다.

## 설치된 MCP 서버

### 1. PostgreSQL MCP 서버

**위치**: `backend/mcp_servers/postgres_server.js`

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
npm run mcp:postgres
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

**위치**: `backend/mcp_servers/mysql_server.js`

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
npm run mcp:mysql
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

**위치**: `backend/mcp_servers/excel_server.js`

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
npm run mcp:excel
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
pip install mcp
```

### 사용 예시

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def query_postgres():
    server_params = StdioServerParameters(
        command="node",
        args=["backend/mcp_servers/postgres_server.js"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 도구 호출
            result = await session.call_tool("query", {
                "sql": "SELECT * FROM users LIMIT 10"
            })

            print(result.content[0].text)

# 실행
asyncio.run(query_postgres())
```

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
