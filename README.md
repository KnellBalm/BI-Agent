<h1 align="center">BI-Agent: The Frontier of Autonomous Business Intelligence</h1>

<p align="center">
  <strong>"데이터 오퍼레이션을 넘어, 비즈니스 인사이트의 자율화를 설계하는 아키텍트"</strong><br />
  BI-Agent는 단순한 데이터 추출 도구를 넘어, 기업의 데이터 자산을 스스로 탐색하고<br />
  <strong>차세대 의사결정 시스템(Autonomous BI)</strong>을 위한 완벽한 지능형 오케스트레이션을 제공합니다.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Status-POC--Stage-orange?style=for-the-badge&logo=statuspage" alt="Status" />
  <img src="https://img.shields.io/badge/Powered%20By-Gemini%202.0%20Flash-4285F4?style=for-the-badge&logo=google-gemini" alt="Gemini" />
  <img src="https://img.shields.io/badge/Protocol-MCP-green?style=for-the-badge" alt="MCP" />
  <img src="https://img.shields.io/badge/Architecture-Multi--Agent-blue?style=for-the-badge" alt="Architecture" />
</p>

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
- **Failover LLM Provider**: Google Gemini(Primary)와 Ollama(Secondary)를 결합하여 안정적인 지능을 유지합니다.
- **Plan B Logic**: 데이터 연결이 끊긴 상황에서도 사용자 의도를 기반으로 '가상 스키마'를 추론하여 분석을 지속합니다.

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
- Python 3.10+, Node.js 18+ 설치
- `.env.example`을 참고하여 `.env` 생성 및 Gemini API 키 입력

### 2단계: 설치 및 실행 (Go Live)

> [!NOTE]
> 현재 `bi-agent`는 PyPI에 등록되어 있지 않습니다. 아래의 방법을 통해 설치해 주세요.

#### 방법 A: GitHub에서 직접 설치 (추천)
다른 사용자라면 터미널에서 다음 명령어를 실행하여 설치할 수 있습니다:
```bash
pip install git+https://github.com/KnellBalm/BI-Agent.git
```

#### 방법 B: 로컬 소스 코드로 설치 (개발자용)
레포지토리를 클론한 상태라면 디렉토리 내부에서 다음을 실행합니다:
```bash
# 1. 의존성 및 패키지 설치
pip install -e .
npm install  # MCP 서버 기능 사용 시 필요

# 2. 실행 (어디서든 'bi-agent' 명령어로 실행 가능)
bi-agent
```

---

## 🛠️ Technical Excellence

| Layer | Technologies |
| :--- | :--- |
| **Intelligence** | LangGraph, Gemini 2.0 Flash, Ollama, PydanticAI |
| **Interface** | **Premium TUI (Rich)**, Interactive Dashboard (Plotly) |
| **Data Engine** | DuckDB, Pandas, Postgres, Snowflake, BigQuery |
| **Connectivity** | **Model Context Protocol (MCP)**, Node.js |
| **Aesthetics** | CSS Glassmorphism, Google Fonts (Outfit/Inter) |

---

## 📖 Related Documents

* [**MASTER_SPEC.md**](./docs/BI_AGENT_MASTER_SPEC.md): 상세 기술 명세서
* [**PLAN.md**](./docs/PLAN.md): 로드맵 및 설계 철학
* [**USER_GUIDE.md**](./docs/USER_GUIDE.md): 기능 활용 가이드

---

Copyright © 2026 BI-Agent Team. All rights reserved.
