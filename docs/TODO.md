# BI-Agent 개발 TODO (Roadmap 2.1 기반)
> 마지막 업데이트: 2026-01-30
> 목표: 15단계 초정밀 여정 구현을 통한 분석가 최적화 워크스페이스 구축

---

## 🏗️ Phase 0: 아키텍처 파운데이션
- [x] **0.1 BaseIntent 클래스 구현**: `base_intent.py` 신규 생성
- [x] **0.2 ChartIntent 리팩토링**: `BaseIntent` 상속 및 구조 개선
- [x] **0.3 AnalysisIntent 구현**: 복합 분석용 의도 객체 설계
- [ ] **0.4 Unit Tests**: Intent 클래스군에 대한 단위 테스트 (커버리지 90%)

---

## 🛰️ Phase 2: 의도 파악 및 컨텍스트 스캐닝
- [x] **Step 4. 분석 의도 선언**: `/intent` 명령어 연동 및 기본 플랜 생성 로직 (LLM)
- [ ] **Step 4.2 히스토리 강화**: 최근 명령 저장 및 탭 자동완성 최적화
- [ ] **Step 5. 타겟 데이터 선정**: `TableRecommender` (LLM 기반 relevance scoring)
- [ ] **Step 5.2 추천 UI**: `TableSelectionScreen` 텍스추얼 모달 구현
- [ ] **Step 5.3 ERD 추론**: `ERDAnalyzer` (JOIN 관계 자동 감지)
- [ ] **Step 6. 딥 스캐닝**: `Profiler` 고도화 (4분위수, 결측치, 히스토그램 데이터)
- [ ] **Step 6.2 데이터 그리드**: TUI 내 샘플 데이터 테이블 뷰어 (`DataGrid`)
- [ ] **Step 6.3 타입 교정**: `TypeCorrector` (날짜/숫자 형식 자동 감지 및 변환 제안)

---

## 🧠 Phase 3: 전략 수립 및 가설 검증
- [ ] **Step 7. 분석 실행 플랜**: `PipelineGenerator` (3-7단계 상세 분석 파이프라인 생성)
- [ ] **Step 7.2 가설 템플릿**: 업종별 가설 엔진 (`RETAIL`, `FINANCE` 등)
- [ ] **Step 8. 사고 과정 시각화**: `AgentMessageBus` (비동기 큐 기반 메시지 브로드캐스팅)
- [ ] **Step 8.2 상태 변환기**: LLM 상태를 "스키마 해석 중" 등 한국어로 번환 출력
- [ ] **Step 9. 사용자 정렬**: `HypothesisScreen` (가설 선택 및 수정 UI)
- [ ] **Step 9.2 제약조건 입력**: `ConstraintScreen` (날짜/지역 필터 수동 입력)

---

## 📊 Phase 4: 리포트 조립 및 인터랙티브 설계
- [ ] **Step 10. 최적 쿼리 생성**: `SQLGenerator` 고도화 (Dialect 검증 및 설명 추가)
- [ ] **Step 10.2 자가 치유**: `QueryHealer` (실행 오류 발생 시 LLM 자동 수정 루프)
- [ ] **Step 11. 레이아웃 디자인**: `ChartRecommender` (데이터 특성별 차트 자동 매핑)
- [ ] **Step 11.2 테마 엔진**: 프리미엄 테마 3종 추가 및 폰트 메타데이터 연동
- [ ] **Step 12. 인터랙션 주입**: `varList`/`eventList` 자동 생성 및 JSON 바인딩

---

## 🏁 Phase 5: 결과 검수 및 최종 익스포트
- [ ] **Step 13. 초안 브리핑**: `SummaryGenerator` (한국어 요약 및 인사이트 추출)
- [ ] **Step 13.2 프리뷰 서버**: 로컬 Flask 서버 기반 대시보드 미리보기 가동
- [ ] **Step 14. 반복적 교정**: `/refine` 루프 (차트 변경, 필터 추가 실시간 처리)
- [ ] **Step 15. 최종 출력**: `JSONValidator` (InHouse 스키마 검증) 및 패키징 (Excel, PDF)

---

## 🚨 긴급 & 기술적 이슈
- [ ] **Section 9 Dependencies**: `flask`, `openpyxl`, `weasyprint`, `pyperclip` 등 추가
- [ ] **TUI 성능**: 대용량 데이터 스캔 시 비동기 처리 최적화
- [ ] **Tableau 연기**: `.twb` 생성 로직은 MVP 이후 단계로 조정

---
Copyright © 2026 BI-Agent Team. All rights reserved.
