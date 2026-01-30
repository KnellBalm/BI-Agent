# BI-Agent Changelog (2026-01-30)

## 🌟 Major Highlights: "Phase 2 & Step 3 Implementation"

오늘의 업데이트는 **데이터 연결 자동화(Step 3)**의 완성 및 **분석 의도 처리(Step 4)**의 기반을 마련하는 데 집중되었습니다. 상세 구현 계획(Detailed Implementation Plan)을 수립하고 이에 맞춰 코어 모듈을 대폭 업데이트했습니다.

---

### 🟢 Added (신규 기능)
- **인터랙티브 데이터 소스 커넥터 (`ConnectionScreen`)**:
    - Excel, SQLite, PostgreSQL, MySQL을 TUI 모달에서 즉시 연결 가능.
    - 선택한 소스 타입에 따라 입력 폼이 동적으로 변환되는 UX 구현.
- **자동 메타데이터 스캐닝 엔진**:
    - 데이터 연결 즉시 `MetadataScanner`가 작동하여 테이블 목록, 행 수, 주요 컬럼을 자동 추출.
    - 스캔 결과를 TUI 채팅창에 가독성 높은 요약 형태로 출력.
- **분석 의도 선언 명령어 (`/intent`)**:
    - 사용자가 복합적인 분석 요청(예: "작년 대비 매출 하락 원인 분석")을 내릴 수 있는 인터페이스 구축.
    - 입력된 의도를 LLM이 분석하여 5~7단계의 실행 파이프라인으로 변환하는 기초 로직 구현.

### 🟡 Improved (개선 사항)
- **공식 문서(docs/) 전면 최신화**:
    - `PLAN.md`: 15단계 마일스톤을 Roadmap 2.1 버전으로 고도화 (Section 0 파운데이션 단계 포함).
    - `TODO.md`: 현재 진행 상황 및 향후 기술 부채를 단계별로 재정리.
    - `USER_GUIDE.md`: 새로운 TUI 명령어 시스템 및 분석 워크플로우 반영.
    - `SETUP_GUIDE.md`: `flask`, `weasyprint` 등 신규 의존성 패키지 안내 추가.
- **Auth UI 안정화**: API 키 저장 및 즉시 반영 로직 버그 수정.

### 🔵 Architecture (아키텍처)
- **공유 의도 설계 (BaseIntent)**:
    - `ChartIntent`와 `AnalysisIntent`가 공유하는 추상 베이스 클래스를 도입하여 데이터 모델의 일관성 확보.
- **메시지 버스 기반 통신**:
    - 에이전트 간 사고 과정을 실시간으로 중계할 수 있는 `AgentMessageBus` 아키텍처 수립.

---

### 🚀 Next Steps
1. **Step 5. 타겟 데이터 선정**: 다중 테이블 환경에서 최적 테이블 추천 알고리즘 완성.
2. **Step 8. 사고 과정 시각화**: `ThinkingPanel`을 메시지 버스와 연동하여 실시간 진행률 표시.
3. **Step 10. 자가 치유 쿼리**: SQL 실행 에러 시 AI가 자동으로 수정 제안하는 루프 구현.

---
**업데이트 일자**: 2026-01-30
**버전**: V2.1.0-beta
Copyright © 2026 BI-Agent Team. All rights reserved.
