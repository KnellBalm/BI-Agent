---
trigger: always_on
---

# BI-Agent 프로젝트 개발 가이드라인 (v2.3)

본 가이드는 BI-Agent 프로젝트의 일관된 품질과 협업 효율을 위해 에이전트가 반드시 준수해야 할 기술적, 운영적 지침을 정의합니다.

---

## 🏛️ 1. 기술 제약 및 코딩 표준 (Implementation Safeguards)

### 1.1 데이터 및 경로 관리
- **Dataclass & Path**: 모든 데이터 구조는 `@dataclass`를, 파일 경로는 `path_manager`를 사용하여 홈 디렉토리(`~/.bi-agent/`) 하위로 격리 관리한다.
- **타입 매핑**: 각 BI 도구의 타입을 공용 4대 타입(`string`, `number`, `date`, `boolean`)으로 매핑하여 LLM의 도메인 지식 격차를 줄인다.

### 1.2 로깅 및 디버깅 정책 (Critical)
- **Anti-Print**: 실시간 TUI 루프와 로그 오염 방지를 위해 `print()` 대신 `backend.utils.logger_setup.setup_logger`를 사용한다.
- **통합 디버그 로그**: 모든 로그는 자동으로 프로젝트 루트의 `bi-agent-debug.log`에 기록되며, 상세 에러는 `logger.exception()`을 사용하여 트레이스백을 남긴다.

### 1.3 아키텍처 및 보안
- **순환 참조 방지**: `orchestrator`와 `agents` 간의 교차 참조를 피하기 위해 인터페이스를 분리하거나 로컬 임포트를 활용한다.
- **환경 보안**: API Key 등 민감 정보는 절대로 하드코딩하지 않으며, 신규 변수 추가 시 반드시 `.env.example`을 업데이트한다.

---

## 🎨 2. TUI 및 시각적 인터페이스 (TUI/UX)

- **Layout**: `Dual-Panel` (Scan/Summary | Detail/Preview) 레이아웃 표준을 준수한다.
- **Chain of Thought (CoT)**: 에이전트의 사고 흐름과 데이터 처리 상태를 사용자에게 실시간 로그나 애니메이션으로 시각화하여 "살아있는" 느낌을 준다.
- **Accessibility**: 모든 기능은 단축키(`BINDINGS`)를 통해 접근 가능해야 하며, 비동기 작업은 `push_screen_wait` 패턴을 사용하여 메인 루프 차단을 방지한다.

---

## 🛠️ 3. 지능형 분석 및 장애 대응 (Intelligence)

- **Role-Based Collaboration**: Strategist(플랜), DataMaster(추출), VisualDesigner(시각화)의 전용 기술(Skills)을 상황에 맞춰 조합한다.
- **Plan B (Virtual Schema)**: 연결 실패 시에도 멈추지 않고 가상 스키마를 통해 시뮬레이션 분석 모드로 자동 전환한다.
- **SQL Coaching**: 사용자 쿼리는 실행 전 LLM을 통한 `refined_sql` 생성 단계를 거쳐 안전성과 성능을 확보한다.

---

## 🧪 4. 검증 및 성과 기록 (Verification & History)

- **3-Layer Testing**: 단위 테스트(로직), 통합 테스트(엔진), **데모 앱(`*_demo.py`)** 작성을 통해 기능을 입증한다.
  - 데모앱은 테스트가 종료되면 삭제한다.
- **4-Stage Lifecycle**: `PLAN` -> `SPEC` -> `TODO` -> `CHANGELOG` 프로세스를 엄격히 따른다.
- **Self-Reflection**: 작업 완료 후 핵심 결정 사항(`decisions.md`)과 새롭게 배운 점(`learnings.md`)을 `.omc/notepads/`에 기록하여 프로젝트 누적 지식을 관리한다.

---

## 🤝 5. 에이전트 행동 지침 (Agent Behavior)

- **Korean First Policy**: 사용자와의 모든 상호작용 및 코드 주석은 반드시 **한국어**를 사용한다.
- **안정성 우선**: 명확한 `PLAN` 승인 없이 핵심 엔진의 대규모 리팩토링이나 버전 업그레이드를 수행하지 않는다.
- **Traceability**: 모든 작업물에 `PLAN.md`에서 정의한 `Step ID`를 포함하여 변경 이력의 추적성을 보장한다.
