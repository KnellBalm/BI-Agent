# BI-Agent 사용 가이드

BI-Agent는 자연어로 데이터를 조회하고 BI 대시보드를 수정할 수 있는 AI Agent입니다.

## 설치

### 1. 저장소 클론

```bash
git clone https://github.com/your-org/bi-agent.git
cd bi-agent
```

### 2. 의존성 설치

```bash
# Node.js 패키지
npm install

# Python 패키지
pip install -r backend/requirements.txt
```

### 3. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 열고 GEMINI_API_KEY 입력
```

---

## 사용 방법

### Claude Desktop에서 사용

1. Claude Desktop 설정 파일 열기:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

2. MCP 서버 등록:

```json
{
  "mcpServers": {
    "bi-agent": {
      "command": "node",
      "args": ["/path/to/bi-agent/bin/bi-agent-mcp.js"],
      "env": {
        "GEMINI_API_KEY": "your-api-key"
      }
    }
  }
}
```

3. Claude Desktop 재시작

4. 자연어로 질문:
   - "PostgreSQL에서 이번 달 매출 상위 10개 제품 보여줘"
   - "매출 대시보드에 이익률 필드 추가해줘"

### CLI로 직접 사용

```bash
python backend/main.py
```

---

## 제공 기능

| 도구 | 설명 |
|------|------|
| query_data | 자연어로 DB 조회 (PostgreSQL, MySQL, Excel) |
| modify_bi | BI 대시보드 수정 (필드/쿼리/시각화) |
| list_connections | 등록된 연결 목록 조회 |
| register_connection | 새 데이터 연결 등록 |

---

## 데이터 소스 연결

### PostgreSQL

```
# 대화로 연결 등록
"test_pg라는 이름으로 localhost:5433의 biagent_test DB에 연결해줘. 사용자는 biagent, 비밀번호는 biagent123"
```

### 테스트용 Docker DB

```bash
cd /mnt/z/GitHub/docker-db
docker compose up -d
```

---

## 문제 해결

### "GEMINI_API_KEY not found"

`.env` 파일에 API 키가 설정되어 있는지 확인하세요.

### MCP 서버 연결 실패

1. Node.js 18+ 설치 확인
2. Python 3.10+ 설치 확인
3. 경로가 절대 경로인지 확인

---

**최종 업데이트**: 2026-01-22
