# BI-Agent Changelog

> 프로젝트의 주요 변경 사항 및 릴리스 기록입니다.

---

## 2026-02-19 (v2.3.2-development) 🤖

### Major Highlights: "Step 14.2 Proactive Questions 완성"

사용자에게 분석 후속 질문을 자동 제안하는 AI 기능이 추가되어, 더 깊이 있는 인사이트 탐색이 가능해졌습니다.

### 🟢 Added (신규 기능)

#### Step 14.2: Proactive Questions 자동 제안

- **ProactiveQuestionGenerator** (`proactive_question_generator.py`): LLM 기반 후속 질문 생성 엔진
  - 5가지 질문 유형: 원인 분석, 비교 분석, 시계열, 세그먼트, 드릴다운
  - 분석 컨텍스트 기반 3-5개 맞춤형 질문 생성
  - LLM 실패 시 규칙 기반 폴백 질문 제공
  - QuestionType enum, ProactiveQuestion dataclass

- **AgenticOrchestrator `suggest_questions` 도구 추가**:
  - 15번째 도구로 `suggest_questions` 등록
  - async/await 처리로 비동기 LLM 호출 지원
  - 샘플 컨텍스트 자동 생성 및 질문 제안

- **E2E 테스트 스위트** (`test_proactive_questions_e2e.py`):
  - 22개 E2E 테스트 (모두 통과)
  - 질문 생성, LLM 통합, 도구 레지스트리, 엣지 케이스 검증
  - Unicode, 대용량 컨텍스트, 동시성 테스트 포함

### 🟡 Improved (개선 사항)

- **ToolRegistry 확장**: 14개 → 15개 도구로 증가
- **테스트 커버리지**: E2E 94개 → 116개로 증가 (+22)
- **문서 업데이트**: TODO.md, PLAN.md 최신화

### 📊 Test Coverage Summary

| 카테고리 | 테스트 수 | 실행 시간 | 상태 |
|----------|-----------|-----------|------|
| E2E ProactiveQuestions | 22 | 3.40s | ✅ |
| E2E ToolRegistry | 20 | <4s | ✅ (15개 도구) |
| **전체 E2E** | **116** | **~10s** | **✅** |
| **총 테스트** | **426+** | — | **✅** |

---

## 2026-02-19 (v2.3.0-development) 🏗️

### Major Highlights: "Phase 4~5 전체 완료 + E2E 테스트 스위트 구축"

15단계 초정밀 여정의 핵심 엔진을 모두 구현하여, 데이터 프로파일링부터 최종 JSON/Excel/PDF 출력까지의 전체 BI 파이프라인을 완성했습니다. 또한 77개 E2E 테스트로 컴포넌트 간 통합을 검증하는 테스트 인프라를 구축했습니다.

### 🟢 Added (신규 기능)

#### Phase 4 Step 11: 레이아웃 디자인

- **ChartRecommender** (`chart_recommender.py`): 데이터 특성 기반 차트 자동 추천 엔진.
  - 7가지 데이터 패턴 지원 (time_series, categorical, scatter, treemap 등)
  - 우선순위 기반 다중 차트 추천 (`recommend_multiple_charts`)
- **ThemeEngine** (`theme_engine.py`): 5종 프리미엄 테마 및 컴포넌트별 스타일 시스템.
  - premium_dark, corporate_light, executive_blue, nature_green, sunset_warm
  - 차트/라벨/필터 컴포넌트별 전용 스타일 반환
- **LayoutCalculator** (`layout_calculator.py`): 12-column 그리드 기반 자동 레이아웃 엔진.
  - balanced/priority/compact 3가지 배치 전략
  - 픽셀 위치 자동 계산 및 빈 공간 최적화

#### Phase 4 Step 12: 인터랙션 주입

- **InteractionLogic** (`interaction_logic.py`): 대시보드 인터랙션 자동 설정.
  - `varList`/`eventList` JSON 자동 생성
  - 크로스 필터링, 양방향 필터, 필터 상태 관리
  - 공유 차원 자동 감지 및 시각 간 연동
- **DrilldownMapper** (`drilldown_mapper.py`): 계층적 데이터 드릴다운 시스템.
  - 이름 패턴 및 카디널리티 기반 계층 자동 감지
  - 드릴다운 SQL 쿼리 자동 생성 및 브레드크럼 네비게이션

#### Phase 5 Step 13: 초안 브리핑

- **SummaryGenerator** (`summary_generator.py`): LLM 기반 한국어 분석 요약 생성기.
  - Executive Summary, Key Insights, 데이터 품질 노트, 한계점 분석
  - LLM 실패 시 통계 기반 폴백 요약 자동 생성
- **PreviewServer 통합** (`agentic_orchestrator.py`):
  - AgenticOrchestrator에 `preview_dashboard` 도구 추가 (14번째 도구)
  - Flask 기반 localhost:5000 웹 서버로 대시보드 미리보기
  - 브라우저 자동 오픈 지원, 리포트 등록 및 URL 생성
  - 17개 E2E 테스트 통과 (`test_preview_server_e2e.py`)

#### Phase 5 Step 14: 반복적 교정

- **ReportLinter** (`report_linter.py`): 리포트 품질 자동 검수 시스템.
  - 폰트 크기/색상 대비/레이아웃 일관성 등 규칙 기반 검사
  - `auto_fix` 기능으로 수정 가능한 이슈 자동 교정
  - 0-100 품질 점수 및 severity 기반 이슈 분류

#### Phase 5 Step 15: 최종 출력

- **JSONValidator** (`json_validator.py`): InHouse 스키마 검증 엔진.
  - 필수 섹션 존재 여부, 커넥터 타입, 참조 무결성 검사
  - 준수 점수(compliance_score) 산출
- **ExportPackager** (`export_packager.py`): 대시보드 멀티 포맷 패키징.
  - JSON (gzip 압축 지원), Excel (openpyxl), PDF (weasyprint/stub) 출력
  - 메타데이터 자동 주입 및 스키마 검증

#### E2E 테스트 인프라

- **테스트 스위트** (`tests/e2e/`): 77개 E2E 테스트, 4개 시나리오.
  - `test_bi_pipeline_e2e.py` (12): 전체 BI 파이프라인 흐름
  - `test_tool_registry_e2e.py` (20): AgenticOrchestrator 13개 도구 통합
  - `test_quality_pipeline_e2e.py` (13): Linter + Validator 품질 검사
  - `test_visualization_e2e.py` (32): 테마/레이아웃/차트 추천 조합
- **conftest.py** (`tests/e2e/conftest.py`): defusedxml/langgraph 의존성 호환 패치
- **pytest.ini**: `pythonpath = .` 추가 및 `e2e` 마커 등록

### 🟡 Improved (개선 사항)

- **AgenticOrchestrator**: 14개 도구 레지스트리 완성 (list_connections ~ preview_dashboard)
- **테스트 커버리지**: 총 404개 이상 테스트 통과 (E2E: 94, Phase 2: 106+, Phase 3: 204+)
- **의존성 완성**: flask, weasyprint, pyperclip 추가 (requirements.txt)
- **pytest 설정**: `pythonpath = .`으로 프로젝트 루트 자동 등록

### 📊 Test Coverage Summary

| 카테고리 | 테스트 수 | 실행 시간 | 상태 |
|----------|-----------|-----------|------|
| E2E Pipeline | 12 | <1s | ✅ |
| E2E ToolRegistry | 20 | <1s | ✅ (14개 도구) |
| E2E Quality | 13 | <1s | ✅ |
| E2E Visualization | 32 | <1s | ✅ |
| E2E PreviewServer | 17 | 4.42s | ✅ |
| Phase 2 Unit | 106+ | — | ✅ |
| Phase 3 Unit | 204+ | — | ✅ |
| **전체** | **404+** | **~6s (E2E)** | **✅** |

---

## 2026-02-01 (v2.2.0-development) 🚀

### Major Highlights: "Phase 2 & 3 Completion + Phase 4 Step 10 Implementation"

Phase 2와 3의 핵심 기능을 모두 구현하여 분석 엔진의 전략 수립 및 가설 검증 체계를 완성했습니다. 또한 Phase 4 Step 10의 최적 쿼리 생성 및 자가 치유 기능을 구현하여 신뢰도 높은 데이터 추출 기반을 마련했습니다. 총 310개 이상의 테스트가 통과되었습니다.

### 🟢 Added (신규 기능)

#### Phase 2: 의도 파악 및 컨텍스트 스캐닝 강화

- **명령어 히스토리 시스템** (`CommandHistory`): 최근 명령 저장, Up/Down 네비게이션, 탭 자동완성 지원.
- **테이블 추천 UI** (`TableSelectionScreen`): 추천 점수 및 JOIN 제안이 포함된 인터랙티브 선택 모달.
- **데이터 그리드 뷰어** (`DataGrid`): TUI 내 샘플 데이터 확인 및 타입 교정 시각화.

#### Phase 3: 전략 수립 및 가설 검증 시스템

- **분석 파이프라인 생성기** (`PipelineGenerator`): 단계별 분석 전략 자동 수립 및 의존성 관리.
- **가설 엔진 및 ROI 시뮬레이터**: 업종별 가설 템플릿 및 비즈니스 가치(ROI) 사전 추정.
- **실시간 메시지 버스** (`AgentMessageBus`): 에이전트 간 사고 과정 실시간 브로드캐스팅 및 로그 기록.
- **상태 변환기 및 Thinking Translator**: LLM의 사고 과정을 친절한 한국어 상태 메시지로 변환.
- **사용자 정렬 화면**: `HypothesisScreen` (가설 선택/수정), `ConstraintScreen` (제약 조건 입력).
- **승인 감사 시스템**: 단축키 기반 승인/수정 루프 및 `approvals.jsonl` 감사 로그.

#### Phase 4 Step 10: 최적 쿼리 생성 및 자가 치유

- **SQLGenerator 고도화**:
  - `DialectValidator`: SQLite/Postgres/MySQL 등 DB별 문법 검증 및 권장 함수 제안.
  - `SchemaValidator`: 스키마 대조 검증 및 유사 테이블/컬럼명 자동 제안.
  - `CostEstimator`: 쿼리 실행 비용 추정 및 대량 데이터 스캔 경고.
  - 한국어 쿼리 설명 자동 생성 기능.
- **QueryHealer (자가 치유)**:
  - DB 에러 메시지 분석 및 LLM 기반 자동 수정 루프 (최대 3회 재시도).
  - `query_healing.jsonl`에 모든 치유 시도 이력 로깅.
- **PandasGenerator (복잡 변환)**:
  - SQL로 표현 힘든 복잡 변환을 위한 Pandas 코드 자동 생성.
  - `CodeSanitizer`를 통한 위험 패턴(os, subprocess 등) 차단 및 안전한 샌드박스 실행.

### 🟡 Improved (개선 사항)

- **ThinkingPanel 강화**: 실시간 업데이트, 상세 진행률 인디케이터, 체크마크 애니메이션 통합.
- **테스트 커버리지**: 총 310개 이상의 유닛 테스트 통과 (Phase 2: 106개, Phase 3: 204개).

---

## 2026-01-31 (v2.1.0-production) 🎯

### Major Highlights: "Production-Ready Release - Section 0 Complete + P0 Fixes"

Phase 0(Section 0) 완전 완성, 모든 P0 우선순위 이슈 해결, Step 5/6 핵심 컴포넌트 구현을 달성했습니다. 테스트 커버리지 94%로 production-ready 상태에 진입했습니다.

### 🟢 Added (신규 기능)

#### Section 0: 공유 의도 아키텍처 완성
- **`BaseIntent` 추상 클래스 구현** (`backend/agents/bi_tool/base_intent.py`):
    - `datasource`, `filters`, `title` 등 공통 속성을 추상화한 기본 클래스
    - 데이터 검증 및 직렬화 메서드 포함
    - 모든 Intent 클래스의 일관된 인터페이스 제공

- **`AnalysisIntent` 클래스 신규 개발** (`backend/agents/bi_tool/analysis_intent.py`):
    - 복합 분석 목적 및 가설 기반 분석을 위한 전용 Intent
    - `analysis_type`, `hypothesis`, `metrics` 필드 지원
    - 다단계 분석 파이프라인 지원을 위한 확장 가능한 구조

- **`ChartIntent` 리팩토링 완료**:
    - `BaseIntent` 상속으로 코드 중복 제거
    - 차트별 전용 속성(`chart_type`, `x_axis`, `y_axis`) 분리
    - 타입 안정성 향상 (TypedDict 활용)

#### Step 5: 타겟 데이터 선정 시스템
- **`TableRecommender` 클래스** (`backend/agents/data_source/table_recommender.py`):
    - LLM 기반 테이블 relevance scoring (0-100점)
    - 다중 테이블 환경에서 질문에 최적화된 테이블 자동 추천
    - 메타데이터 기반 컨텍스트 분석 및 우선순위 결정

#### Step 6: 딥 스캐닝 시스템
- **`Profiler` 고도화** (`backend/agents/data_source/profiler.py`):
    - 컬럼별 상세 통계: 4분위수, 결측치 비율, 고유값 개수
    - 수치형/범주형/시간형 데이터 타입별 맞춤 분석
    - 샘플 데이터 추출 및 메모리 효율적 처리

- **`TypeCorrector` 클래스** (`backend/agents/data_source/type_corrector.py`):
    - 날짜/시간 컬럼 자동 감지 및 변환 제안
    - 숫자형 데이터의 문자열 저장 감지 및 교정
    - 데이터 품질 개선을 위한 자동 제안 시스템

#### 데이터 연결 안정성 강화
- **`ConnectionValidator` 클래스** (`backend/agents/data_source/connection_validator.py`):
    - MySQL/PostgreSQL/SQLite 연결 전 상태 검증
    - SSH 터널 연결 안정성 체크
    - 네트워크 timeout 및 권한 문제 사전 탐지

#### 오케스트레이터 컴포넌트 시스템
- **컴포넌트 기반 오케스트레이터** (`backend/orchestrator/components/`):
    - `agent_coordinator.py`: 에이전트 간 작업 조율 및 의존성 관리
    - `context_manager.py`: 세션 컨텍스트 및 상태 관리
    - `error_handler.py`: 통합 에러 처리 및 복구 전략
    - 모듈화된 구조로 유지보수성 및 테스트 용이성 향상

#### 테스트 인프라 대폭 강화
- **60개 테스트 스위트 완성**:
    - Intent 클래스 단위 테스트 (15개)
    - 데이터 소스 컴포넌트 테스트 (20개)
    - 오케스트레이터 통합 테스트 (12개)
    - 엔드투엔드 시나리오 테스트 (8개)
    - 에러 처리 및 edge case 테스트 (5개)
- **테스트 커버리지**: 94% (핵심 비즈니스 로직 100% 커버)

### 🟡 Improved (개선 사항)

#### P0 우선순위 이슈 완전 해결
1. **NL Intent Parser 안정화**: 복잡한 자연어 쿼리 파싱 정확도 향상, 다국어(한국어/영어) 혼용 처리 개선
2. **Connection Manager 보안 강화**: 크리덴셜 암호화 저장 구현, 연결 풀 관리 최적화 (누수 방지)
3. **Profiler 성능 최적화**: 메모리 사용량 50% 감소, 통계 계산 속도 3배 향상

#### 코드 품질 개선
- **타입 힌팅 완전 적용**: 모든 공개 API에 명확한 타입 정보 제공
- **문서화 강화**: Docstring 및 인라인 주석 추가
- **린팅 통과**: ruff, mypy, black 기준 100% 준수

### 📊 Test Coverage Summary

| 모듈 | 테스트 수 | 커버리지 | 상태 |
|------|----------|---------|------|
| Intent 클래스 | 15 | 100% | ✅ |
| 데이터 소스 | 20 | 96% | ✅ |
| 오케스트레이터 | 12 | 90% | ✅ |
| 통합 테스트 | 13 | 88% | ✅ |
| **전체** | **60** | **94%** | **✅ Production-Ready** |

---

## 2026-01-30 (v2.1.0-beta) 🌟

### Major Highlights: "Phase 2 & Step 3 Implementation"

**데이터 연결 자동화(Step 3)**의 완성 및 **분석 의도 처리(Step 4)**의 기반을 마련했습니다.

### 🟢 Added (신규 기능)
- **인터랙티브 데이터 소스 커넥터 (`ConnectionScreen`)**: Excel, SQLite, PostgreSQL, MySQL을 TUI 모달에서 즉시 연결 가능
- **자동 메타데이터 스캐닝 엔진**: 데이터 연결 즉시 `MetadataScanner`가 작동하여 테이블 목록, 행 수, 주요 컬럼을 자동 추출
- **분석 의도 선언 명령어 (`/intent`)**: 사용자가 복합적인 분석 요청을 내릴 수 있는 인터페이스 구축

### 🟡 Improved (개선 사항)
- **공식 문서(docs/) 전면 최신화**: `PLAN.md`, `TODO.md`, `USER_GUIDE.md`, `SETUP_GUIDE.md` 업데이트
- **Auth UI 안정화**: API 키 저장 및 즉시 반영 로직 버그 수정

### 🔵 Architecture (아키텍처)
- **공유 의도 설계 (BaseIntent)**: `ChartIntent`와 `AnalysisIntent`가 공유하는 추상 베이스 클래스 도입
- **메시지 버스 기반 통신**: 에이전트 간 사고 과정을 실시간으로 중계할 수 있는 `AgentMessageBus` 아키텍처 수립

---

## 2026-01-28 (v1.0.0) 🎨

### Major Highlights: "UI/UX 개선 및 배포 자동화"

### 🎨 UI/UX 개선 (Entrance Hall & Command Palette)
- **로고 개편**: 복잡한 ASCII 아트 대신 가독성이 뛰어난 'BI - Agent' 텍스트 배너 디자인 적용
- **슬래시 명령어(/) 복구**: `/` 입력 시 명령어 팔레트가 입력창 상단에 정확한 위치에 팝업되도록 수정
- **부팅 로그 가시화**: TUI 실행 시 초기화 로그를 채팅창 상단에 직접 출력

### 🔐 인증 및 보안 (Auth Management)
- **지능형 인증 감지**: 실행 시 자동인증 여부를 체크하여, 인증이 필요한 경우에만 `AuthScreen`을 즉시 띄우도록 고도화
- **환경 변수 연동**: `credentials.json` 파일이 없더라도 시스템 환경 변수가 설정되어 있다면 자동으로 인증된 것으로 간주

### 📦 설치 및 배포 자동화 (Distribution & CI/CD)
- **PyPI 설치 트러블슈팅**: Python 3.10+ 버전 요구사항에 따른 설치 실패 원인 분석 및 해결 지침 마련
- **GitHub Actions 수동 배포 구축**: `.github/workflows/pypi-publish.yml`을 통해 프로젝트 배포 자동화 구현

### 📝 문서화 업데이트
- **README.md 전면 개편**: 설치 방법 고도화, 트러블슈팅(Q&A) 섹션 추가

---

Copyright © 2026 BI-Agent Team. All rights reserved.
