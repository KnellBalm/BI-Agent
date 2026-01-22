# BI-Agent 설정 가이드 (Setup Guide)

이 문서는 프로젝트 실행에 필요한 환경 변수(.env) 설정 방법을 설명합니다.

## 1. 환경 변수 설정 (.env)

프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 다음 변수들을 설정합니다. `.env.example` 파일을 복사하여 사용할 수 있습니다.

### [LLM API 설정]
- **`GEMINI_API_KEY`**: 메인으로 사용할 Google Gemini API 키입니다.
- **`GEMINI_MODEL`**: 사용할 모델명입니다. (기본값: `gemini-2.0-flash`)
- **`OLLAMA_MODEL`**: 모든 Gemini API 키 소진 시 사용할 로컬 모델명입니다. (기본값: `llama3`)
- **`GEMINI_API_CONFIGS`**: 멀티 키 관리 및 과금 제어를 위한 JSON 배열 설정입니다.
  - `key`: API 키
  - `type`: `free` 또는 `paid` (과금 모델 구분)
  - `project_id`: GCP 프로젝트 ID (할당량 추적용)
- **`GCP_PROJECT_ID`**: 기본 GCP 프로젝트 ID입니다.

### [BI 솔루션 설정]
- **`BI_JSON_PATH`**: 분석 및 수정할 BI 리포트의 JSON 파일 경로입니다.

### [서버 및 MCP 설정]
- **`SERVER_PORT`**: 메인 서버 포트 (기본: 3000)
- **`API_PORT`**: FastAPI 백엔드 포트 (기본: 8000)
- **`MCP_EXCEL_PORT`**: Excel MCP 서버 포트 (기본: 3003)

### [개발 및 로그]
- **`DEBUG`**: 디버그 모드 활성화 여부
- **`LOG_LEVEL`**: 로그 레벨 (info, debug, error 등)

## 2. 가상 환경 설정 (Python)

```bash
python -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

## 3. MCP 서버 실행

Node.js 환경에서 각 데이터 소스별 MCP 서버를 실행할 수 있습니다.
```bash
npm run mcp:postgres
npm run mcp:excel
```
