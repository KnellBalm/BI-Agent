# BI Agent 시스템 POC 구현 계획

## 1. 프로젝트 개요

### 목표
Business Intelligence(BI) 작업을 자동화하는 Multi-Agent 시스템 구축. 사용자는 자연어로 데이터 분석 요청을 하고, Agent가 데이터 소스 연결, 쿼리 실행, BI 대시보드 수정을 자동으로 수행합니다.

### POC 범위
- Excel/PostgreSQL/MySQL 데이터 소스 연결
- 회사 BI 솔루션 JSON 파일 분석 및 수정
- 웹 UI를 통한 자연어 인터페이스
- 기본적인 멀티 Agent 오케스트레이션

### 기술 스택
- **Backend**: Python (Agent 로직, 데이터 처리) + Node.js (MCP 서버)
- **LLM**: Google Gemini (Free & Paid Tier 병용) + Ollama (폐쇄망용 백업)
  - *과금 방지*: Quota Manager를 통한 키 로테이션 및 예산 초과 방지
- **프로토콜**: Model Context Protocol (MCP)
- **SaaS/Cloud**: Snowflake, Google BigQuery, Amazon S3
- **Orchestration**: Apache Airflow
- **Interface**: TUI (Terminal User Interface) & CLI + MCP Server

---

## 2. 시스템 아키텍처

### 2.1 Multi-Agent 구조

```
┌─────────────────────────────────────────────────────┐
│                   Web UI (React)                     │
│              (자연어 입력 + 결과 표시)                 │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP/WebSocket
┌──────────────────────▼──────────────────────────────┐
│           Orchestrator Agent (Python)                │
│         - 사용자 의도 파악                            │
│         - Sub-Agent 선택 및 호출                      │
│         - 결과 통합 및 응답 생성                       │
└─────┬─────────────────────────────┬─────────────────┘
      │                             │
      │                             │
┌─────▼─────────────────┐  ┌────────▼────────────────┐
│ Data Source Agent     │  │ BI Tool Agent           │
│ (Python)              │  │ (Python/Node.js)        │
│                       │  │                         │
│ - DB 쿼리 실행          │  │ - JSON 파싱/수정          │
│ - Excel 파일 읽기       │  │ - 대시보드 업데이트         │
│ - 데이터 변환            │  │ - 시각화 설정             │
└─────┬─────────────────┘  └────────┬────────────────┘
      │                              │
      │ MCP Protocol                 │ File I/O
      │                              │
┌─────▼──────────────────────────────▼────────────────┐
│              MCP Tools Layer                         │
│                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │ PostgreSQL   │  │ MySQL        │  │ Excel     │  │
│  │ MCP Server   │  │ MCP Server   │  │ MCP Server│  │
│  └──────────────┘  └──────────────┘  └───────────┘  │
└──────────────────────────────────────────────────────┘
          │                  │                │
          ▼                  ▼                ▼
      PostgreSQL          MySQL           Excel Files
```

### 2.2 컴포넌트 설명

#### Orchestrator Agent (핵심)
- **역할**: 전체 워크플로우 조율
- **기능**:
  - 사용자 요청 분석 (예: "최근 3개월 매출 추이를 보여줘")
  - 필요한 Sub-Agent 결정
  - 작업 순서 결정 (데이터 조회 → 분석 → 시각화)
  - 결과 통합 및 자연어 응답 생성
- **구현**: Python + LangGraph (Agent workflow framework)

#### Data Source Agent
- **역할**: 데이터 소스 접근 및 쿼리 실행
- **기능**:
  - MCP 서버를 통한 DB 연결
  - SQL 쿼리 생성 및 실행
  - Excel 파일 읽기/쓰기
  - 데이터 전처리 (pandas)
- **구현**: Python + MCP Client

#### BI Tool Agent
- **역할**: 회사 BI 솔루션 제어
- **기능**:
  - JSON 파일 파싱 (connector, datamodel, visual, report)
  - 데이터 모델 수정 (필드 추가, 쿼리 변경)
  - 시각화 설정 업데이트 (차트 타입, 옵션)
  - REST API를 통한 데이터 조회
- **구현**: Python (JSON 처리) + Node.js (REST API 호출)

---

## 3. BI JSON 구조 분석

사용자가 제공한 `tmp/20260120.json` 분석 결과:

### 주요 엔티티

| 엔티티 | 설명 | Agent 활용 |
|--------|------|-----------|
| `connector` | DB 연결 정보 (host, port, user, password) | Data Source Agent가 읽어서 DB 접속 |
| `datamodel` | 데이터 모델 (fields, dataset.query) | BI Tool Agent가 수정하여 새 필드/쿼리 추가 |
| `visual` | 시각화 설정 (type, etc에 Base64 옵션) | BI Tool Agent가 차트 타입/옵션 변경 |
| `report` | 대시보드 메타데이터 (name, dashboard) | BI Tool Agent가 리포트 정보 업데이트 |
| `image` | 썸네일 이미지 (Base64) | 향후 이미지 생성 시 사용 |

### 샘플 데이터모델 구조

```json
{
  "id": "d9f57cd9-7a0e-4c6a-8628-25fd20d2c5ab",
  "name": "유동인구_월별_동별_총계_지도_2",
  "fields": [
    {"name": "year_month", "type": "TEXT"},
    {"name": "total", "type": "INTEGER"},
    {"name": "admi_cd", "type": "TEXT"}
  ],
  "dataset": {
    "format": "view",
    "query": "*| sql \"select * from table\" | calculate total/1000 as total"
  },
  "connector_id": "",
  "referenced_id": "61b57294-6f07-48a0-8801-cbfd3648d57c"
}
```

### Agent 작업 예시

**사용자 요청**: "2024년 유동인구 데이터에 '여성비율' 필드를 추가해줘"

1. **Orchestrator**: 요청 분석 → BI Tool Agent 호출
2. **BI Tool Agent**:
   - JSON 파일 로드
   - `datamodel` 배열에서 "유동인구" 키워드 검색
   - `fields`에 `{"name": "female_ratio", "type": "FLOAT"}` 추가
   - `dataset.query`에 `calculate female/total as female_ratio` 추가
   - JSON 파일 저장
3. **Orchestrator**: "여성비율 필드가 추가되었습니다" 응답

---

## 4. 구현 단계

### Phase 1: 기반 구축 (1주)

#### 1.1 프로젝트 초기화
```bash
BI-Agent/
├── backend/
│   ├── orchestrator/       # Orchestrator Agent (Python)
│   ├── agents/
│   │   ├── data_source/    # Data Source Agent (Python)
│   │   └── bi_tool/        # BI Tool Agent (Python)
│   ├── mcp_servers/        # MCP 서버들 (Node.js)
│   └── requirements.txt
├── frontend/               # React 웹 UI
└── docs/                   # 문서
```

#### 1.2 MCP 서버 설정
- **PostgreSQL MCP**: `@modelcontextprotocol/server-postgres` 설치
- **MySQL MCP**: 커스텀 MCP 서버 또는 기존 라이브러리 활용
- **Excel MCP**: `negokaz/excel-mcp-server` 또는 `haris-musa/excel-mcp-server` 설치

#### 1.3 LLM 통합
- Google Gemini API 키 설정
- `google-generativeai` Python SDK 설치
- 향후 Ollama 지원을 위한 추상화 레이어 설계 (LLM Provider 인터페이스)

```python
# llm_provider.py
class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        pass

class GeminiProvider(LLMProvider):
    def generate(self, prompt: str) -> str:
        # Gemini API 호출
        pass

class OllamaProvider(LLMProvider):
    def generate(self, prompt: str) -> str:
        # Ollama API 호출
        pass
```

### Phase 2: Agent 구현 (2주)

#### 2.1 Data Source Agent
- MCP Client 구현 (Python)
- 쿼리 생성 로직 (자연어 → SQL)
- Excel 파일 처리 (pandas + openpyxl)

```python
# data_source_agent.py
class DataSourceAgent:
    def __init__(self, mcp_client):
        self.mcp_client = mcp_client

    def query_database(self, connector_id: str, query: str) -> pd.DataFrame:
        # MCP를 통해 DB 쿼리 실행
        pass

    def read_excel(self, file_path: str) -> pd.DataFrame:
        # Excel 파일 읽기
        pass
```

#### 2.2 BI Tool Agent
- JSON 파일 파싱 (connector, datamodel, visual, report)
- 데이터 모델 수정 API
- 시각화 설정 업데이트 (Base64 디코딩/인코딩)

```python
# bi_tool_agent.py
class BIToolAgent:
    def __init__(self, json_path: str):
        self.json_path = json_path
        self.data = self.load_json()

    def load_json(self) -> dict:
        with open(self.json_path, 'r') as f:
            return json.load(f)

    def add_field_to_datamodel(self, model_name: str, field: dict):
        # datamodel 찾기 → fields 배열에 추가
        pass

    def update_query(self, model_name: str, new_query: str):
        # dataset.query 수정
        pass

    def save_json(self):
        with open(self.json_path, 'w') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
```

#### 2.3 Orchestrator Agent
- LangGraph를 사용한 Agent workflow
- 사용자 의도 분류 (데이터 조회 / BI 수정 / 혼합)
- Sub-Agent 호출 및 결과 통합

```python
# orchestrator.py
from langgraph.graph import StateGraph

class Orchestrator:
    def __init__(self, llm_provider, data_agent, bi_agent):
        self.llm = llm_provider
        self.data_agent = data_agent
        self.bi_agent = bi_agent
        self.graph = self.build_graph()

    def build_graph(self):
        workflow = StateGraph()
        workflow.add_node("classify", self.classify_intent)
        workflow.add_node("data_task", self.handle_data_task)
        workflow.add_node("bi_task", self.handle_bi_task)
        workflow.add_node("respond", self.generate_response)
        # ... edge 정의
        return workflow.compile()

    def classify_intent(self, state):
        prompt = f"사용자 요청: {state['user_input']}\n분류: [DATA_QUERY, BI_MODIFY, BOTH]"
        intent = self.llm.generate(prompt)
        state['intent'] = intent
        return state

    def handle_data_task(self, state):
        # Data Source Agent 호출
        result = self.data_agent.query_database(...)
        state['data_result'] = result
        return state

    def handle_bi_task(self, state):
        # BI Tool Agent 호출
        self.bi_agent.add_field_to_datamodel(...)
        state['bi_result'] = "필드 추가 완료"
        return state
```

### Phase 3: 기능 고도화 및 검증 (2주)

> 모든 데이터 소스와 BI 수정 기능을 완벽하게 구현하고 검증하는 단계

#### 3.1 기능 고도화 (SaaS & Cloud)
- [ ] **SaaS 연동**: Snowflake, BigQuery MCP 서버 연동 및 쿼리 테스트
- [ ] **Cloud Storage**: Amazon S3 내의 CSV/Excel 데이터 직접 조회 기능
- [ ] **MySQL 연동 검증**: Docker MySQL 컨테이너 환경 최적화

#### 3.2 UI/UX 혁신 (TUI)
- [ ] **TUI (Terminal User Interface) 기반 에이전트 구현**:
  - `rich` 또는 `textual` 라이브러리를 사용한 인터랙티브 터미널 UI
  - 데이터 스트리밍 로그, Agent 사고 과정 시각화
  - 터미널 내 데이터 테이블 프리뷰

#### 3.3 워크플로우 자동화 및 과금 관리
- [ ] **Quota Manager 고도화**:
  - Free Tier 키와 Paid Tier 키의 우선순위 자동 조정
  - 일일 할당량 도달 시 자동 중지 또는 로컬 Ollama 전환 로직
- [ ] **Airflow 활용 방안 수립**:
  - Agent가 생성한 쿼리를 Airflow DAG로 자동 변환/등록하는 PoC
  - 데이터 파이프라인 상태 모니터링 연동

#### 3.4 BI Tool Agent 및 에러 핸들링
- [ ] **BI Tool Agent 강화**: Base64 시각화 및 복잡한 필드 로직 지원
- [ ] **안정성**: DB 연결 및 쿼리 실패 시 자동 복구(Self-healing) 로직 시도

#### 3.2 통합 테스트 (CLI 중심)
- [ ] PostgreSQL + MySQL + Excel 교차 질의 테스트
- [ ] 대규모 BI JSON 파일 처리 성능 및 안정성 테스트
- [ ] `backend/main.py`를 통한 전체 시나리오 검증

### Phase 4: 패키징 및 배포 (1주)

> 완성된 에이전트를 외부에서 쉽게 사용할 수 있도록 패키징

#### 4.1 MCP 서버 패키지화
- [ ] `bin/bi-agent-mcp.js` 안정화
- [ ] `backend/mcp_bridge.py` 기능 확장 (모든 신규 기능 포함)
- [ ] npm 패키지 설정 (`package.json`) 및 퍼블리시 준비

#### 4.2 배포 및 가이드
- [ ] npx를 통한 설치 없는 실행 가이드
- [ ] Claude Desktop / Cursor 연동 가이드 최신화
- [ ] Docker 이미지 빌드 및 레지스트리 푸시 (필요 시)

---

## 5. 핵심 파일 및 경로

### 구현 필요 파일
```
backend/
├── orchestrator/
│   ├── main.py                    # Orchestrator 엔트리포인트 (CLI)
│   ├── orchestrator.py            # Orchestrator Agent 로직
│   └── connection_manager.py      # 데이터 연결 관리
├── agents/
│   ├── data_source/
│   │   ├── data_source_agent.py   # Data Source Agent
│   │   ├── mcp_client.py          # MCP Client 래퍼
│   │   └── sql_generator.py       # SQL 생성기
│   └── bi_tool/
│       ├── bi_tool_agent.py       # BI Tool Agent
│       ├── json_parser.py         # JSON 파서
│       └── visual_decoder.py      # Base64 시각화 옵션 디코더
├── mcp_servers/                   # 기반 MCP 서버들 (JS)
└── mcp_bridge.py                  # Node.js ↔ Python 브릿지 (배포용)

bin/
└── bi-agent-mcp.js                # npx 엔트리포인트 (배포용)
```

### 기존 파일
- `/Users/zokr/python_workspace/BI-Agent/tmp/20260120.json`: 회사 BI 솔루션 JSON (분석 완료)

---

## 6. 검증 방법

### 6.1 기능 검증
1. **MCP 연결 테스트**
   - PostgreSQL 쿼리 실행 성공
   - MySQL 쿼리 실행 성공
   - Excel 파일 읽기 성공

2. **Agent 동작 테스트**
   - Data Source Agent: SQL 생성 및 실행
   - BI Tool Agent: JSON 파일 수정 및 저장
   - Orchestrator: Sub-Agent 조율 및 응답 생성

3. **엔드투엔드 테스트**
   - 웹 UI에서 자연어 입력
   - 백엔드 Agent 실행
   - 결과 표시 (데이터 테이블 또는 성공 메시지)

### 6.2 성능 검증 (POC 후)
- 응답 시간: 일반 쿼리 < 5초
- JSON 파일 처리: 대용량 파일 (>1MB) < 3초

---

## 7. Future Plan (POC 이후)

### 7.1 Ollama 통합 (폐쇄망 대응)
- `llm_provider.py`에 `OllamaProvider` 추가
- 로컬 모델 다운로드 및 실행 가이드
- 성능 비교 (Gemini vs Ollama)

### 7.2 Tableau 연동
- Tableau REST API를 사용한 대시보드 관리
- Hyper API를 통한 데이터 주입
- 새로운 `TableauAgent` 구현

### 7.3 고급 기능
- 자연어 → SQL 변환 정확도 향상 (few-shot learning)
- 시각화 자동 추천 (데이터 특성 기반)
- 대시보드 버전 관리 (Git 연동)
- 멀티유저 지원 (권한 관리)

### 7.4 프로덕션 준비
- 에러 핸들링 및 로깅 (Sentry, ELK)
- 보안 강화 (인증, 권한, DB 비밀번호 암호화)
- 테스트 커버리지 80% 이상
- Docker 컨테이너화
- CI/CD 파이프라인 구축

---

## 8. 리소스 및 참고 자료

### MCP 서버
- [PostgreSQL MCP Server](https://github.com/modelcontextprotocol/servers)
- [Excel MCP Server by negokaz](https://github.com/negokaz/excel-mcp-server)
- [Excel MCP Server by haris-musa](https://github.com/haris-musa/excel-mcp-server)
- [MindsDB MCP Server](https://mindsdb.com/unified-model-context-protocol-mcp-server-for-databases)

### LLM & Agent Framework
- [Google Gemini API](https://ai.google.dev/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)

### Frontend
- [React Documentation](https://react.dev/)
- [Chart.js](https://www.chartjs.org/)

---

## 9. 예상 타임라인

| 주차 | 작업 | 산출물 |
|------|------|--------|
| 1주차 | 프로젝트 초기화, MCP 서버 설정, LLM 통합 | 실행 가능한 기본 구조 |
| 2주차 | Data Source Agent 구현 | DB 쿼리 실행 가능 |
| 3주차 | BI Tool Agent 구현 | JSON 파일 수정 가능 |
| 4주차 | Orchestrator 구현 | Agent 조율 동작 |
| 5주차 | 웹 UI 구현 | 사용자 인터페이스 완성 |
| 6주차 | 테스트 및 문서화 | POC 완성 |

**총 기간**: 6주 (POC)

---

## 10. 위험 요소 및 대응

| 위험 | 영향 | 대응 방안 |
|------|------|----------|
| Gemini API 할당량 초과 | Agent 응답 불가 | API 키 모니터링, 캐싱, Ollama 백업 |
| BI JSON 스키마 변경 | JSON 파싱 오류 | 스키마 버전 관리, 유연한 파서 설계 |
| MCP 서버 호환성 문제 | DB 연결 실패 | 커스텀 MCP 서버 구현 준비 |
| 복잡한 자연어 요청 처리 | 잘못된 Agent 호출 | 명확한 프롬프트 엔지니어링, few-shot examples |

---

## Sources

- [GitHub - modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers)
- [MindsDB MCP Server](https://mindsdb.com/unified-model-context-protocol-mcp-server-for-databases)
- [PostgreSQL MCP Server](https://www.pulsemcp.com/servers/modelcontextprotocol-postgres)
- [Excel MCP Server by negokaz](https://github.com/negokaz/excel-mcp-server)
- [Excel MCP Server by haris-musa](https://github.com/haris-musa/excel-mcp-server)
- [MCP Examples](https://modelcontextprotocol.io/examples)
