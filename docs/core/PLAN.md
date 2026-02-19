# BI-Agent 초정밀 사용자 여정 및 세부 구현 명세 (Roadmap 2.1)

> **[ 🗺️ 전략/로드맵 ]** · [ 🛠️ 상세 설계 (DETAILED_SPEC)](./DETAILED_SPEC.md) · [ 📋 현재 실행 (TODO)](./TODO.md) · [ 📜 변경 이력 (CHANGELOG)](./CHANGELOG.md)

---

## 🎯 Recent Updates (2026-02-19)

**V2.3.0-development** 릴리스를 통해 다음을 달성했습니다:
- ✅ **Phase 4 Step 11~12 전체 구현**: ChartRecommender, ThemeEngine(5종), LayoutCalculator, InteractionLogic, DrilldownMapper
- ✅ **Phase 5 Step 13~15 전체 구현**: SummaryGenerator, ReportLinter, JSONValidator, ExportPackager
- ✅ **E2E 테스트 스위트 구축**: 77개 E2E 테스트 (4개 시나리오), 총 387개 이상 테스트 통과
- ✅ **AgenticOrchestrator 13개 도구 레지스트리**: 모든 BI 파이프라인 도구 통합 검증

상세 변경 내역은 [CHANGELOG.md](./CHANGELOG.md)를 참조하세요.

---

## 1. 프로젝트 비전
분석가가 터미널에 접속하여 최종 BI 리포트 결과물을 얻기까지, 에이전트의 사고 과정과 상호작용을 투명하게 공개하고 제어할 수 있는 **지능형 분석 워크스페이스**를 구축합니다.

---

## 2. 15단계 초정밀 마일스톤 및 세부 구현 로드맵

### [Phase 0: 파운데이션 리팩토링 - 필수 전제 조건]
#### **Section 0. 공유 의도 아키텍처 수립**
- [x] `BaseIntent` 추상 클래스 설계 (`datasource`, `filters`, `title` 공유)
- [x] `ChartIntent` 클래스 확장 및 리팩토링
- [x] `AnalysisIntent` 클래스 신규 개발 (복합 분석 목적 및 가설 기반)

---

### [Phase 1: 진입 및 환경 최적화]
#### **Step 1. 시스템 기동 (Launch)**
- [x] ASCII 배너 렌더링 엔진 고도화
- [x] `.env` 및 `credentials.json` 존재 여부 체크 로직
- [x] 필수 라이브러리(Textual, Rich 등) 환경 검증
#### **Step 2. 지능형 인증 (Smart Auth)**
- [x] LLM 공급자별 API 키 유효성 즉시 검증 (Ping test)
- [x] 마스킹된 키 표시 및 수정 전용 UI (`AuthScreen`)
- [x] 쿼터 소진 시 알림 및 자동 대체 모델 제안 로직
#### **Step 3. 데이터 엔진 연결 (Connection)**
- [x] SQLite/MySQL/Postgres 커넥터 UI 인터페이스
- [x] Excel 파일 경로 및 시트 스캔 기능
- [x] 연결 성공 시 기본적인 스키마 통계 자동 출력 (MetadataScanner 연동)

---

### [Phase 2: 의도 파악 및 컨텍스트 스캐닝]
#### **Step 4. 분석 의도 선언 (Intent)**
- [x] **`/intent` 명령어 도입**: 사용자의 복합적인 분석 의도를 접수하고 LLM 기반 실행 플랜 생성
- [x] 사용자 자연어 질문에서 분석 목적(성능, 트렌드, 이상치) 자동 추출
- [x] 최근 명령 히스토리 저장 및 탭 자동완성 최적화
#### **Step 5. 타겟 데이터 선정 (Targeting)**
- [x] 다중 테이블 환경에서 질문에 적합한 테이블 추천 알고리즘 (LLM 기반)
- [x] 테이블 선택용 인터랙티브 `TableSelectionScreen` 모달 UI 서비스
- [x] 테이블 간 ERD 관계 자동 추론 및 조인(Join) 필요성 제안
#### **Step 6. 딥 스캐닝 (Scanning)**
- [x] 컬럼별 상세 통계량(결측치 비율, 4분위수, 분포 등) 실시간 산출
- [x] 샘플 데이터(5~10행) 추출 및 TUI 내 그리드 컴포넌트 출력
- [x] 데이터 타입(Numerical, Categorical, Time) 자동 교정 시스템

---

### [Phase 3: 전략 수립 및 가설 검증]
#### **Step 7. 분석 실행 플랜 수립 (Planning)**
- [x] `/intent` 입력 시 **LLM 기반 상세 분석 파이프라인(Pipeline)** 제안 로직
- [x] 업종별/분석 테마별 가설 템플릿 엔진 구축
- [x] 분석 결과에서 기대되는 비즈니스 가치(ROI) 사전 시뮬레이션
#### **Step 8. 사고 과정 시각화 (Thinking CoT)**
- [x] 에이전트 간 내부 메시지 버스(`AgentMessageBus`) 실시간 노출 패널
- [x] LLM의 "생각 중..." 단계를 구체적인 한국어 상태 메시지로 변환
- [x] 장시간 분석 시 단계별 체크마크 및 진행률 인디케이터
#### **Step 9. 사용자 정렬 (Alignment)**
- [x] 생성된 가설 중 사용자가 선택/수정할 수 있는 `HypothesisScreen` 구축
- [x] 분석 제약 조건(기간, 지역, 카테고리) 추가 입력 워크플로우 (`ConstraintScreen`)
- [x] 에이전트의 제안에 대한 '승인/수정/반려' 단축키 시스템

---

### [Phase 4: 리포트 조립 및 인터랙티브 설계 ✅]
#### **Step 10. 최적 쿼리 생성 (Querying)**
- [x] 가설 검증용 SQL 자동 생성 및 DB 문법 호환성 체크
- [x] 실행 오류 시 에러 로그 기반 자동 쿼리 수정 루프 (Self-healing)
- [x] 복잡한 연산 시 Pandas Transformation 코드 자동 생성 및 실행
#### **Step 11. 레이아웃 디자인 (Designing)**
- [x] 데이터 특성별 최적 차트 추천 엔진 (`ChartRecommender` — 7가지 패턴)
- [x] 프리미엄 테마 엔진 기반 색상 팔레트 및 컴포넌트별 스타일 주입 (`ThemeEngine` — 5종 테마)
- [x] 컴포넌트 간 최적 배치(Grid) 자동 계산 알고리즘 (`LayoutCalculator` — 3가지 전략)
#### **Step 12. 인터랙션 주입 (Interactive)**
- [x] 전역 필터 연동을 위한 `varList` 및 `eventList` JSON 자동 생성 (`InteractionLogic`)
- [x] 드릴다운(Drill-down) 및 크로스 필터링 로직 매핑 (`DrilldownMapper`)
- [x] 양방향 크로스 필터, 필터 상태 관리, 브레드크럼 네비게이션

---

### [Phase 5: 결과 검수 및 최종 익스포트 ✅]
#### **Step 13. 초안 브리핑 (Preview)**
- [x] 분석 결과에 대한 LLM 한국어 요약 브리핑 및 인사이트 추출 (`SummaryGenerator`)
- [ ] 로컬 웹 서버 기반 웹 대시보드 프리뷰 자동 실행 로직
- [x] TUI 내에서 주요 지표(KPI Cards) 데이터 구조 렌더링
#### **Step 14. 반복적 교정 (Refine)**
- [x] 최종 결과물의 가시성 및 가독성 자동 검수(Linting) 단계 (`ReportLinter`)
- [x] 수정 가능한 이슈 자동 교정 (`auto_fix` 기능)
- [x] 추가 심층 분석 질문(Proactive Questions) 자동 제안 (`ProactiveQuestionGenerator`)
#### **Step 15. 최종 출력 및 배포 (Export)**
- [x] InHouse JSON 최종 빌드 및 스키마 정합성 검증 (`JSONValidator`)
- [x] Excel/PDF 리포트 패키징 및 gzip 압축 지원 (`ExportPackager`)
- [ ] **Note**: Tableau .twb 내보내기는 향후 단계로 연기됨

---

## 3. 리스크 및 대응 전략
- **LLM Rate Limit**: 적극적인 캐싱 및 로컬 폴백 모델 활용.
- **스키마 불일치**: 각 단계별 검증 및 사용자 확인 절차 강화.
- **TUI 반응성**: 비동기 워커 및 상태 표시기를 통한 응답성 유지.

---
Copyright © 2026 BI-Agent Team. All rights reserved.
