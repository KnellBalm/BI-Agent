# BI-Agent

Business Intelligence 작업을 자동화하는 AI Agent 시스템

## 개요

BI-Agent는 자연어로 BI 작업을 수행할 수 있는 멀티 Agent 시스템입니다. 사용자는 채팅 인터페이스를 통해 데이터 조회, 분석, 대시보드 수정 등을 자동으로 수행할 수 있습니다.

## 주요 기능

- **데이터 소스 연결**: PostgreSQL, MySQL, Excel 파일 지원
- **자연어 쿼리**: "2024년 매출 추이를 보여줘" 같은 자연어 명령 처리
- **BI 대시보드 자동 수정**: JSON 기반 BI 솔루션 자동 업데이트
- **멀티 Agent 아키텍처**: Orchestrator, Data Source, BI Tool Agent 협업

## 아키텍처

```
┌─────────────────┐
│   Web UI        │
│   (React)       │
└────────┬────────┘
         │
┌────────▼────────┐
│  Orchestrator   │
│     Agent       │
└────┬────────┬───┘
     │        │
┌────▼─────┐ ┌▼──────────┐
│ Data     │ │ BI Tool   │
│ Source   │ │ Agent     │
│ Agent    │ │           │
└──────────┘ └───────────┘
```

자세한 내용은 [docs/PLAN.md](docs/PLAN.md)를 참고하세요.

## 프로젝트 구조

```
BI-Agent/
├── backend/              # Python 백엔드
│   ├── orchestrator/     # Orchestrator Agent
│   ├── agents/           # Sub-Agents
│   │   ├── data_source/  # Data Source Agent
│   │   └── bi_tool/      # BI Tool Agent
│   ├── mcp_servers/      # MCP 서버들
│   └── requirements.txt  # Python 의존성
├── frontend/             # React 프론트엔드
│   └── src/
├── server/               # Node.js 웹 서버
├── docs/                 # 문서
│   └── PLAN.md          # 구현 계획서
├── tests/                # 테스트
└── tmp/                  # 임시 파일 (BI JSON 샘플 등)
```

## 빠른 시작

### 사전 요구사항

- Python 3.9+
- Node.js 18+
- PostgreSQL/MySQL (선택)

### 설치

```bash
# 1. 저장소 클론 (또는 이미 클론된 경우 생략)
cd BI-Agent

# 2. Python 의존성 설치
pip install -r backend/requirements.txt

# 3. Node.js 의존성 설치
npm install

# 4. 환경 변수 설정
cp .env.example .env
# .env 파일에서 GEMINI_API_KEY 등 설정
```

### 실행

```bash
# 1. 백엔드 실행 (Python)
python backend/orchestrator/main.py

# 2. 웹 서버 실행 (Node.js)
npm start

# 3. 프론트엔드 개발 서버 (별도 터미널)
cd frontend
npm run dev
```

브라우저에서 `http://localhost:3000` 접속

## 개발 상태

현재 **POC (Proof of Concept)** 단계입니다.

- [x] 프로젝트 구조 생성
- [x] MCP 서버 설정 (PostgreSQL, MySQL, Excel)
- [ ] LLM 통합 (Google Gemini)
- [ ] Data Source Agent 구현
- [ ] BI Tool Agent 구현
- [ ] Orchestrator Agent 구현
- [ ] 웹 UI 구현
- [ ] 테스트 및 문서화

## 기술 스택

- **Backend**: Python, LangGraph, pandas
- **MCP Protocol**: Model Context Protocol
- **LLM**: Google Gemini API (+ Ollama 향후 지원)
- **Frontend**: React, Chart.js
- **Server**: Node.js, Express
- **Database**: PostgreSQL, MySQL

## 문서

- [TODO 리스트](docs/TODO.md) - 개발 작업 목록 및 진행 상황
- [구현 계획서](docs/PLAN.md) - 전체 시스템 설계 및 구현 계획
- [MCP 서버 가이드](docs/MCP_SERVERS.md) - MCP 서버 설정 및 사용법
- [아키텍처 문서](docs/ARCHITECTURE.md) - (작성 예정)
- [API 명세](docs/API.md) - (작성 예정)

## 라이선스

MIT License

## 기여

이 프로젝트는 현재 개발 초기 단계입니다.
