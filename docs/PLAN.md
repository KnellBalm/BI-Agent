# BI-Agent 시스템 고도화 및 구현 계획 (Roadmap)

## 1. 프로젝트 개요

### 목표
**"BI 메타데이터 지능화와 시각화 설계를 자율화하는 전술적 AI Agent"**
단순한 데이터 추출을 넘어, Tableau(`.twbx`), Power BI(`.pbix`) 등의 메타데이터를 직접 조정하고, 도구별 전문 계산식(DAX, LOD) 생성 및 UI 가이드 지원을 통해 BI 운영의 복잡도를 획기적으로 낮춥니다.

### 핵심 가치
- **Metadata Intelligence**: BI 툴 내부 구조(XML/JSON)를 이해하고 직접 수정하는 능력.
- **Design & Logic Builder**: 고도의 시각화 설계 역량과 복잡한 계산식 전문성.
- **Guide & UI Assistant**: 방대한 BI 도구 문서를 기반으로 사용자 가이드 제공.
- **Universal Connectivity**: MCP를 통한 원활한 데이터 공급 (기존 자산 활용).

---

## 2. 시스템 아키텍처

### 2.1 Multi-Agent & Interface 구조

```mermaid
graph TD
    User([User]) --> Interface[TUI / CLI / Web UI]
    Interface --> Orchestrator{Orchestrator Agent}
    
    subgraph Agents [Specialized Agents]
        Orchestrator --> DSA[Data Source Agent]
        Orchestrator --> BIA[BI Tool Agent]
    end
    
    subgraph Connectivity [MCP Tools Layer]
        DSA --> MCP_SaaS[Snowflake / BigQuery]
        DSA --> MCP_Local[Postgres / MySQL / Excel]
        DSA --> S3[Amazon S3 File Reader]
    end
    
    subgraph Automation [BI Intelligence Layer]
        BIA --> XML[Tableau .twbx XML]
        BIA --> DAX[Power BI DAX/Logic]
        BIA --> Guide[UI/Guide RAG]
    end
    
    subgraph Intelligence [LLM Quota Management]
        Orchestrator -.-> QM[Quota Manager]
        QM --> Gemini_Free[Gemini Free Tier]
        QM --> Gemini_Paid[Gemini Paid Tier]
        QM --> Ollama[Local Ollama Backup]
    end
```

### 2.2 기술 스택
- **Backend / Agent**: Python (LangGraph, PydanticAI, pandas)
- **Protocol**: Model Context Protocol (MCP) - Node.js 기반 서버 레이어
- **LLM Provider**: Google Gemini (Main), Ollama (Local/Air-gap backup)
- **Interface**: **TUI (Rich/Textual)**, CLI (npx global 지원), React (Future)
- **Data & Ops**: Snowflake, BigQuery, S3, PostgreSQL, MySQL, Apache Airflow

---

## 3. 구현 단계 (Phases)

### Phase 1: 기반 구축 (Completed)
- [x] 프로젝트 구조 및 환경 설정 (`venv`, `dotenv`)
- [x] 기본적인 멀티 에이전트 구조 및 Orchestrator 설계
- [x] PostgreSQL/MySQL MCP 서버 연동 및 기본 쿼리 테스트
- [x] Gemini API 연동 및 Quota 관리 기초 구현

### Phase 2: 기능 확장 및 TUI 도입 (Completed/Finalizing)
- [x] Excel 데이터 소스 지원 (`excel-mcp-server`)
- [x] **TUI (Terminal UI) 프로토타입** 구현 (`rich` 라이브러리 활용)
- [x] Docker 기반 MySQL 테스트 환경 최적화 및 연동 검증
- [x] `.env.example` 및 상세 가이드 문서화 (`docs/SETUP_GUIDE.md`)

### Phase 3: 기능 고도화 및 지능형 오케스트레이션 (In-Progress)
- **SaaS & Cloud Connectivity**:
  - [ ] Snowflake 및 BigQuery 전용 커넥터 연동
  - [ ] Amazon S3 버킷 내 파일(CSV/Parquet) 직접 분석 기능
- **Billing Sovereignty (과금 제어)**:
  - [ ] `Quota Manager` 고도화: 무료 키 소진 시 유료 키/Ollama 자동 로테이션
  - [ ] 트큰 사용량 모니터링 및 실시간 비용 리포팅
- **BI Metadata Intelligence**:
  - [ ] **Tableau Metadata (.twbx XML)**: 파일 내 데이터 바인딩 및 시각화 속성 수정 기능
  - [ ] **Power BI Logic (DAX)**: 복잡한 DAX 쿼리 및 파워 쿼리 M 문법 자동 생성 지원
- **UI & Guide Support**:
  - [ ] BI 도구(Tableau, Power BI) 공식 가이드를 활용한 UI 조작 도우미 (RAG 기반)
- **Agent Intelligence**:
  - [ ] 비즈니스 도메인 지식 주입 및 Few-shot SQL 생성 최적화 (SaaS 포함)
  - [ ] BI JSON/XML 명세서의 지능형 오류 교정 및 스타일 튜닝

### Phase 4: 패키징 및 글로벌 배포 (Planning)
- **Distribution**:
  - [ ] **NPM Global 패키지 배포**: `npm install -g bi-agent` 지원
  - [ ] 경량화 전략: Node.js 래퍼 + 동적 Python 엔진 설치 방식 적용
- **Production Readiness**:
  - [ ] 에러 핸들링 고도화 (Self-healing logic 강화)
  - [ ] 보안 강화 (DB Credential 관리, API Key 암호화)
  - [ ] 상세 사용자 가이드 및 API 문서 완성

---

## 4. 핵심 컴포넌트 상세

### Quota Manager (과금 방지)
- **목표**: 0원에 수렴하는 운영 비용 관리
- **기능**:
  - `GEMINI_API_KEYS`의 할당량을 실시간 추적
  - 무료 티어 키들을 순환(Rotation)시키며 활용 극대화
  - 모든 API 키 소진 시 로컬 Ollama 모델로 자동 Failover

### TUI Interface (경험의 혁신)
- **목표**: 터미널 기반의 전문적인 분석 워크스페이스 제공
- **기능**:
  - Agent의 사고 과정(Chain of Thought) 시각화
  - 데이터 테이블 프리뷰 및 분석 결과 실시간 스트리밍
  - 한글 입력 및 다국어 지원 최적화

---

## 5. 리스크 및 대응 전략

| 리스크 | 영향도 | 대응 방안 |
|:---:|:---:|:--- |
| **과금 위험** | 높음 | Quota Manager를 통한 임계치 설정 및 차단 |
| **데이터 보안** | 높음 | 로컬 DB 접근 권한 분리 및 환경 변수 암호화 |
| **복잡한 쿼리 오류** | 중간 | Self-healing (오류 로그 분석 후 재시도) 로직 적용 |
| **설치 편의성** | 낮음 | npx 및 글로벌 CLI 배포를 통한 원클릭 환경 구축 |

---

## 6. 예상 타임라인 (Re-evaluated)

- **1~2주차**: (완료) 아키텍처 수립 및 로컬 DB 연동
- **3~4주차**: (현재) TUI 고도화, 과금 관리 로직, SaaS 연동
- **5~6주차**: Airflow PoC 및 BI JSON 수정 자동화
- **7주차**: 패키징 및 최종 검증

---
Copyright © 2026 BI-Agent Team. All rights reserved.
