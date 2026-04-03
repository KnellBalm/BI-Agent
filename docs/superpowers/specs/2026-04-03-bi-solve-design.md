# BI-Agent Phase 1: Problem-First Orchestrator (bi-solve) 설계 스펙

**날짜:** 2026-04-03  
**상태:** 승인됨  
**범위:** Phase 1 — bi-solve 오케스트레이터, 사전 질문지 시스템, Playbook 라이브러리, 플랫폼 어댑터

---

## 1. 정체성 재정의

BI-Agent는 데이터 분석 도구 묶음이 아니다.

DA가 낯선 도메인(PA/MA/BA)에서 업무를 할 때 "다음에 뭘 해야 하는지" 알려주는 **분석 방법론 어시스턴트**다. BI 아웃풋(리포트, 대시보드)은 결과이지 목적이 아니다.

### 핵심 철학 (superpowers 벤치마킹)

| superpowers 원칙 | bi-solve 적용 |
|---|---|
| Systematic over ad-hoc | 분석 유형별 검증된 프레임워크 제공 |
| Evidence over claims | 가설 수립 게이트 → 검증 게이트 → 완료 선언 |
| 설계 승인 없이 구현 불가 | 사전 질문지 작성 → 승인 → 분석 실행 |
| 단일 질문 원칙 | 불명확한 문제에서 한 번에 하나씩 질문 |

### 대상 사용자

빅데이터/엔지니어링 백그라운드를 가진 DA로서 SaaS PA/MA/BA 업무를 처음 접하는 경우. 도메인 구분 없이 어떤 비즈니스 문제든 구조적으로 접근할 수 있어야 한다.

---

## 2. 분석 질문 유형 분류 (Playbook 기반)

문제를 도메인(PA/MA/BA)이 아닌 **질문 유형**으로 분류한다. 6개 유형이 실제 DA 업무의 95%를 커버한다.

| 유형 | 대표 질문 | 분석 패턴 |
|---|---|---|
| **진단 (Diagnostic)** | "왜 X가 바뀌었나?" | 지표 분해 → 세그먼트 드릴다운 → 원인 귀속 |
| **탐색 (Exploratory)** | "X가 어떻게 생겼나?" | 분포 → 패턴 → 이상치 |
| **비교 (Comparative)** | "A와 B 중 뭐가 나은가?" | 그룹 비교 → 통계 유의성 |
| **예측 (Predictive)** | "앞으로 어떻게 될까?" | 트렌드 → 예측 → 불확실성 |
| **결정 (Decision)** | "어떻게 해야 하나?" | 옵션 열거 → 트레이드오프 → 권고 |
| **모니터링 (Monitoring)** | "계속 봐야 할 것은?" | KPI 체계 → 기준선 → 알림 조건 |

---

## 3. bi-solve 오케스트레이터

### 전체 흐름

```
사용자: "이번 달 매출이 왜 떨어졌지?"
        ↓
    bi-solve
        ├─ [G1] 문제 분류 — 3-5 초기 질문으로 유형 파악
        ├─ [G2] 환경 체크 — 데이터 소스 유무 확인
        ├─ [G3] 프레임워크 승인 — Playbook 요약 제시 후 사용자 승인
        │        ↓ (승인)
        │   📝 사전 질문지 생성 → context/sessions/YYYY-MM-DD-{slug}.md
        │        ↓ (사용자 작성 완료)
        ├─ 모드 분기
        │   ├─ 소크라테스 모드: 가설 없음 / 데이터 불명확
        │   └─ Playbook 모드: 가설 있음 / 데이터 확보
        ├─ [G4] 가설 수립 — 분석 전 명시적 가설 기록
        ├─ 실행 — 기존 bi-* 도구 활용
        └─ [G5] 검증 완료 — 가설 확인/기각 후 완료 선언
                ↓
        "이 분석 정기화할까요?" 질문
```

### 5개 Gate 상세

| Gate | 조건 | 통과 기준 | 실패 시 |
|---|---|---|---|
| G1 문제 분류 | 항상 | 6개 유형 중 하나 특정 | 추가 질문 (1개씩) |
| G2 환경 체크 | 항상 | 데이터 소스 확인 | 소스 없으면 수동 분석 대안 제시 후 진행 |
| G3 프레임워크 승인 | 항상 | 사용자 "예" 또는 "수정" | 수정 요청 반영 후 재제시 |
| G4 가설 수립 | 실행 전 | 명시적 가설 기록 | 소크라테스 모드로 가설 도출 |
| G5 검증 완료 | 완료 전 | 가설 확인/기각 판단 | 추가 분석 제안 |

### 두 가지 실행 모드

**소크라테스 모드 (기본, 탐색 중일 때)**
- 유형별 문서화된 질문 세트(`context/socratic_questions/`) 사용
- 한 번에 하나의 질문 → 사용자 응답 → 다음 질문
- 목적: 사용자가 스스로 분석 방향을 발견하도록 유도

**Playbook 모드 (빠른 실행, 방향이 잡혔을 때)**
- `context/playbooks/{type}.md` 의 표준 분석 패턴 실행
- 단계별 체크리스트 제시
- 목적: 반복 분석 및 검증된 방법론 빠른 적용

**소크라테스 모드 트리거 조건:**
- G1에서 질문 유형이 여전히 불명확할 때
- G2에서 데이터 소스가 없을 때
- G4에서 가설이 없을 때 ("모르겠다")

---

## 4. 사전 질문지 시스템

### 파일 구조

```
context/sessions/
├── index.md                          # 분석 목록 인덱스
└── YYYY-MM-DD-{slug}.md              # 개별 세션
```

### 사전 질문지 템플릿

```markdown
# 분석 사전 질문지: {문제 제목}

**날짜:** YYYY-MM-DD  
**유형:** {진단/탐색/비교/예측/결정/모니터링}  
**모드:** {소크라테스/Playbook}  
**상태:** 작성 중 / 진행 중 / 완료

---

## 분석 목적
> (이 분석으로 무엇을 알고 싶은가?)

## 현재 상황
> (지금 어떤 상황이며, 무엇이 이상한가?)

## 보유 데이터
> (어떤 데이터 소스를 사용할 수 있나?)

## 초기 가설
> (원인에 대한 예상이 있다면? 없으면 공란)

## 성공 기준
> (어떤 결과가 나오면 이 분석이 완료됐다고 할 수 있나?)

---

## 분석 결과
> (분석 완료 후 작성)

## 핵심 발견
> 

## 결론 및 다음 액션
> 

## 정기화 여부
- [ ] 정기 분석으로 전환 (주기: )
```

### 인덱스 형식

```markdown
# 분석 히스토리 인덱스

| 날짜 | 문제 | 유형 | 결론 요약 | 정기화 |
|---|---|---|---|---|
| 2026-04-03 | 매출 하락 원인 | 진단 | 신규 채널 CAC 급등 | - |
```

---

## 5. Playbook 라이브러리

```
context/playbooks/
├── diagnostic.md      # 진단: 지표 분해 → 세그먼트 → 원인 귀속
├── exploratory.md     # 탐색: 분포 → 패턴 → 이상치
├── comparative.md     # 비교: 그룹 비교 → 통계 유의성
├── predictive.md      # 예측: 트렌드 → 예측 → 불확실성
├── decision.md        # 결정: 옵션 → 트레이드오프 → 권고
└── monitoring.md      # 모니터링: KPI 체계 → 기준선 → 알림

context/socratic_questions/
├── diagnostic_qs.md   # 진단형 소크라테스 질문 세트
├── exploratory_qs.md
├── comparative_qs.md
├── predictive_qs.md
├── decision_qs.md
└── monitoring_qs.md
```

각 Playbook 파일 구조:
```markdown
# {유형} 분석 Playbook

## 언제 사용하나
## 표준 분석 단계
## 체크리스트
## 흔한 함정
## 도메인별 변형 (SaaS / 커머스 / B2B)
```

---

## 6. 플랫폼 어댑터

### 원칙: 단일 소스 + 플랫폼별 얇은 래퍼

bi-solve 워크플로우 내용은 `skills/bi-solve.md` 한 곳에만 작성한다.
각 플랫폼 파일은 "여기를 보라"는 참조만 담는다. 내용이 바뀌면 `skills/bi-solve.md` 하나만 수정하면 된다.

```
skills/
└── bi-solve.md          ← 단일 소스 (전체 워크플로우 정의)

# 플랫폼 어댑터 (얇은 래퍼 — 각 AI 도구가 읽는 파일)
.claude/commands/bi-solve.md                        ← Claude Code (/bi-solve)
.gemini/antigravity/global_workflows/bi-solve.md    ← Gemini / Antigravity IDE
AGENTS.md                                           ← Codex 등

context/                 ← 모든 플랫폼 공유 데이터 (수정 없음)
```

### 플랫폼별 사용 방법

| 플랫폼 | 진입 방법 | 주요 모드 |
|---|---|---|
| Claude Code | `/bi-solve` 슬래시 명령 | 소크라테스 (대화형) |
| Antigravity IDE | global_workflows에서 bi-solve 실행 | Playbook (step-by-step) |
| Codex | AGENTS.md 지침 따라 자동 적용 | 둘 다 |

### 핸드오프 패턴 (Claude Code → Antigravity)

```
Claude Code에서 bi-solve 실행
    → 소크라테스 대화로 질문지 작성
    → context/sessions/파일 생성
         ↓
Antigravity IDE에서 파일 열기
    → 질문지 확인 후 Playbook 모드 실행
    → 분석 결과 파일에 직접 기록
```

---

## 7. 기존 bi-* 스킬 재배치

기존 스킬은 **코드 변경 없이** bi-solve의 실행 도구로 재포지셔닝된다.

| 스킬 | 역할 변경 | 독립 사용 |
|---|---|---|
| bi-connect | bi-solve G2에서 호출 | 가능 |
| bi-explore | 소크라테스 모드에서 호출 | 가능 |
| bi-analyze | G4-G5 사이 실행 | 가능 |
| bi-stats | 분석 실행 중 호출 | 가능 |
| bi-ab | 비교 Playbook에서 호출 | 가능 |
| bi-viz | 결과 시각화 | 가능 |
| bi-report | G5 이후 최종 아웃풋 | 가능 |
| bi-help | bi-solve 안내로 업데이트 | 가능 |
| bi-domain | 도메인 컨텍스트 관리 | 독립 사용 |
| bi-setup | 초기 설정 | 독립 사용 |

---

## 8. Phase 범위

### Phase 1 (현재 스펙)
- bi-solve 오케스트레이터 (Claude Code 스킬)
- 사전 질문지 생성 시스템
- Playbook 라이브러리 (6개 유형)
- 소크라테스 질문 세트
- AGENTS.md 업데이트
- context/sessions/ 인덱스

### Phase 2 (향후)
- Analysis History 강화 (검색, 태깅, 필터)
- 히스토리 기반 패턴 인식 ("비슷한 문제를 이전에 분석했습니다")

### Phase 3 (향후)
- Ad-hoc → 정기 분석 전환 자동화
- 정기 분석 스케줄 관리

---

## 9. 제외 범위

- MCP 서버 코드(`bi_agent_mcp/`) 변경 없음 — Phase 1은 스킬/컨텍스트 레이어만
- 기존 bi-* 스킬 코드 변경 없음
- 새로운 데이터 소스 연결 없음
