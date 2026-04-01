# BI-Agent MCP — 분석가 AI Assistant 디자인 스펙

**작성일:** 2026-04-01  
**상태:** 확정 (사용자 승인)  
**목표:** 데이터 소스 → 분석 → BI 전체를 커버하는 Data팀 AI 어시스턴트

---

## 1. 비전 및 목표

### 핵심 비전
> "분석가가 생각하는 일에 몰두할 수 있도록, 데이터 소스 연결부터 BI 대시보드 완성까지 전체 워크플로우를 AI가 보조한다."

### 사용자
- **지금**: 나 혼자 (개인 분석 도구)
- **목표**: Data팀 전체가 쓸 수 있는 공통 어시스턴트

### 사용 환경
- Claude Code 또는 Antigravity에 MCP 서버 연결

---

## 2. 전체 아키텍처

```
[Claude Code / Antigravity]
         │
         │ 자연어 요청
         ▼
┌─────────────────────────────────────────┐
│              bi_start()                 │
│          (단일 진입점, Phase 1 신규)      │
│                                         │
│  요청 복잡도/유형 판단                    │
│  ┌────────────┬──────────────────────┐  │
│  │  단순/명확  │    복잡/다단계         │  │
│  └─────┬──────┴───────────┬──────────┘  │
└────────┼──────────────────┼─────────────┘
         │                  │
         ▼                  ▼
┌─────────────────┐  ┌──────────────────────┐
│   가이드 모드    │  │   오케스트레이터 모드   │
│                 │  │                      │
│ bi_tool_selector│  │ bi_orchestrate()     │
│ hypothesis_helper│  │  (Phase 1 신규)      │
│                 │  │                      │
│ → 도구 추천 +   │  │ connect → schema →   │
│   워크플로우    │  │ sql → run → analyze  │
│   안내 반환     │  │ → report 자동 실행   │
│ → 사용자가 직접 │  │ → 각 단계 결과 출력  │
│   도구 호출     │  │                      │
└─────────────────┘  └──────────────────────┘
         │                  │
         └────────┬─────────┘
                  ▼
         Specialist Tools (169개)
```

### 경로 판단 기준

| 요청 유형 | 경로 |
|-----------|------|
| "매출 분석 어떻게 해?" / "뭐부터 해야 해?" | 가이드 모드 |
| "이번 달 매출 하락 원인 분석해줘" | 오케스트레이터 |
| "A/B 테스트 결과 해석해줘" | 오케스트레이터 |
| "RFM 분석 파라미터가 뭐야?" | 가이드 모드 |

---

## 3. 레이어별 상세 설계

### 3-1. 데이터 소스 레이어

| 분류 | 도구 | 상태 |
|------|------|------|
| **DB/DW** | PostgreSQL, MySQL, BigQuery, Databricks, dbt Cloud | 일부 미등록 |
| **파일/스토리지** | CSV/Excel, AWS S3 | S3 미구현 |
| **SaaS/이벤트** | Segment, Amplitude, Mixpanel, Heap, GA4 | 일부 미등록 |
| **수집 파이프라인** | Airbyte | 미등록 |
| **쿼리 레이어** | Redash, Grafana | 미등록 |

### 3-2. 분석 레이어

| 분류 | 주요 도구 |
|------|----------|
| 탐색/SQL | `get_schema`, `text_to_sql`, `run_query`, `profile_table` |
| 통계/검정 | `descriptive_stats`, `ttest_independent`, `chi_square_test`, `normality_test` |
| 도메인 분석 | `revenue_analysis`, `churn_analysis`, `funnel_analysis`, `rfm_analysis`, `ab_test_analysis` |
| 가이드 헬퍼 | `bi_tool_selector`, `hypothesis_helper`, `suggest_analysis` |

### 3-3. BI 출력 레이어

| 도구 | 파일 | 상태 |
|------|------|------|
| Chart.js HTML 대시보드 | `dashboard.py` | 등록됨 |
| Tableau TWBX 생성 | `tableau.py` | 등록됨 |
| Tableau TWBX 편집 | — | Phase 2 구현 |
| Tableau UI 가이드 | — | Phase 2 구현 |
| Power BI | `powerbi.py` | **미등록** |
| QuickSight | `quicksight.py` | **미등록** |
| Looker Studio | `looker_studio.py` | **미등록** |
| Superset | `superset.py` | **미등록** |
| Metabase | `metabase.py` | **미등록** |
| Power BI UI 가이드 | — | Phase 2 구현 |
| QuickSight UI 가이드 | — | Phase 2 구현 |

---

## 4. 신규 구현 상세

### 4-1. bi_start() — 단일 진입점

```python
bi_start(
    query: str,        # 자연어 요청
    conn_id: str = "", # 연결 ID (선택)
) -> str
```

- 의도 파악 후 가이드 모드 또는 오케스트레이터 모드로 분기
- 연결 없으면 `list_connections()` 결과로 연결 안내

### 4-2. bi_orchestrate() — 오케스트레이터

```python
bi_orchestrate(
    query: str,
    conn_id: str,
    output: str = "report",  # report / dashboard / insight
) -> str
```

**실행 단계:**
1. `get_schema()` — 테이블 구조 파악
2. `hypothesis_helper()` + `bi_tool_selector()` — 의도 분류 + 도구 결정
3. `text_to_sql()` → `run_query()` — SQL 생성 및 실행
4. Specialist Tool 호출 — 도메인 분석
5. `suggest_analysis()` → `generate_report()` — 인사이트 + 보고서

각 단계 결과를 즉시 스트리밍 출력. 오류 시 멈추고 원인 + 다음 선택지 제시.

### 4-3. bi_tool_guide() — BI 툴 UI 가이드 (Phase 2)

```python
bi_tool_guide(
    tool: str,        # tableau / powerbi / quicksight / looker / metabase / superset
    situation: str,   # 자유 텍스트 (예: "연결 오류", "차트 타입 변경")
    version: str = "" # 선택: 툴 버전
) -> str
```

**커버 상황:**
| 상황 | 예시 |
|------|------|
| 연결/인증 오류 | DB 재연결, OAuth 갱신 단계 |
| 차트 타입 변경 | 막대→꺾은선, 파이→테이블 버튼 경로 |
| 필터/파라미터 설정 | 날짜 범위, 드롭다운 추가 방법 |
| 퍼블리시/공유 | Tableau Server 게시, Power BI 서비스 배포 |
| 계산 필드 추가 | Calculated Field 생성 UI 경로 |

---

## 5. Phase 로드맵

### Phase 1: 핵심 완성

| 작업 | 설명 |
|------|------|
| 미등록 도구 server.py 등록 | powerbi, quicksight, mixpanel, airbyte, heap, databricks, looker_studio 등 |
| `bi_start()` 구현 | 단일 진입점, 경로 분기 |
| `bi_orchestrate()` 구현 | end-to-end 분석 파이프라인 |
| CLAUDE.md 업데이트 | 흐름 가이드, 도구 선택 기준 |

**Phase 1 완료 기준:**
```
bi_start("이번 달 매출 왜 떨어졌어?", conn_id="mydb")
→ 스키마 파악 → SQL 생성 → 실행 → 분석 → 보고서 (end-to-end 동작)
```

### Phase 2: BI 완성

| 작업 | 설명 |
|------|------|
| Tableau TWBX 편집 | `twbx_edit(file, instruction)` — 자연어로 수정 |
| `bi_tool_guide()` 구현 | Tableau, Power BI, QuickSight, Looker, Metabase UI 단계별 가이드 |
| Power BI / QuickSight 연동 강화 | 현재 파일 → 실제 API 연동 완성 |

### Phase 3: 팀 확장

- 다중 사용자, 권한 관리, 공유 기능
- 팀 공통 쿼리 라이브러리, KPI 딕셔너리 연동

---

## 6. 현재 갭 요약

| 항목 | 현황 | Phase |
|------|------|-------|
| `bi_start()` | 없음 | 1 |
| `bi_orchestrate()` | 없음 | 1 |
| 미등록 도구 7개+ | 파일 있음, 등록 안 됨 | 1 |
| AWS S3 연동 | 없음 | 1 |
| Tableau TWBX 편집 | 생성만 있음 | 2 |
| `bi_tool_guide()` | 없음 | 2 |
| Power BI / QuickSight API 완성 | 파일만 있음 | 2 |
