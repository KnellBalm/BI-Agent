# BI-Agent MVP Work Plan: Natural Language to BI Meta JSON

> **Plan Created**: 2026-01-23
> **Timeline**: 1 Week (7 Days)
> **Priority**: MVP Speed-First

---

## 1. Context Summary

### 1.1 Original Request
자연어 질문을 받으면 사용자가 사용하는 BI 솔루션의 메타데이터 JSON을 생성해주는 MVP

### 1.2 Interview Summary

| Question | Answer |
|----------|--------|
| Business Priority | Speed (MVP First) |
| Claude Features | A. Tableau Metadata Engine, B. Power BI Intelligence |
| Antigravity Features | E. Ask Mode RAG, F. Premium TUI v2 |
| Timeline | 1 Week (focused but breathing room) |
| BI Tool Focus | Tableau First, Power BI Later |
| Data Sources | Existing DBs (PostgreSQL:5433, MySQL:3307) |
| UX Depth | Minimal UI First |
| Success Scenario | "자연어 질문 -> BI 메타 JSON 생성" |

### 1.3 Research Findings (Codebase Analysis)

**Existing Components (Reusable)**:
- `TableauMetadataEngine`: Basic XML parsing for .twb files (fields, datasources)
- `PBILogicGenerator`: DAX template generation (YoY, MTD patterns)
- `GuideAssistant`: Static knowledge base for UI guides (Ask Mode)
- `InteractionOrchestrator`: Mode detection (ask/agent), tool routing
- `main.py` + `tui_interface.py`: Rich-based TUI already working
- `BIToolAgent`: JSON-based BI metadata modification

**Gaps to Fill**:
1. No "Natural Language -> Meta JSON" pipeline
2. Tableau engine needs enhancement (worksheets, calculated fields)
3. No RAG vector store for BI docs
4. TUI lacks meta JSON preview/export

---

## 2. Work Objectives

### 2.1 Core Objective
Build an end-to-end pipeline: **Natural Language Query -> Tableau Meta JSON Output**

### 2.2 Deliverables

| # | Deliverable | Role | Priority |
|---|-------------|------|----------|
| D1 | Tableau Meta JSON Generator | Claude | P0 |
| D2 | NL-to-Intent Parser | Claude | P0 |
| D3 | Basic RAG Knowledge Base | Antigravity | P1 |
| D4 | TUI Meta Preview Panel | Antigravity | P1 |
| D5 | Power BI DAX JSON (Stub) | Claude | P2 |
| D6 | Enhanced TUI (CoT Display) | Antigravity | P2 |

### 2.3 Definition of Done

MVP is complete when:
1. User types natural language in TUI (e.g., "월별 매출 차트를 만들어줘")
2. System generates valid Tableau-compatible meta JSON
3. JSON includes: datasource, fields, calculated fields, visual type
4. Output can be previewed in TUI and exported to file

---

## 3. Guardrails

### 3.1 MUST HAVE (P0)

- [ ] Tableau XML -> Meta JSON 변환 파이프라인
- [ ] 자연어 의도 분석 (LLM 기반)
- [ ] 기본 TUI 입출력 흐름
- [ ] 최소 3개 시각화 타입 지원 (bar, line, table)
- [ ] PostgreSQL/MySQL 스키마 연동

### 3.2 MUST NOT HAVE (Scope Exclusion)

- Power BI .pbix 바이너리 파싱 (JSON 템플릿만)
- Cloud BI (Looker, QuickSight) - Phase 4
- Airflow DAG 생성 - Phase 4
- Self-Healing 로직 - Post-MVP
- 복잡한 계산 필드 (단순 SUM, AVG만)

### 3.3 Technical Constraints

- Python 3.14 runtime (existing venv)
- LLM: Gemini (primary) / Ollama (fallback)
- No external vector DB (use local FAISS or simple search)
- Existing DB connections (5433/3307 ports)

---

## 4. Task Flow and Dependencies

```
[Day 1-2: Foundation]
    T1: Tableau Meta Schema Design ─────┐
    T2: NL Intent Parser (LLM Prompt)───┼──> [Day 3-4: Integration]
    T3: RAG Knowledge Base Setup ───────┘       T5: Pipeline Integration
                                                 T6: TUI Preview Panel
                                                      │
                                                      v
                                           [Day 5-7: Polish & Demo]
                                                 T7: End-to-End Testing
                                                 T8: Bug Fixes & Demo Prep
```

### Dependency Map

| Task | Depends On | Blocks |
|------|------------|--------|
| T1 (Schema) | - | T5 |
| T2 (Intent Parser) | - | T5 |
| T3 (RAG Setup) | - | T6 |
| T4 (DAX Stub) | T1 | - |
| T5 (Pipeline) | T1, T2 | T7 |
| T6 (TUI Preview) | T3, T5 | T7 |
| T7 (Testing) | T5, T6 | T8 |
| T8 (Demo) | T7 | - |

### Critical Path
**T1 -> T5 -> T7 -> T8** (Tableau Meta Generation은 MVP의 핵심)

---

## 5. Detailed Task Breakdown

### Day 1-2: Foundation (Parallel Work)

---

#### T1: Tableau Meta JSON Schema Design [Claude] [P0]
**File**: `backend/agents/bi_tool/tableau_meta_schema.py`

**Description**:
Tableau 메타데이터를 표준 JSON 포맷으로 정의. 기존 `TableauMetadataEngine`을 확장.

**Acceptance Criteria**:
- [ ] Meta JSON schema 정의 (datasources, fields, worksheets, visuals)
- [ ] `TableauMetadataEngine.to_meta_json()` 메서드 추가
- [ ] 기존 .twb 파일에서 메타 추출 테스트
- [ ] 빈 템플릿 생성 기능 (`create_empty_meta()`)

**Sample Output Schema**:
```json
{
  "version": "1.0",
  "tool": "tableau",
  "datasources": [
    {
      "name": "SalesData",
      "connection": {"type": "postgres", "table": "sales"},
      "fields": [
        {"name": "OrderDate", "type": "date", "role": "dimension"},
        {"name": "Sales", "type": "number", "role": "measure", "aggregation": "SUM"}
      ]
    }
  ],
  "worksheets": [
    {
      "name": "Monthly Sales",
      "visual_type": "bar",
      "dimensions": ["OrderDate"],
      "measures": ["Sales"]
    }
  ],
  "calculated_fields": []
}
```

**Estimated Effort**: 3-4 hours

---

#### T2: Natural Language Intent Parser [Claude] [P0]
**File**: `backend/agents/bi_tool/nl_intent_parser.py`

**Description**:
LLM을 사용하여 자연어 질문을 구조화된 의도(intent)로 변환.

**Acceptance Criteria**:
- [ ] Intent 타입 정의 (create_chart, modify_field, add_filter, etc.)
- [ ] LLM 프롬프트 템플릿 작성
- [ ] 의도 추출 함수 구현 (`parse_intent(user_input) -> Intent`)
- [ ] 5개 이상의 자연어 입력 테스트

**Intent Structure**:
```python
@dataclass
class ChartIntent:
    action: str  # "create", "modify", "delete"
    visual_type: str  # "bar", "line", "pie", "table"
    datasource: str
    dimensions: List[str]
    measures: List[str]
    filters: List[dict]
    title: Optional[str]
```

**Sample Prompt Template**:
```
You are a BI assistant. Parse the user's request into structured intent.

User: "월별 매출 추이를 보여주는 라인 차트를 만들어줘"

Output JSON:
{
  "action": "create",
  "visual_type": "line",
  "dimensions": ["month"],
  "measures": ["sales"],
  "title": "월별 매출 추이"
}
```

**Estimated Effort**: 4-5 hours

---

#### T3: RAG Knowledge Base Setup [Antigravity] [P1]
**File**: `backend/agents/bi_tool/rag_knowledge.py`
**Data**: `backend/data/knowledge_base/tableau/*.md`

**Description**:
Tableau 공식 문서 기반 지식 베이스 구축. 기존 `GuideAssistant`를 확장.

**Acceptance Criteria**:
- [ ] Tableau 기본 조작 가이드 5개 이상 작성 (Markdown)
- [ ] 간단한 키워드 기반 검색 (MVP: no vector DB)
- [ ] LLM 컨텍스트 주입 함수 구현
- [ ] GuideAssistant 업데이트

**Knowledge Topics**:
1. 차트 유형별 생성 가이드 (bar, line, pie)
2. 필터 추가 방법
3. 계산 필드 작성 기본
4. 데이터 소스 연결
5. 대시보드 레이아웃

**Estimated Effort**: 3-4 hours

---

#### T4: Power BI DAX JSON Stub [Claude] [P2]
**File**: `backend/agents/bi_tool/pbi_meta_schema.py`

**Description**:
Power BI용 메타 JSON 스텁. MVP에서는 기본 구조만 정의.

**Acceptance Criteria**:
- [ ] PBI Meta JSON schema 정의 (tables, measures, visuals)
- [ ] DAX 템플릿 5개 확장 (기존 2개 + 3개)
- [ ] `PBILogicGenerator.to_meta_json()` 스텁 구현

**Estimated Effort**: 2 hours

---

### Day 3-4: Integration

---

#### T5: Meta Generation Pipeline [Claude] [P0]
**File**: `backend/agents/bi_tool/meta_generator.py`

**Description**:
핵심 파이프라인: NL Input -> Intent -> Schema Lookup -> Meta JSON Output

**Acceptance Criteria**:
- [ ] `MetaGenerator` 클래스 구현
- [ ] DB 스키마 조회 연동 (기존 DataSourceAgent 활용)
- [ ] Intent -> Meta JSON 변환 로직
- [ ] 도구별 분기 (tableau/powerbi)
- [ ] 에러 핸들링 및 fallback

**Pipeline Flow**:
```
User Input
    │
    v
[NL Intent Parser] ──> Intent Object
    │
    v
[Schema Lookup] ──> DB 스키마 정보 (tables, columns)
    │
    v
[Meta Generator] ──> BI Meta JSON
    │
    v
[Validator] ──> 유효성 검사
    │
    v
Output JSON
```

**Integration Points**:
- `InteractionOrchestrator.handle_request()` 확장
- `DataSourceAgent.get_schema()` 활용
- `TableauMetadataEngine.create_from_intent()` 신규

**Estimated Effort**: 6-8 hours

---

#### T6: TUI Meta Preview Panel [Antigravity] [P1]
**File**: `backend/orchestrator/tui_meta_preview.py`

**Description**:
생성된 Meta JSON을 TUI에서 시각화하고 내보내기 기능 제공.

**Acceptance Criteria**:
- [ ] Rich Panel로 JSON 프리뷰 표시
- [ ] Syntax highlighting (JSON)
- [ ] 파일 저장 기능 (`save <filename>`)
- [ ] `main.py` TUI 루프에 통합

**TUI Commands**:
- `meta preview` - 마지막 생성된 Meta JSON 표시
- `meta save <path>` - JSON 파일로 저장
- `meta export twb` - .twb 파일로 변환 (optional)

**Estimated Effort**: 4-5 hours

---

### Day 5-7: Polish & Demo

---

#### T7: End-to-End Testing [Both] [P0]
**File**: `backend/tests/test_mvp_e2e.py`

**Description**:
MVP 시나리오 전체 테스트. 자연어 입력부터 JSON 출력까지.

**Test Scenarios**:
1. "월별 매출 바 차트 생성" -> Tableau Meta JSON
2. "고객별 주문 테이블 만들기" -> Tableau Meta JSON
3. "매출 추이 라인 차트" -> Tableau Meta JSON
4. 잘못된 입력 처리 테스트
5. DB 연결 실패 시 graceful fallback

**Acceptance Criteria**:
- [ ] 5개 시나리오 모두 통과
- [ ] 생성된 JSON 유효성 검증
- [ ] TUI에서 정상 출력 확인
- [ ] 에러 메시지 적절성 확인

**Estimated Effort**: 4-5 hours

---

#### T8: Demo Preparation & Bug Fixes [Both] [P0]
**File**: Various

**Description**:
데모 준비 및 발견된 버그 수정.

**Demo Script**:
1. TUI 시작 화면 소개
2. 자연어로 차트 생성 요청
3. 생성된 Meta JSON 프리뷰
4. JSON 파일 저장
5. (Optional) Tableau에서 import 시연

**Acceptance Criteria**:
- [ ] 3분 데모 스크립트 준비
- [ ] Critical 버그 0개
- [ ] Happy path 100% 작동

**Estimated Effort**: 3-4 hours

---

## 6. Schedule Overview

| Day | Claude Tasks | Antigravity Tasks | Checkpoint |
|-----|--------------|-------------------|------------|
| **Day 1** | T1: Schema Design | T3: RAG Setup | - |
| **Day 2** | T2: Intent Parser | T3: RAG (cont.) | - |
| **Day 3** | T5: Pipeline (start) | T6: TUI Preview | **Mid-Week Check** |
| **Day 4** | T5: Pipeline (complete) | T6: TUI (cont.) | - |
| **Day 5** | T7: E2E Testing | T7: E2E Testing | - |
| **Day 6** | T8: Bug Fixes | T8: Bug Fixes | - |
| **Day 7** | T4: PBI Stub (if time) | Demo Polish | **Final Demo** |

---

## 7. Commit Strategy

### Commit Points

| Commit | Description | Tasks |
|--------|-------------|-------|
| `feat: add tableau meta json schema` | T1 완료 | T1 |
| `feat: implement nl intent parser` | T2 완료 | T2 |
| `feat: setup rag knowledge base` | T3 완료 | T3 |
| `feat: integrate meta generation pipeline` | T5 완료 | T5 |
| `feat: add tui meta preview panel` | T6 완료 | T6 |
| `test: add mvp e2e tests` | T7 완료 | T7 |
| `chore: mvp demo preparation` | T8 완료 | T8 |

### Branch Strategy
- `main` - stable
- `feature/mvp-meta-json` - MVP 개발 브랜치
- PR on Day 7 after all tests pass

---

## 8. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LLM API rate limit | Medium | High | Ollama fallback 활용 |
| Tableau XML complexity | Low | Medium | 기본 구조만 지원 (MVP) |
| DB schema 조회 실패 | Low | Medium | Mock data fallback |
| TUI 렌더링 이슈 | Low | Low | 기존 코드 재사용 |
| 시간 부족 | Medium | High | P2 태스크 스킵 가능 |

### Contingency Plan
- Day 5까지 P0 미완료 시: P1/P2 전체 스킵, P0에 집중
- LLM 완전 실패 시: 하드코딩된 Intent 매핑으로 대체

---

## 9. Verification Checkpoints

### Day 3: Mid-Week Checkpoint
**Pass Criteria**:
- [ ] T1 (Schema) 100% 완료
- [ ] T2 (Intent Parser) 80% 이상 완료
- [ ] T3 (RAG) 기본 데이터 구축 완료
- [ ] T5 (Pipeline) 시작됨

**Action if Fail**: P2 태스크 전체 드랍, 리소스 재배치

### Day 7: Final MVP Demo
**Pass Criteria**:
- [ ] 성공 시나리오 작동: "자연어 -> Meta JSON"
- [ ] TUI에서 입출력 가능
- [ ] JSON 파일 저장 가능
- [ ] 3분 데모 완주

---

## 10. Success Criteria Summary

### MVP Complete When:

1. **Functional**: 사용자가 TUI에서 "월별 매출 차트 만들어줘" 입력 시 유효한 Tableau Meta JSON 생성
2. **Visual**: JSON이 TUI에 syntax-highlighted로 표시
3. **Exportable**: 생성된 JSON을 파일로 저장 가능
4. **Stable**: Happy path에서 에러 없이 작동

### Post-MVP Backlog (Phase 4)

| Item | Description |
|------|-------------|
| Power BI .pbix 파싱 | 바이너리 포맷 분석 |
| Cloud BI 연동 | Looker Studio, QuickSight |
| Vector RAG | FAISS/Chroma 기반 문서 검색 |
| Self-Healing | 에러 로그 자동 분석 |
| Workflow Automation | Airflow DAG 생성 |

---

## 11. File Structure (After MVP)

```
backend/
├── agents/
│   └── bi_tool/
│       ├── bi_tool_agent.py          # (existing)
│       ├── tableau_metadata.py       # (existing, enhanced)
│       ├── tableau_meta_schema.py    # NEW: T1
│       ├── nl_intent_parser.py       # NEW: T2
│       ├── rag_knowledge.py          # NEW: T3
│       ├── pbi_meta_schema.py        # NEW: T4
│       ├── meta_generator.py         # NEW: T5
│       └── guide_assistant.py        # (existing, enhanced)
├── orchestrator/
│   ├── interaction_orchestrator.py   # (existing, enhanced)
│   ├── tui_meta_preview.py           # NEW: T6
│   └── tui_interface.py              # (existing)
├── data/
│   └── knowledge_base/
│       └── tableau/
│           ├── chart_guide.md        # NEW: T3
│           ├── filter_guide.md       # NEW: T3
│           └── calc_field_guide.md   # NEW: T3
└── tests/
    └── test_mvp_e2e.py               # NEW: T7
```

---

**Plan Version**: 1.0
**Created By**: Prometheus (Planning Agent)
**Ready for**: `/start-work mvp-bi-meta-json`
