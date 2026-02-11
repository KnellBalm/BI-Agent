# Phase 4-5 Product Requirements & Prioritization

**Document Owner:** Product Owner
**Created:** 2026-02-11
**Project:** BI-Agent v2.2.0 → v3.0.0 (MVP Complete)
**Status:** Phase 0-3 Complete (Steps 1-10) | Phase 4-5 Remaining (Steps 11-15)

---

## Executive Summary

Phase 4-5 represents the **final 33% of the MVP roadmap**, focusing on visualization design, user interaction, and output delivery. Current completion: **67% (Steps 1-10 완료)**. Remaining work concentrates on transforming analysis results into polished, interactive dashboards.

**Strategic Goal:** Deliver a production-ready BI agent capable of autonomous report generation from natural language queries to exportable dashboards.

---

## 1. Current State Assessment

### ✅ Completed (Steps 1-10)
- **Phase 0-1:** Foundation, authentication, connection management
- **Phase 2:** Intent parsing, table recommendation, deep profiling (106 tests)
- **Phase 3:** Pipeline generation, hypothesis engine, thinking visualization (204 tests)
- **Phase 4 (Partial):** SQL generation with self-healing (Step 10 완료)

### 📊 Quality Metrics
- **Test Coverage:** 95%+ (310+ tests passing)
- **Type Safety:** 100% (all public APIs)
- **Documentation:** 95% docstring coverage
- **Production Ready:** Steps 1-10 fully validated

### 🎯 Remaining Work
- **Step 11:** Layout Design (차트 추천, 테마, 레이아웃)
- **Step 12:** Interaction Injection (varList/eventList, 드릴다운)
- **Step 13:** Preview & Briefing (요약, 웹 프리뷰, KPI)
- **Step 14:** Iterative Refinement (수정 루프, 품질 검증)
- **Step 15:** Final Export (JSON 검증, Excel/PDF)

---

## 2. Detailed Requirements Analysis

### 2.1 Step 11: Layout Design (레이아웃 디자인)

#### 2.1.1 Chart Recommendation Engine
**Business Value:** HIGH | **Complexity:** MEDIUM | **Priority:** P0 (MVP 필수)

**Requirements:**
- 데이터 특성 자동 감지 (시계열, 분포, 상관, 비교)
- 특성별 차트 타입 매핑 (시계열→Line, 분포→Histogram, etc.)
- 상위 3개 차트 추천 + 근거 제공
- LLM 기반 의미론적 추천

**Acceptance Criteria:**
- [ ] `ChartRecommender` 클래스 구현 (`backend/agents/bi_tool/chart_recommender.py`)
- [ ] 시계열/분포/상관/비교 데이터 패턴 자동 감지 (정확도 85%+)
- [ ] 각 추천에 신뢰도 점수 (0-100) 및 한국어 근거 제공
- [ ] 15개 이상 테스트 케이스 (다양한 데이터 타입별)

**Dependencies:**
- Profiler output (Step 6 완료)
- AnalysisIntent (Phase 2 완료)

**Risk Assessment:**
- **Technical:** LOW (LLM 프롬프트 기반, 기존 패턴 활용)
- **Business:** HIGH (잘못된 차트 선택 시 인사이트 왜곡)

---

#### 2.1.2 Premium Theme Engine Enhancement
**Business Value:** MEDIUM | **Complexity:** LOW | **Priority:** P1 (Enhanced MVP)

**Current State:**
- 기존 `theme_engine.py` 존재 (2개 테마: premium_dark, corporate_light)
- 기본 색상 팔레트 및 레이아웃 토큰 제공

**Requirements:**
- 최소 3개 추가 테마 팔레트 (총 5개)
  - `executive_blue`: 임원 보고서용 차분한 블루 계열
  - `nature_green`: 환경/지속가능성 리포트용
  - `sunset_warm`: 마케팅/소비자 분석용 따뜻한 톤
- 폰트 메타데이터 주입 (family, size scale, weight mapping)
- 테마별 접근성 대비 비율 검증 (WCAG AA 준수)

**Acceptance Criteria:**
- [ ] 5개 테마 팔레트 구현 (각 8개 이상 색상 정의)
- [ ] 폰트 메타데이터 스키마 (`fontFamily`, `fontSize`, `fontWeight`)
- [ ] 색상 대비 비율 자동 검증 (4.5:1 이상)
- [ ] 테마 전환 시 모든 컴포넌트 일관성 유지

**Risk Assessment:**
- **Technical:** VERY LOW (정적 설정 확장)
- **Business:** LOW (UX 개선이지만 필수 아님)

---

#### 2.1.3 Auto Layout Calculator
**Business Value:** HIGH | **Complexity:** MEDIUM | **Priority:** P0 (MVP 필수)

**Requirements:**
- N개 컴포넌트를 12컬럼 그리드에 자동 배치
- 컴포넌트 우선순위 기반 크기 조정
  - KPI 카드: 2-3 컬럼
  - 메인 차트: 8-12 컬럼
  - 필터: 2-4 컬럼
- 반응형 레이아웃 (모바일/태블릿/데스크탑)
- 빈 공간 최소화 알고리즘

**Acceptance Criteria:**
- [ ] `LayoutCalculator` 클래스 구현 (`backend/agents/bi_tool/layout_calculator.py`)
- [ ] 그리드 위치 계산 (x, y, width, height)
- [ ] 우선순위 기반 배치 (High → Medium → Low)
- [ ] 컴포넌트 겹침 방지 검증
- [ ] 10개 이상 레이아웃 시나리오 테스트

**Dependencies:**
- ChartRecommender output
- ThemeEngine layout tokens

**Risk Assessment:**
- **Technical:** MEDIUM (복잡한 배치 알고리즘 필요)
- **Business:** HIGH (레이아웃 깨지면 사용성 급락)

---

### 2.2 Step 12: Interaction Injection (인터랙션 주입)

#### 2.2.1 VarList/EventList Generator
**Business Value:** VERY HIGH | **Complexity:** HIGH | **Priority:** P0 (MVP 필수)

**Current State:**
- `interaction_logic.py` 기본 구현 존재 (99 lines)
- varList/eventList 기초 구조만 제공

**Requirements:**
- 전역 필터 변수 자동 생성 (날짜 범위, 카테고리 선택)
- 크로스 필터 이벤트 바인딩 (한 차트 클릭 → 다른 차트 필터링)
- 파라미터 바인딩 문법 (SQL 쿼리 내 `{{ v_date_start }}` 주입)
- 동적 변수 슬라이더/드롭다운 UI 메타데이터

**Acceptance Criteria:**
- [ ] `InteractionLogic` 클래스 고도화 (기존 99 lines → 300+ lines)
- [ ] varList 자동 생성 (필터 타입별: date, select, slider, multiselect)
- [ ] eventList 자동 생성 (onClick, onChange, onHover)
- [ ] 파라미터 바인딩 검증 (SQL 쿼리 파싱 및 변수 주입 테스트)
- [ ] 20개 이상 인터랙션 시나리오 테스트

**Example Output:**
```json
{
  "varList": [
    {
      "id": "v_date_start",
      "name": "Start Date",
      "type": "parameter",
      "value": "2024-01-01"
    }
  ],
  "eventList": [
    {
      "id": "e_chart_click",
      "trigger": "onClick",
      "source": "chart_sales",
      "action": "filter",
      "target": ["chart_regions", "kpi_total"]
    }
  ]
}
```

**Dependencies:**
- Profiler column type detection (Step 6)
- ChartRecommender output (Step 11.1)

**Risk Assessment:**
- **Technical:** HIGH (복잡한 이벤트 체이닝 로직)
- **Business:** VERY HIGH (인터랙티브 기능은 BI 대시보드의 핵심)

---

#### 2.2.2 Drill-Down Logic Mapper
**Business Value:** HIGH | **Complexity:** MEDIUM | **Priority:** P1 (Enhanced MVP)

**Requirements:**
- 드릴다운 계층 자동 정의 (연도 → 분기 → 월 → 일)
- 데이터로부터 계층 구조 감지 (`year`, `month` 컬럼 자동 그룹핑)
- 계층별 쿼리 자동 생성
- Breadcrumb 네비게이션 메타데이터

**Acceptance Criteria:**
- [ ] `DrilldownMapper` 클래스 구현 (`backend/agents/bi_tool/drilldown_mapper.py`)
- [ ] 시간 계층 자동 감지 (year/quarter/month/week/day)
- [ ] 지리 계층 자동 감지 (country/state/city)
- [ ] 카테고리 계층 자동 감지 (category/subcategory/product)
- [ ] 계층별 집계 쿼리 생성 및 검증

**Risk Assessment:**
- **Technical:** MEDIUM (계층 감지 로직 복잡)
- **Business:** MEDIUM (선택적 기능이지만 UX 크게 향상)

---

### 2.3 Step 13: Preview & Briefing (초안 브리핑)

#### 2.3.1 Summary Generator
**Business Value:** VERY HIGH | **Complexity:** LOW | **Priority:** P0 (MVP 필수)

**Requirements:**
- LLM 기반 한국어 분석 요약 생성 (3-5 문단)
- 주요 인사이트 추출 (3-5개 불렛 포인트)
- 비즈니스 권장사항 생성
- 요약 품질 자동 평가 (가독성, 정확성)

**Acceptance Criteria:**
- [ ] `SummaryGenerator` 클래스 구현 (`backend/agents/bi_tool/summary_generator.py`)
- [ ] LLM 프롬프트 템플릿 (분석 결과 → 요약)
- [ ] 인사이트 추출 알고리즘 (통계적 유의성 기반)
- [ ] 한국어 품질 검증 (맞춤법, 문맥 일관성)
- [ ] 10개 이상 요약 시나리오 테스트

**Dependencies:**
- Pipeline execution results (Step 7)
- Query results (Step 10)

**Risk Assessment:**
- **Technical:** LOW (LLM 프롬프트 기반)
- **Business:** VERY HIGH (잘못된 요약은 의사결정 오류 유발)

---

#### 2.3.2 Local Web Preview Server
**Business Value:** HIGH | **Complexity:** MEDIUM | **Priority:** P1 (Enhanced MVP)

**Requirements:**
- Flask 기반 로컬 HTTP 서버 (`localhost:5000`)
- 생성된 HTML 대시보드 실시간 서빙
- 자동 브라우저 오픈
- Hot reload 지원 (대시보드 수정 시 자동 갱신)

**Acceptance Criteria:**
- [ ] `PreviewServer` 클래스 구현 (`backend/utils/preview_server.py`)
- [ ] Flask 앱 초기화 및 `/preview/<report_id>` 엔드포인트
- [ ] HTML 템플릿 렌더링 (InHouse JSON → HTML)
- [ ] 포트 충돌 처리 (5000 사용 중이면 5001, 5002... 자동 할당)
- [ ] 서버 시작/중지 테스트

**New Dependency:**
```python
# requirements.txt에 추가 필요
flask>=3.0.0
```

**Risk Assessment:**
- **Technical:** MEDIUM (서버 관리 복잡성)
- **Business:** MEDIUM (TUI만으로도 작동 가능하지만 UX 크게 향상)

---

#### 2.3.3 ASCII KPI Cards (TUI)
**Business Value:** MEDIUM | **Complexity:** LOW | **Priority:** P2 (Nice-to-Have)

**Requirements:**
- TUI 내 ASCII 박스 형태 KPI 카드
- 스파크라인 시각화 (`▁▂▃▄▅▆▇█`)
- 증감 인디케이터 (▲ 10% ↑)
- 색상 코딩 (Rich 라이브러리 활용)

**Acceptance Criteria:**
- [ ] `ASCIIKPICard` 위젯 구현 (`backend/orchestrator/components/ascii_kpi.py`)
- [ ] 박스 그리기 (Rich Panel 활용)
- [ ] 스파크라인 생성 (8단계 유니코드 블록)
- [ ] 증감률 자동 계산 (전 기간 대비)
- [ ] Textual 앱 통합 테스트

**Risk Assessment:**
- **Technical:** VERY LOW (UI 컴포넌트 추가)
- **Business:** LOW (보조 기능)

---

### 2.4 Step 14: Iterative Refinement (반복적 교정)

#### 2.4.1 Refinement Command Loop
**Business Value:** HIGH | **Complexity:** MEDIUM | **Priority:** P1 (Enhanced MVP)

**Requirements:**
- 수정 명령 파싱 ("차트 바꿔줘" → action 매핑)
- 실시간 대시보드 수정 적용
- 수정 히스토리 관리 (Undo/Redo)
- 자연어 수정 명령 지원

**Acceptance Criteria:**
- [ ] `RefinementHandler` 클래스 구현 (`backend/orchestrator/refinement_handler.py`)
- [ ] 명령어 패턴 매칭 ("차트 타입 변경", "필터 추가", "색상 조정")
- [ ] 수정 적용 로직 (InHouse JSON 업데이트)
- [ ] 히스토리 스택 구현 (최대 10단계)
- [ ] 15개 이상 수정 시나리오 테스트

**Risk Assessment:**
- **Technical:** MEDIUM (명령어 파싱 복잡)
- **Business:** HIGH (사용자 만족도에 직접 영향)

---

#### 2.4.2 Report Linter
**Business Value:** MEDIUM | **Complexity:** LOW | **Priority:** P2 (Nice-to-Have)

**Requirements:**
- 시각적 명료성 검사 (폰트 크기, 색상 대비)
- 데이터 정확성 검사 (참조 컬럼 존재, 집계 오류)
- 접근성 검증 (WCAG AA 준수)
- 자동 수정 제안

**Acceptance Criteria:**
- [ ] `ReportLinter` 클래스 구현 (`backend/agents/bi_tool/report_linter.py`)
- [ ] 5개 이상 린팅 규칙 (폰트, 대비, 컬럼 참조, 집계, 레이아웃)
- [ ] 경고/에러 레벨 분류
- [ ] 자동 수정 제안 생성
- [ ] 린팅 보고서 출력

**Risk Assessment:**
- **Technical:** LOW (규칙 기반 검증)
- **Business:** MEDIUM (품질 향상이지만 필수 아님)

---

### 2.5 Step 15: Final Export (최종 출력)

#### 2.5.1 JSON Validator
**Business Value:** VERY HIGH | **Complexity:** LOW | **Priority:** P0 (MVP 필수)

**Requirements:**
- InHouse 표준 스키마 검증
- 참조 무결성 확인 (datamodel ID 존재 여부)
- 순환 참조 감지
- 스키마 버전 관리

**Acceptance Criteria:**
- [ ] `JSONValidator` 클래스 구현 (`backend/agents/bi_tool/json_validator.py`)
- [ ] JSON Schema 정의 파일 (`schemas/inhouse_v1.schema.json`)
- [ ] 검증 오류 상세 메시지 (한국어)
- [ ] 자동 수정 제안 (가능한 경우)
- [ ] 20개 이상 검증 시나리오 테스트

**Risk Assessment:**
- **Technical:** VERY LOW (JSON Schema 라이브러리 활용)
- **Business:** VERY HIGH (잘못된 JSON은 대시보드 로드 실패 유발)

---

#### 2.5.2 Excel/PDF Export
**Business Value:** HIGH | **Complexity:** MEDIUM | **Priority:** P1 (Enhanced MVP)

**Current State:**
- `output_packager.py` 기본 구현 존재 (51 lines)
- HTML/JSON 패키징만 지원

**Requirements:**
- Excel 내보내기 (`.xlsx`)
  - 데이터 테이블을 시트로 저장
  - 기본 서식 적용 (헤더 굵게, 필터 활성화)
  - 다중 시트 지원 (데이터 + 요약)
- PDF 리포트 생성
  - HTML 대시보드 → PDF 변환
  - 페이지 레이아웃 최적화 (A4 세로/가로)
  - 목차 및 페이지 번호

**Acceptance Criteria:**
- [ ] `OutputPackager` 클래스 확장 (51 lines → 200+ lines)
- [ ] Excel 내보내기 구현 (`export_excel()` 메서드)
- [ ] PDF 내보내기 구현 (`export_pdf()` 메서드)
- [ ] 파일 브라우저 통합 (TUI 내 다운로드 경로 표시)
- [ ] 10개 이상 내보내기 시나리오 테스트

**New Dependencies:**
```python
# requirements.txt에 추가 필요
openpyxl>=3.1.0      # Excel 쓰기
weasyprint>=60.0     # HTML → PDF 변환
```

**Risk Assessment:**
- **Technical:** MEDIUM (라이브러리 의존성, PDF 렌더링 복잡)
- **Business:** HIGH (엑셀 내보내기는 실무자 필수 요구사항)

---

## 3. MVP Scope Definition

### 3.1 Must-Have (P0 - MVP Blocker)
**없으면 MVP 출시 불가능**

| Step | Component | Effort | Business Impact |
|------|-----------|--------|-----------------|
| 11.1 | ChartRecommender | 5 days | VERY HIGH |
| 11.3 | LayoutCalculator | 4 days | HIGH |
| 12.1 | VarList/EventList Generator | 6 days | VERY HIGH |
| 13.1 | SummaryGenerator | 3 days | VERY HIGH |
| 15.1 | JSONValidator | 2 days | VERY HIGH |

**Total P0 Effort:** 20 days
**Critical Path:** Step 12.1 (가장 복잡하고 의존성 높음)

---

### 3.2 Should-Have (P1 - Enhanced MVP)
**MVP 품질을 크게 향상시키지만 필수 아님**

| Step | Component | Effort | Business Impact |
|------|-----------|--------|-----------------|
| 11.2 | Theme Engine (3종 추가) | 2 days | MEDIUM |
| 12.2 | DrilldownMapper | 4 days | HIGH |
| 13.2 | PreviewServer (Flask) | 3 days | HIGH |
| 14.1 | RefinementHandler | 4 days | HIGH |
| 15.2 | Excel/PDF Export | 5 days | HIGH |

**Total P1 Effort:** 18 days
**Recommendation:** 15.2 (Excel Export)는 P0로 승격 고려 (실무자 필수 요구)

---

### 3.3 Nice-to-Have (P2 - Future)
**출시 후 추가 가능**

| Step | Component | Effort | Business Impact |
|------|-----------|--------|-----------------|
| 13.3 | ASCII KPI Cards (TUI) | 2 days | LOW |
| 14.2 | ReportLinter | 3 days | MEDIUM |

**Total P2 Effort:** 5 days
**Defer to:** v3.1.0 릴리스

---

## 4. Implementation Roadmap

### 4.1 Sprint 1: Visualization Core (Week 1-2)
**Goal:** 차트 추천 및 레이아웃 시스템 구축

**Tasks:**
1. ChartRecommender 구현 (Step 11.1) - 5 days
2. LayoutCalculator 구현 (Step 11.3) - 4 days
3. ThemeEngine 확장 (Step 11.2) - 2 days

**Deliverable:** 데이터 → 차트 타입 → 레이아웃 자동 생성 파이프라인

**Acceptance Test:**
```python
# 입력: Profiler 결과
profile = {"columns": [...], "row_count": 1000}

# 출력: 추천 차트 + 레이아웃
recommendations = chart_recommender.recommend(profile, intent)
layout = layout_calculator.calculate(recommendations)

# 검증
assert len(recommendations) >= 3
assert all(r["confidence"] > 70 for r in recommendations)
assert layout["grid_cols"] == 12
```

---

### 4.2 Sprint 2: Interaction Layer (Week 3-4)
**Goal:** 인터랙티브 기능 구현

**Tasks:**
1. VarList/EventList Generator 고도화 (Step 12.1) - 6 days
2. DrilldownMapper 구현 (Step 12.2) - 4 days

**Deliverable:** 전역 필터 + 크로스 필터링 + 드릴다운 지원

**Acceptance Test:**
```python
# 입력: 프로파일 + 추천 차트
config = interaction_logic.suggest_configuration(profile)

# 출력: varList + eventList
assert len(config["varList"]) > 0
assert len(config["eventList"]) > 0
assert "{{ v_date_start }}" in config["dynamic_query"]
```

---

### 4.3 Sprint 3: Preview & Export (Week 5-6)
**Goal:** 결과물 생성 및 출력

**Tasks:**
1. SummaryGenerator 구현 (Step 13.1) - 3 days
2. PreviewServer 구현 (Step 13.2) - 3 days
3. JSONValidator 구현 (Step 15.1) - 2 days
4. Excel/PDF Export 구현 (Step 15.2) - 5 days

**Deliverable:** 완성된 대시보드 + 요약 + 다중 포맷 출력

**Acceptance Test:**
```python
# 전체 파이프라인 테스트
result = orchestrator.execute_analysis(intent)

# 검증
assert result["summary_ko"] is not None
assert result["dashboard_html"] is not None
assert os.path.exists(result["excel_path"])
assert os.path.exists(result["pdf_path"])
```

---

### 4.4 Sprint 4: Refinement & QA (Week 7)
**Goal:** 반복 수정 기능 + 통합 테스트

**Tasks:**
1. RefinementHandler 구현 (Step 14.1) - 4 days
2. 통합 테스트 스위트 작성 - 2 days
3. 문서화 업데이트 - 1 day

**Deliverable:** 사용자 수정 명령 지원 + 전체 E2E 테스트

---

## 5. Risk Assessment & Mitigation

### 5.1 High Risk Items

#### Risk #1: VarList/EventList 복잡도 (Step 12.1)
**Probability:** HIGH | **Impact:** VERY HIGH

**Description:** 크로스 필터링 이벤트 체이닝 로직이 예상보다 복잡할 수 있음

**Mitigation:**
1. 간단한 시나리오부터 구현 (단방향 필터 → 크로스 필터)
2. LLM 보조 활용 (복잡한 이벤트 체인은 LLM이 생성)
3. 기존 `interaction_logic.py` 코드 최대한 재활용
4. Early Prototype (Sprint 1에서 기본 구조 검증)

---

#### Risk #2: Excel/PDF 의존성 (Step 15.2)
**Probability:** MEDIUM | **Impact:** HIGH

**Description:** `weasyprint`는 OS별 의존성 (Cairo, Pango) 설치 필요

**Mitigation:**
1. Docker 환경 우선 검증
2. 설치 가이드 문서화 (`SETUP_GUIDE.md` 업데이트)
3. 선택적 의존성으로 구현 (weasyprint 없어도 Excel은 작동)
4. Fallback: HTML → 인쇄용 CSS 제공

---

#### Risk #3: Preview Server 포트 충돌 (Step 13.2)
**Probability:** LOW | **Impact:** MEDIUM

**Description:** 로컬 5000 포트가 이미 사용 중일 수 있음

**Mitigation:**
1. 동적 포트 할당 (5000-5010 범위 자동 탐색)
2. 사용자 설정 가능하도록 `.env` 변수 제공
3. 포트 충돌 시 친절한 에러 메시지

---

### 5.2 Medium Risk Items

#### Risk #4: LLM 비용 (전체)
**Probability:** MEDIUM | **Impact:** MEDIUM

**Description:** Step 11-15에서 LLM 호출이 증가하여 API 비용 상승

**Mitigation:**
1. 적극적인 캐싱 (동일 데이터 프로파일 → 동일 추천 결과)
2. 로컬 모델 fallback (Ollama 지원)
3. 배치 처리 (여러 작업을 한 번의 LLM 호출로)

---

## 6. Success Criteria

### 6.1 Functional Requirements
- [ ] 자연어 쿼리 → 완성된 대시보드 (E2E) 성공률 90%+
- [ ] 차트 추천 정확도 85%+ (사용자 만족도 기준)
- [ ] 인터랙티브 필터 동작 성공률 95%+
- [ ] Excel/PDF 생성 성공률 98%+

### 6.2 Non-Functional Requirements
- [ ] 테스트 커버리지 90%+ 유지
- [ ] E2E 테스트 실행 시간 < 5분
- [ ] 대시보드 생성 시간 < 30초 (중간 복잡도 기준)
- [ ] 메모리 사용량 < 500MB

### 6.3 User Acceptance
- [ ] 5명 이상 내부 베타 테스터 검증
- [ ] 평균 만족도 4.0/5.0 이상
- [ ] Critical Bug 0건

---

## 7. Dependencies & Blockers

### 7.1 External Dependencies
```python
# requirements.txt 추가 필요
flask>=3.0.0           # Step 13.2 (PreviewServer)
openpyxl>=3.1.0        # Step 15.2 (Excel Export)
weasyprint>=60.0       # Step 15.2 (PDF Export) - Optional
pyperclip>=1.8.0       # Step 6.2 (Clipboard) - 이미 완료된 Step
```

### 7.2 Internal Blockers
**None.** Phase 0-3 완료로 모든 기술적 기반 확보됨.

---

## 8. Recommendation & Next Steps

### 8.1 Immediate Actions (이번 주)
1. **Excel Export를 P0로 승격** (실무 필수 요구사항)
2. **Sprint 1 착수** (ChartRecommender + LayoutCalculator)
3. **의존성 설치 검증** (flask, openpyxl, weasyprint)

### 8.2 Sprint Planning
- **Sprint 1 (Week 1-2):** Step 11 완료
- **Sprint 2 (Week 3-4):** Step 12 완료
- **Sprint 3 (Week 5-6):** Step 13, 15 완료
- **Sprint 4 (Week 7):** Step 14 + QA

**Total Timeline:** 7 weeks to MVP v3.0.0

### 8.3 Resource Allocation
- **Architect:** 설계 검토 및 복잡도 높은 컴포넌트 (Step 12.1, 15.2)
- **Builder-1:** 표준 구현 (Step 11, 13, 15.1)
- **Builder-2:** 보조 기능 및 테스트 (Step 14, 통합 테스트)

---

## 9. Appendix

### 9.1 File Creation Summary
**신규 생성 예정 파일 (9개):**
1. `backend/agents/bi_tool/chart_recommender.py`
2. `backend/agents/bi_tool/layout_calculator.py`
3. `backend/agents/bi_tool/drilldown_mapper.py`
4. `backend/agents/bi_tool/summary_generator.py`
5. `backend/agents/bi_tool/json_validator.py`
6. `backend/utils/preview_server.py`
7. `backend/orchestrator/refinement_handler.py`
8. `backend/orchestrator/components/ascii_kpi.py`
9. `backend/agents/bi_tool/report_linter.py`

**확장 예정 파일 (3개):**
1. `backend/agents/bi_tool/theme_engine.py` (78 lines → 150+ lines)
2. `backend/agents/bi_tool/interaction_logic.py` (99 lines → 300+ lines)
3. `backend/utils/output_packager.py` (51 lines → 200+ lines)

### 9.2 Test File Summary
**신규 테스트 파일 (9개):**
1. `tests/test_chart_recommender.py` (15+ tests)
2. `tests/test_layout_calculator.py` (10+ tests)
3. `tests/test_drilldown_mapper.py` (8+ tests)
4. `tests/test_summary_generator.py` (10+ tests)
5. `tests/test_json_validator.py` (20+ tests)
6. `tests/test_preview_server.py` (8+ tests)
7. `tests/test_refinement_handler.py` (15+ tests)
8. `tests/test_output_packager.py` (10+ tests)
9. `tests/integration/test_phase4_5_e2e.py` (5+ scenarios)

**Expected Test Count:** 100+ new tests

---

**Document Version:** 1.0
**Last Updated:** 2026-02-11
**Next Review:** Sprint 1 완료 후 (2주 후)

---

Copyright © 2026 BI-Agent Team. All rights reserved.
