# WSL (Home) Development Setup Guide

이 가이드는 Mac에서 작업하던 내용을 집(WSL)에서 그대로 이어하기 위한 절차입니다.

## 1. 최신 코드 가져오기
가장 확실한 방법은 새로 클론받거나 기존 폴더를 초기화하는 것입니다.
```bash
# 새로 클론할 경우
git clone <your-repo-url> BI-Agent
cd BI-Agent

# 기존 폴더에서 할 경우
git pull origin main
```

## 2. 가상환경 (venv) 초기화 (중요!)
Mac의 venv는 WSL에서 작동하지 않습니다. 반드시 새로 만드세요.
```bash
# 기존 venv 삭제 (있다면)
rm -rf venv

# 새 가상환경 생성 및 패키지 설치
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 3. 환경 변수 (.env) 설정
`.env` 파일은 Git에 포함되지 않으므로 수동으로 만드세요.
```bash
touch .env
```
아래 내용을 `.env`에 복사해 넣으세요 (오늘 성공한 Paid 키 포함):
```bash
GEMINI_API_KEY=AIzaSyD5AAHOFFFAgG9EytclFel_9Yd0d-ymvPc
GEMINI_MODEL=gemini-2.0-flash
# 나머지 설정은 .env.example 참고
```

## 4. 앱 인증 정보 초기화 (중요!)
오늘 고생했던 `credentials.json` 문제입니다. WSL에서도 초기값으로 맞춰야 합니다.
```bash
# 설정 폴더 생성
mkdir -p ~/.bi-agent

# 초기 credentials.json 생성 (더미 키 삭제)
echo '{"providers": {"gemini": {"key": null, "token": null}, "claude": {"key": null, "token": null}, "openai": {"key": null, "token": null}}}' > ~/.bi-agent/credentials.json
```

## 5. 동작 확인 (E2E 테스트)
모든 설정이 완료되었는지 확인하는 명령어입니다.
```bash
# 1. 패키지 임포트 테스트
pytest tests/test_e2e_import.py

# 2. 실제 LLM + DB 연동 파이프라인 테스트 (오늘 성공한 것)
python tests/test_e2e_pipeline.py
```

## 6. 추가 팁
- **DB 경로**: `config/connections.json`의 SQLite 경로가 `backend/data/...`인 상대경로인지 확인하세요.
- **포트**: WSL에서 실행 시 `SERVER_PORT=3000` 등이 이미 사용 중인지 확인하세요 (`netstat -ano | grep 3000`).
