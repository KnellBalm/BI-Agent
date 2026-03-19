# bi-agent MCP

BI 분석가를 위한 Model Context Protocol 서버. Claude Desktop, Cursor, VSCode, Antigravity 등 MCP를 지원하는 LLM 클라이언트에서 자연어로 데이터베이스를 분석하세요.

## 특징

- **다중 DB 지원**: PostgreSQL, MySQL, BigQuery 연결 및 SELECT 쿼리 실행
- **외부 데이터 소스**: Google Analytics 4, Amplitude 이벤트 데이터 조회
- **자동 분석**: 테이블 프로파일링, 스키마 분석, 분석 방향 제안
- **아웃풋 생성**: 마크다운 분석 리포트, Tableau TWBX 파일 자동 생성
- **데이터 안전성**: SELECT 전용(읽기만), 결과 행 수 제한, 로컬 처리 보장

## 빠른 시작

### 1단계: 설치

Python 3.11 이상 필요합니다.

```bash
pip install bi-agent-mcp
```

또는 개발 모드:

```bash
git clone https://github.com/your-org/bi-agent.git
cd bi-agent
python -m venv .venv
source .venv/bin/activate  # macOS/Linux 또는 .venv\Scripts\activate (Windows)
pip install -e .
```

### 2단계: 클라이언트 설정

아래 클라이언트 중 하나를 선택하여 설정합니다.

## 클라이언트 설정

### Claude Desktop

`~/.claude/claude_desktop_config.json` (macOS) 또는 `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

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
        "BI_AGENT_PG_PASSWORD": "your_password"
      }
    }
  }
}
```

### Cursor

`.cursor/mcp.json` (프로젝트 루트 또는 `~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
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

### VSCode Copilot

`.vscode/mcp.json`:

```json
{
  "servers": {
    "bi-agent": {
      "type": "stdio",
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

### Antigravity

자세한 설정 방법은 [Antigravity 클라이언트 가이드](./docs/clients/antigravity.md)를 참고하세요.

기본 설정 예시 (`~/.gemini/antigravity/mcp_config.json`):

```json
{
  "mcpServers": {
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

## 환경 변수

모든 환경 변수는 `BI_AGENT_` 접두사를 사용합니다.

### PostgreSQL

| 변수명 | 설명 | 기본값 | 필수 |
|--------|------|--------|------|
| `BI_AGENT_PG_HOST` | 호스트 주소 | `localhost` | N |
| `BI_AGENT_PG_PORT` | 포트 | `5432` | N |
| `BI_AGENT_PG_DBNAME` | 데이터베이스 이름 | - | Y* |
| `BI_AGENT_PG_USER` | 사용자명 | - | Y* |
| `BI_AGENT_PG_PASSWORD` | 비밀번호 | - | Y* |

### MySQL

| 변수명 | 설명 | 기본값 | 필수 |
|--------|------|--------|------|
| `BI_AGENT_MYSQL_HOST` | 호스트 주소 | `localhost` | N |
| `BI_AGENT_MYSQL_PORT` | 포트 | `3306` | N |
| `BI_AGENT_MYSQL_DBNAME` | 데이터베이스 이름 | - | Y* |
| `BI_AGENT_MYSQL_USER` | 사용자명 | - | Y* |
| `BI_AGENT_MYSQL_PASSWORD` | 비밀번호 | - | Y* |

### BigQuery

| 변수명 | 설명 | 기본값 | 필수 |
|--------|------|--------|------|
| `BI_AGENT_BQ_PROJECT_ID` | Google Cloud 프로젝트 ID | - | Y* |
| `BI_AGENT_BQ_DATASET` | 데이터셋 이름 | - | Y* |
| `BI_AGENT_BQ_CREDENTIALS_PATH` | 서비스 계정 키 경로 | - | Y* |

### Google Analytics 4

| 변수명 | 설명 | 기본값 | 필수 |
|--------|------|--------|------|
| `BI_AGENT_GOOGLE_CLIENT_ID` | OAuth 클라이언트 ID | - | Y* |
| `BI_AGENT_GOOGLE_CLIENT_SECRET` | OAuth 클라이언트 시크릿 | - | Y* |

### Amplitude

| 변수명 | 설명 | 기본값 | 필수 |
|--------|------|--------|------|
| `BI_AGENT_AMPLITUDE_API_KEY` | API 키 | - | Y* |
| `BI_AGENT_AMPLITUDE_SECRET_KEY` | 시크릿 키 | - | Y* |

### 기타

| 변수명 | 설명 | 기본값 | 필수 |
|--------|------|--------|------|
| `BI_AGENT_QUERY_LIMIT` | 쿼리 결과 최대 행 수 | `500` | N |

> Y* = 해당 데이터 소스를 사용할 때 필수

## MCP 도구 목록

### v0 — 핵심 데이터베이스 기능

| 도구명 | 설명 |
|--------|------|
| `connect_db` | PostgreSQL, MySQL, BigQuery 연결 등록 |
| `list_connections` | 등록된 연결 목록 조회 (비밀번호 마스킹) |
| `get_schema` | 테이블 스키마 조회 (컬럼, 타입, 샘플 데이터) |
| `run_query` | SELECT 쿼리 실행 (읽기 전용, 최대 500행) |
| `profile_table` | 테이블 프로파일링 (NULL 비율, 유니크 값, 최댓값, 상위값) |

### v1 — 외부 데이터 소스 연동

| 도구명 | 설명 |
|--------|------|
| `connect_ga4` | Google Analytics 4 연결 (OAuth 2.0) |
| `get_ga4_report` | GA4 지표 및 차원 조회 |
| `connect_amplitude` | Amplitude 프로젝트 연결 |
| `get_amplitude_events` | Amplitude 이벤트 데이터 조회 |
| `suggest_analysis` | 데이터 컨텍스트에 맞는 분석 방향 제안 |
| `save_query` | 자주 사용하는 쿼리 저장 |
| `list_saved_queries` | 저장된 쿼리 목록 조회 |

### v2 — 아웃풋 생성

| 도구명 | 설명 |
|--------|------|
| `generate_report` | 마크다운 분석 리포트 생성 |
| `generate_twbx` | Tableau 워크북 초안 생성 (.twbx 파일)

## 보안

### 핵심 보안 원칙

- **SELECT 전용**: DML 쿼리(INSERT, UPDATE, DELETE, DROP 등) 자동 차단
- **결과 행 제한**: 기본 500행 제한 (환경 변수로 조정 가능)
- **로컬 처리 보장**: 모든 데이터는 사용자 로컬 머신 또는 사내 네트워크에서만 처리
- **자격증명 보호**: 평문 로그 기록 없음, 민감한 정보는 마스킹됨

### 자격증명 저장

- **환경 변수**: 권장 방식 (`.env` 파일 사용 가능)
- **OS 키체인**: OAuth 토큰 저장 (macOS Keychain, Linux libsecret, Windows Credential Manager)
- **설정 파일**: 민감한 정보는 절대 설정 파일에 저장하지 마세요

### 데이터 개인정보보호

- 쿼리 결과는 로컬 메모리에서만 처리되며 디스크에 저장되지 않음
- LLM API로는 텍스트 표현만 전송되고 원본 데이터는 전송되지 않음
- 저장된 쿼리는 SQL 텍스트만 저장하며 결과 데이터는 저장하지 않음

## 문서

- [상세 설계 문서](./docs/DESIGN.md) - 시스템 아키텍처, MCP 도구 명세
- [Antigravity 설정 가이드](./docs/clients/antigravity.md) - Antigravity 클라이언트 설정
- [설치 & 배포](./docs/DESIGN.md#5-설치--배포) - 다양한 클라이언트 설정 방법

## 지원

문제가 발생하면:

1. [공식 문서](./docs/DESIGN.md)를 확인하세요
2. [GitHub Issues](https://github.com/your-org/bi-agent/issues)에서 유사한 이슈를 검색하세요
3. 새로운 이슈를 생성할 때는 다음 정보를 포함해주세요:
   - Python 버전 (`python --version`)
   - 설치 방식 (pip 또는 git clone)
   - 사용 중인 클라이언트 (Claude Desktop, Cursor, VSCode, Antigravity)
   - 오류 메시지

## 라이센스

MIT License
