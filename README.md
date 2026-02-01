<h1 align="center">BI-Agent: The Frontier of Autonomous Business Intelligence</h1>

<p align="center">
  <strong>"데이터 오퍼레이션을 넘어, 비즈니스 인사이트의 자율화를 설계하는 아키텍트"</strong><br />
  BI-Agent는 단순한 데이터 추출 도구를 넘어, 기업의 데이터 자산을 스스로 탐색하고<br />
  <strong>차세대 의사결정 시스템(Autonomous BI)</strong>을 위한 완벽한 지능형 오케스트레이션을 제공합니다.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Version-v2.1.0-blue?style=for-the-badge&logo=semver" alt="Version" />
  <img src="https://img.shields.io/badge/Status-Production--Ready-brightgreen?style=for-the-badge&logo=statuspage" alt="Status" />
  <img src="https://img.shields.io/badge/Powered%20By-Gemini%202.0%20Flash-4285F4?style=for-the-badge&logo=google-gemini" alt="Gemini" />
  <img src="https://img.shields.io/badge/Protocol-MCP-green?style=for-the-badge" alt="MCP" />
  <img src="https://img.shields.io/badge/Architecture-Multi--Agent-blue?style=for-the-badge" alt="Architecture" />
  <img src="https://img.shields.io/badge/Test%20Coverage-94%25-success?style=for-the-badge&logo=pytest" alt="Coverage" />
</p>

---

## 🎯 Recent Updates (v2.1.0 - 2026-01-31)

### Production-Ready Release
*   **Section 0 완전 완성**: `BaseIntent`, `AnalysisIntent`, `ChartIntent` 공유 의도 아키텍처 확립
*   **모든 P0 이슈 해결**: NL Parser 안정화, Connection Manager 보안 강화, Profiler 성능 최적화
*   **Step 5/6 핵심 컴포넌트**: `TableRecommender`, `TypeCorrector`, `ConnectionValidator` 구현
*   **테스트 커버리지 94%**: 60개 테스트 스위트, 핵심 비즈니스 로직 100% 커버
*   **타입 안정성 완전 확보**: 모든 공개 API 타입 힌팅, ruff/mypy/black 린팅 100% 통과

상세 변경 내역은 [CHANGELOG.md](./docs/CHANGELOG.md)를 참조하세요.

---

## ✨ Key Features (v0.1.0 → v2.1.0)

### 기존 기능 (v0.1.0)
*   **Smart Quota & Zero-Billing**: 구독 혜택(Gemini Pro, Claude Pro 등)을 최우선 활용하되, 할당량 소진 시 추가 과금 없이 무료/로컬 모델로 자동 전환하는 'Zero-Stop' 엔진 탑재
*   **Premium Entrance Hall**: 터미널 기반의 아름다운 환영 스크린과 실시간 쿼터 대시보드가 통합된 사이드바 적용
*   **Command Palette (/)**: 슬래시(/) 키로 호출하는 직관적인 분석 명령어 시스템 (키보드 네비게이션 지원)
*   **Multi-Provider Integration**: Gemini, Claude 3.5, OpenAI 및 Ollama(Local)를 자유롭게 넘나드는 하이브리드 지능 체계 구축
*   **Secure Multi-Agent Core**: 전략가, 데이터마스터, 디자이너 에이전트의 협업 로직 최적화

### 신규 기능 (v2.1.0)
*   **공유 의도 아키텍처**: `BaseIntent` 추상 클래스 기반 일관된 Intent 시스템 (`ChartIntent`, `AnalysisIntent`)
*   **지능형 테이블 추천**: LLM 기반 relevance scoring으로 다중 테이블 환경에서 최적 테이블 자동 선정
*   **고급 데이터 프로파일링**: 컬럼별 4분위수, 결측치 비율, 타입별 맞춤 통계 실시간 산출
*   **자동 타입 교정**: 날짜/시간/숫자형 데이터의 문자열 저장 감지 및 변환 제안 시스템
*   **연결 검증 시스템**: MySQL/PostgreSQL/SQLite 연결 전 상태 체크 및 SSH 터널 안정성 검증
*   **컴포넌트 기반 오케스트레이터**: Agent Coordinator, Context Manager, Error Handler 모듈화

---

## 🏛️ Vision & Core Values

BI-Agent는 데이터 분석가의 사고 과정을 복제하고 증폭하는 **AI 파트너**를 지향합니다. 사용자의 질문에 답하는 수동적 존재에서 벗어나, 데이터의 문맥을 읽고 선제적으로 통찰을 제안합니다.

*   **Local-First & Privacy**: 클라우드 의존성을 최소화하고 로컬 데이터(DuckDB, Excel, CSV)를 우선적으로 처리합니다.
*   **Agentic Collaboration**: 전략가, 디자이너, 데이터 마스터가 각자의 전문성을 바탕으로 협업합니다.
*   **Proactive Intelligence**: 분석 완료 후 다음 비즈니스 액션을 위한 **[가설]-[질문]-[기대효과]**를 선제적으로 제안합니다.

---

## 🏗️ System Architecture

BI-Agent는 멀티 에이전트 오케스트레이션 프레임워크를 기반으로 설계되었습니다.

### 3.1 Collaborative Orchestrator (중앙 제어)
모든 분석 요청의 관제탑 역할을 수행하며, 하위 에이전트들의 출력을 조율합니다.
- **Smart Quota Manager**: 사용자의 모든 유료 구독(Gemini, Claude, GPT) 할당량을 실시간 추적하고 '과금 제로' 시점에 Fallback을 결정합니다.
- **Failover LLM Engine**: 구독 모델이 지치거나 비용 임계치에 도달하면 즉시 Ollama(로컬)나 무료 티어로 중단 없는 지능 전환을 수행합니다.

### 3.2 Specialized Agents & Skills
- **DataMaster**: `ConnectionManager`를 통해 다양한 데이터 소스(SQL, Local Files)를 안전하게 핸들링합니다.
- **Strategist**: 질문의 비즈니스 의도를 파악하고 최적의 분석 전략 및 지표(Metrics)를 선정합니다.
- **Visual Designer**: `InHouseGenerator`를 통해 데이터에 최적화된 시각화 구성을 제안합니다.

---

## 🚀 Key Features

### 🧠 하이브리드 SQL & AI 코칭
사용자가 직접 SQL을 작성하면(`sql: ...`), AI가 **구문 오류 수정, 성능 최적화, 비즈니스 맥락 주석 추가**를 지원하여 분석가의 숙련도를 한 차원 높여줍니다.

### 💡 가설 기반 선제적 인사이트
분석 결과 도출 시, LLM이 데이터 트렌드를 분석하여 **다음에 탐색할 가치가 있는 전략적 질문**을 3가지 구조화된 형태로 자동 제안합니다.

### 📊 프리미엄 로컬 대시보드
Glassmorphism과 Deep Sea Dark Theme이 적용된 세련된 인터랙티브 대시보드를 로컬 환경에서 즉시 생성합니다. (Plotly & Google Fonts 연동)

### 📂 프로젝트 기반 워크스페이스
`projects/{id}/` 단위로 지표(Metrics), 설정, 연결정보를 완벽히 격리하여 멀티 도메인 분석 환경을 제공합니다.

---

## 🗺️ User Journey (Process Flow)

1.  **Connect**: DB, CSV, Excel, DuckDB 등 소스 연결
2.  **Index**: 메타데이터 스캔 및 시멘틱 레이어(Metric Store) 구축
3.  **Refine**: 하이브리드 SQL 엔진을 통한 쿼리 코칭 및 최적화
4.  **Inquire**: 자연어 질문 기반 복합 분석 및 대시보드 생성
5.  **Deliver**: 인사이트 패키지 번들링 및 Slack/로컬 공유

---

## 🚦 Getting Started

### 1단계: 환경 준비 (Setup)
- **Python 3.10+** (필수: 3.9 이하 환경에서는 패키지를 찾을 수 없거나 설치에 실패할 수 있습니다.)
- Node.js 18+ (MCP 서버 기능 사용 시 필요)
- `.env` 파일 (Gemini API 키 등) 또는 실행 후 TUI에서 직접 입력 가능

### 2단계: 설치 및 실행 (Go Live)

#### 📦 방법 A: PyPI에서 정식 설치 (추천)
가장 안정적인 최신 릴리스 버전을 설치합니다.
```bash
# 파이썬 버전 확인 후 설치
python3 -m pip install --upgrade bi-agent

# 어디서든 실행
bi-agent
```

#### 🛠️ 방법 B: GitHub 소스 설치
개발 버전이나 직접 소스 코드를 수정하고 싶다면:
```bash
# 깃허브에서 직접 설치
pip install git+https://github.com/KnellBalm/BI-Agent.git

# 또는 로컬 소스 폴더에서 설치 (개발자용)
git clone https://github.com/KnellBalm/BI-Agent.git
cd BI-Agent
pip install -e .
npm install
```

> [!IMPORTANT]
> **설치 오류 발생 시**: `ERROR: Could not find a version...` 에러가 난다면, 현재 실행된 `pip` 명령어가 Python 3.10 이상 버전에 연결되어 있는지 확인해 주세요. `python3 -m pip install bi-agent` 명령어가 가장 확실한 방법입니다.

---

## 🏛️ Entrance Hall (지능형 관문)
패키지 설치 후 `bi-agent`를 실행하면 고도화된 **Entrance Hall** UI가 실행됩니다.
- **슬래시 명령어 (/)**: `/`를 입력하여 분석 명령어 팔레트 호출
- **실시간 사고 로그**: 에이전트의 내부 추론 과정과 시스템 로그를 채팅창 하단에서 실시간 모니터링
- **지능형 온보딩**: API 키가 없어도 실행 중 보안 가이드에 따라 즉시 등록 가능

---

## 🛠️ Technical Excellence

| Layer | Technologies |
| :--- | :--- |
| **Intelligence** | Gemini 2.0, Claude 3.5, GPT-4o, Ollama, LangGraph |
| **Interface** | **Premium TUI (Textual)**, Real-time Quota Dashboard |
| **Data Engine** | DuckDB, Pandas, Postgres, MySQL, SQLite, Excel |
| **Connectivity** | **Model Context Protocol (MCP)**, Node.js |
| **Aesthetics** | CSS Glassmorphism, Google Fonts (Outfit/Inter) |
| **Testing** | pytest (94% coverage), ruff, mypy, black |
| **Architecture** | Multi-Agent Orchestrator, Component-Based Design |

---

---

## ❓ Troubleshooting (자주 묻는 질문)

**Q. `ERROR: Could not find a version that satisfies the requirement bi-agent` 에러가 발생합니다.**
- **A**: 이 프로젝트는 **Python 3.10 이상**이 필요합니다. 현재 사용 중인 `pip`가 3.9 이하의 파이썬 버전에 연결되어 있을 때 발생하는 메시지입니다. `python3 --version`으로 버전을 확인하신 후, `python3 -m pip install bi-agent` 명령어로 재시도해 보세요.

**Q. `bi-agent` 명령어를 찾을 수 없다고 나옵니다.**
- **A**: `pip` 설치 시 `--user` 옵션으로 설치된 경우 관련 디렉토리가 `PATH`에 등록되어 있지 않을 수 있습니다. 터미널을 재시작하거나, `$HOME/.local/bin`이 환경변수에 포함되어 있는지 확인해 주세요.

---

## 📖 Related Documents

* [**MASTER_SPEC.md**](./docs/BI_AGENT_MASTER_SPEC.md): 상세 기술 명세서
* [**PLAN.md**](./docs/PLAN.md): 로드맵 및 설계 철학
* [**USER_GUIDE.md**](./docs/guides/USER_GUIDE.md): 기능 활용 가이드

---

Copyright © 2026 BI-Agent Team. All rights reserved.
