# /bi-setup — bi-agent 초기 설정 마법사

bi-agent MCP 서버를 AI 클라이언트에 연결하고 데이터 소스를 등록합니다.

## 실행 절차

### $ARGUMENTS가 없을 경우 → 설치 상태 확인 후 안내

1. `check_setup_status` MCP 도구로 현재 설정 상태 확인
2. 상태에 따라 분기:
   - **미설치**: CLI 설치 방법 안내 (아래 "CLI 실행" 섹션)
   - **설치됨, 연결 없음**: 데이터 소스 추가 안내
   - **정상**: 현재 연결된 소스 목록 출력 + `/bi-connect` 안내

### $ARGUMENTS가 "상태" 또는 "status" 포함 시 → 상태 확인 모드

1. `check_setup_status` 실행 후 결과 출력
2. `list_connections` 로 현재 연결된 데이터 소스 목록 출력
3. 클라이언트 설정 파일 존재 여부 안내

### $ARGUMENTS가 "add" 또는 "추가" 포함 시 → 데이터 소스 추가

사용자에게 CLI 명령어 안내:
```
bi-agent-mcp-setup --add db         # DB 추가
bi-agent-mcp-setup --add ga4        # GA4 추가
bi-agent-mcp-setup --add amplitude  # Amplitude 추가
```

---

## CLI 실행 (가장 쉬운 방법)

터미널에서 아래 명령어를 실행하세요:

```bash
# 전체 설치 마법사 (권장)
python -m bi_agent_mcp setup

# 또는 패키지 설치 후
bi-agent setup
bi-agent-mcp-setup
```

### 마법사 진행 순서

1. **클라이언트 선택** — Claude Desktop / Cursor / VSCode / Antigravity 중 선택
2. **DB 연결 설정** — PostgreSQL / MySQL / BigQuery / Snowflake 중 선택 후 접속 정보 입력
3. **GA4 설정** (선택) — Google Analytics 4 연결
4. **Amplitude 설정** (선택) — Amplitude 연결
5. **설정 파일 자동 업데이트** — 선택한 클라이언트의 config에 bi-agent 항목 추가
6. **완료 메시지** — 재시작 안내 및 다음 단계 제안

---

## 수동 설정 (CLI를 사용할 수 없는 경우)

### 1단계: 클라이언트 설정 파일에 bi-agent 추가

아래 JSON을 클라이언트 설정 파일의 `mcpServers` 블록에 추가하세요.

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "bi-agent": {
      "command": "python",
      "args": ["-m", "bi_agent_mcp"],
      "env": {
        "BI_AGENT_PG_HOST": "localhost",
        "BI_AGENT_PG_PORT": "5432",
        "BI_AGENT_PG_DBNAME": "mydb",
        "BI_AGENT_PG_USER": "myuser"
      }
    }
  }
}
```

**Cursor** (`{프로젝트}/.cursor/mcp.json`) 또는 **VSCode** (`{프로젝트}/.vscode/mcp.json`):
```json
{
  "mcpServers": {
    "bi-agent": {
      "command": "python",
      "args": ["-m", "bi_agent_mcp"]
    }
  }
}
```

### 2단계: 클라이언트 재시작

설정 파일 저장 후 AI 클라이언트를 완전히 종료하고 재시작해야 bi-agent가 활성화됩니다.

### 3단계: 연결 테스트

클라이언트 재시작 후 대화창에 입력:
```
bi-agent 연결 상태 확인해줘
```
또는 `/bi-connect` 스킬 실행.

---

## 지원 데이터 소스

| 타입 | 환경변수 접두사 | 비고 |
|------|----------------|------|
| PostgreSQL | `BI_AGENT_PG_*` | HOST, PORT, DBNAME, USER |
| MySQL | `BI_AGENT_MYSQL_*` | HOST, PORT, DBNAME, USER |
| BigQuery | `BI_AGENT_BQ_*` | PROJECT_ID, DATASET, CREDENTIALS_PATH |
| Snowflake | `BI_AGENT_SNOWFLAKE_*` | ACCOUNT, USER, WAREHOUSE, DATABASE |
| Google Analytics 4 | `BI_AGENT_GOOGLE_CLIENT_ID`, `BI_AGENT_GA4_PROPERTY_ID` | |
| Amplitude | keyring 저장 | API_KEY, SECRET_KEY |
| CSV / Excel | `connect_file` 도구로 직접 연결 | |

비밀번호 및 시크릿은 OS keyring에 안전하게 저장됩니다 (설정 파일에 평문 없음).

---

## 사용법

```
/bi-setup                    # 설치 상태 확인 및 안내
/bi-setup 상태               # 현재 연결 목록 출력
/bi-setup add ga4            # GA4 추가 안내
```

## 참조 파일
- `bi_agent_mcp/setup_cli.py` — CLI 마법사 구현
- `bi_agent_mcp/__main__.py` — `python -m bi_agent_mcp setup` 진입점

## 사용 MCP 도구
- `check_setup_status` — 설정 상태 확인
- `list_connections` — 현재 연결된 데이터 소스 목록
