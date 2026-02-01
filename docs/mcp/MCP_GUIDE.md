# MCP (Model Context Protocol) 작동 원리 가이드

이 문서는 BI Agent 시스템에서 핵심적인 역할을 하는 MCP의 구조와 작동 방식을 코드 레벨에서 설명합니다.

## 1. 개요
MCP는 LLM(Large Language Model)이 로컬 리소스(데이터베이스, 파일 시스템, API 등)와 안전하게 통신할 수 있도록 만든 **개방형 표준 프로토콜**입니다. 우리 프로젝트에서는 **Python(Client)**과 **Node.js(Server)** 사이의 통신 브리지 역할을 합니다.

## 2. 시스템 아키텍처

```mermaid
graph LR
    subgraph "Python Client (Agent)"
        A[DataSourceAgent] --> B[MCPClient]
    end
    
    subgraph "Node.js Server"
        C[MCP Server] --> D[Resource (DB/Excel)]
    end
    
    B -- "Stdio (JSON-RPC)" --> C
```

## 3. 세부 작동 방식

### (1) 서버 섹션: 도구 정의 및 핸들링 (Node.js)
서버는 자신이 제공할 수 있는 **Tools**를 정의하고 호출에 응답합니다.

- **지원 도구 선언**: `ListToolsRequestSchema` 핸들러를 통해 어떤 도구(이름, 파라미터 규격)가 있는지 클라이언트에 알립니다.
- **도구 실행**: `CallToolRequestSchema` 핸들러에서 실제 비즈니스 로직(DB 쿼리 등)을 수행하고 결과를 반환합니다.

```javascript
// 예시: excel_server.js
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  if (name === 'read_excel') {
    // 실제 엑셀 읽기 로직...
    return { content: [{ type: 'text', text: JSON.stringify(data) }] };
  }
});
```

### (2) 클라이언트 섹션: 서버 제어 및 호출 (Python)
클라이언트는 서버 프로세스를 실행하고 도구를 호출합니다.

- **프로세스 관리**: `stdio_client`를 사용하여 노드 프로세스를 실행하고 표준 입력(stdin)/표준 출력(stdout) 채널을 확보합니다.
- **도구 호출**: JSON-RPC 메시지를 통해 서버에 명령을 내립니다.

```python
# 예시: mcp_client.py
async def call_tool(self, name: str, arguments: Dict[str, Any]):
    # 서버 세션을 통해 요청 전송
    return await self.session.call_tool(name, arguments)
```

### (3) 통신 프로토콜: JSON-RPC over Stdio
- 모든 통신은 **JSON-RPC 2.0** 규격을 따릅니다.
- 별도의 네트워크 포트를 열지 않고, 프로세스 간의 **Standard I/O** 스트림을 사용하여 보안성이 뛰어납니다.

## 4. 우리 프로젝트의 MCP 서버 목록
현재 프로젝트에서 사용 중인 주요 MCP 서버들은 다음과 같습니다:

| 서버 파일 | 역할 | 주요 도구 |
| :--- | :--- | :--- |
| `postgres_server.js` | PostgreSQL DB 연동 | `query`, `list_tables`, `describe_table` |
| `excel_server.js` | Excel 파일 읽기/쓰기 | `read_excel`, `list_sheets`, `write_excel` |
| `gcp_manager_server.js` | GCP 할당량/기기 관리 | `get_quota_usage`, `get_billing_info` |

## 5. 요약
1. **표준화**: 언어에 상관없이 동일한 규격으로 도구 사용 가능
2. **보안**: 로컬 데이터에 직접 LLM이 접근하지 않고 샌드박스화된 도구만 사용
3. **확장성**: 새로운 데이터 소스가 필요하면 새로운 MCP 서버만 추가하면 에이전트 코드 수정 최소화
