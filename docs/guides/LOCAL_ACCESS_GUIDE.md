# 로컬 서버 접속 가이드 (Local Access Guide)

BI-Agent 프로젝트의 프리뷰 서버(Flask)나 API 서버(FastAPI)를 로컬 환경에서 실행할 때, 사용 중인 OS에 따라 접속 방법이 다를 수 있습니다. 이 가이드는 환경별 접속 방법을 설명합니다.

---

## 1. 개요
프로그램이 기본적으로 실행되는 포트는 다음과 같습니다 (설정에 따라 변경 가능):
- **Dashboard Preview (Flask)**: `3000`
- **FastAPI Backend**: `8000`

---

## 2. Windows (WSL2 환경)

Windows에서 WSL2를 사용해 서버를 띄운 경우, Windows 브라우저에서 접근하는 방법은 다음과 같습니다.

### ✅ 기본 접속 (Localhost Forwarding)
최신 WSL2 버전은 자동으로 포트 포워딩을 지원합니다.
- 주소: `http://localhost:3000` 또는 `http://localhost:8000`

### ❌ 접속이 안 될 경우 체크리스트

#### ① Host 바인딩 확인
서버 실행 시 호스트가 `127.0.0.1`로 고정되어 있으면 외부(Windows)에서 접근이 차단될 수 있습니다. 반드시 `0.0.0.0`으로 실행하세요.
```bash
# Flask 예시
flask run --host=0.0.0.0 --port=3000
# FastAPI 예시
uvicorn main:app --host 0.0.0.0 --port 8000
```

#### ② WSL IP 직접 접속
포트 포워딩이 제대로 작동하지 않는다면 WSL의 내부 IP를 직접 확인해야 합니다.
```bash
# WSL 터미널에서 실행
hostname -I
```
출력된 IP(예: `172.25.123.45`)를 복사하여 브라우저에 입력합니다.
- 주소: `http://172.25.123.45:3000`

#### ③ .wslconfig 확인
`C:\Users\<YourUsername>\.wslconfig` 파일에 다음 설정이 있는지 확인하세요.
```ini
[wsl2]
localhostForwarding=true
```

---

## 3. macOS 및 Linux (Native)

macOS나 Linux 데스크탑에서 직접 실행하는 경우 가장 직관적입니다.

### ✅ 기본 접속
- 주소: `http://localhost:3000`

### 📡 네트워크 내 다른 기기에서 접속 (Mobile 등)
같은 Wi-Fi 공유기에 연결된 다른 기기에서 접속하려면:
1. 서버를 `0.0.0.0` 호스트로 실행합니다.
2. 실행 중인 컴퓨터의 IP를 확인합니다.
   - **macOS**: `ipconfig getifaddr en0`
   - **Linux**: `hostname -I`
3. 해당 IP로 접속합니다 (예: `http://192.168.0.10:3000`).

---

## 4. 공통 주의사항
- **방화벽 설정**: Windows 방화벽이나 리눅스의 ufw/iptables에서 해당 포트가 허용되어 있는지 확인하세요.
- **Docker 사용 시**: 도커 컨테이너로 실행 중이라면 `-p 3000:3000`과 같이 포트 매핑이 필수입니다.

---
**마지막 업데이트**: 2026-02-19
Copyright © 2026 BI-Agent Team. All rights reserved.
