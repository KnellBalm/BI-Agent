# BI-Agent 설정 가이드 (Setup Guide) - V2.1

이 문서는 BI-Agent-V2 프로젝트 실행에 필요한 환경 및 의존성 설정 방법을 설명합니다.

---

## 1. 환경 변수 설정 (.env)

프로젝트 루트의 `.env` 파일을 통해 LLM 키와 데이터베이스 연결 정보를 관리합니다.

### 🔑 LLM API 설정 (Google, Anthropic, OpenAI)
- **`GEMINI_API_KEY`**: 메인 모델인 Google Gemini API 키
- **`CLAUDE_API_KEY`**: Anthropic Claude API 키 (선택 사항)
- **`OPENAI_API_KEY`**: OpenAI API 키 (선택 사항)
- **`GEMINI_API_CONFIGS`**: 멀티 키 및 할당량 관리를 위한 JSON 배열

### 📊 BI 및 프로젝트 설정
- **`BI_JSON_PATH`**: 타겟 BI 대시보드 JSON 경로 (예: `data/suwon_pop.json`)
- **`OUTPUT_DIR`**: 최종 리포트 저장 대상 디렉토리 (기본: `output/`)

### 🛠️ 서버 포트
- **`SERVER_PORT`**: 3000 (TUI Dashboard Preview)
- **`API_PORT`**: 8000 (FastAPI Backend)

---

## 2. Python 환경 및 의존성 설치

BI-Agent는 Python 3.10 이상을 권장하며, 데이터 분석 및 PDF 생성을 위한 추가 패키지가 필요합니다.

```bash
# 가상 환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 기본 의존성 설치
pip install -r backend/requirements.txt

# Phase 2-5용 추가 의존성 설치 (필수)
pip install flask openpyxl weasyprint pyperclip jsonschema
```

> [!IMPORTANT]
> `weasyprint`는 PDF 생성을 위해 시스템 라이브러리(GObject, Pango 등)가 필요할 수 있습니다. 설치 에러 발생 시 공식 문서를 참조하세요.

---

## 3. 프로그램 실행

### 상호작용형 TUI 콘솔 (메인)
```bash
python -m backend.orchestrator.bi_agent_console
```

### 데이터 소스 스캐너 (단독 실행)
```bash
python -m backend.agents.data_source.metadata_scanner
```

---

## 4. MCP(Model Context Protocol) 서버 연동

외부 도구(Claude Desktop 등)에서 BI-Agent를 도구로 사용하려면 MCP 서버를 실행합니다.

```bash
# PostgreSQL용 MCP 서버 실행
npm run mcp:postgres

# Excel 전용 MCP 서버 실행
npm run mcp:excel
```

---
**마지막 업데이트**: 2026-01-30
Copyright © 2026 BI-Agent Team. All rights reserved.
