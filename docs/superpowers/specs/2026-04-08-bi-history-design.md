# BI-Agent Phase 2: Analysis History 강화 설계 스펙

**날짜:** 2026-04-08
**상태:** 승인됨
**범위:** Phase 2 — SQLite 히스토리 인덱스, MCP 도구 4개, bi-solve 통합, /bi-history 스킬, 크로스 플랫폼 어댑터 표준화

---

## 1. 목적

Phase 1에서 만든 세션 파일 시스템을 검색/추천이 가능한 히스토리 자산으로 발전시킨다.

- 과거 분석을 찾고 재활용할 수 있어야 한다
- LLM 호출을 최소화하여 토큰 비용을 줄여야 한다
- 어떤 플랫폼(Claude Code, Antigravity, Codex)에서도 동일하게 작동해야 한다

---

## 2. 아키텍처

### 전체 흐름

```
세션 완료
    ↓
[G5] LLM이 태그 추출 (1회) → save_session() → history.db
                                              → index.md 업데이트 (기존 유지)

bi-solve G1 (새 분석 시작)
    ↓
get_similar_sessions(type, keywords) → history.db 태그 매칭 (LLM 없이)
    → 유사 세션 있으면: "참고할 과거 분석이 있습니다" 표시
    → 없으면: 조용히 G2 진행

/bi-history 검색
    ↓
search_history(query, filters) → history.db 필터링 (LLM 없이)
--deep 옵션 → 세션 파일 읽기 + LLM 심층 분석 (선택적)
```

### 두 레이어 구조

```
context/sessions/
├── history.db               ← 검색/추천 전용 (SQLite)
├── index.md                 ← 사람이 읽는 요약 목록 (Phase 1, 유지)
└── YYYY-MM-DD-{slug}.md     ← 실제 세션 내용 (Phase 1, 유지)
```

- **history.db:** 태그 필터링, 유사 세션 검색, 정기화 관리
- **index.md:** IDE에서 사람이 직접 읽는 히스토리 목록
- **세션 파일:** 분석 내용 원본, LLM이 --deep 검색 시 참조

---

## 3. SQLite 스키마

```sql
CREATE TABLE sessions (
    id          TEXT PRIMARY KEY,
    date        TEXT NOT NULL,
    title       TEXT NOT NULL,
    type        TEXT NOT NULL CHECK(type IN (
                    'diagnostic','exploratory','comparative',
                    'predictive','decision','monitoring')),
    result      TEXT CHECK(result IN (
                    'confirmed','rejected','inconclusive',
                    'in_progress', NULL)),
    domain_tags TEXT,    -- JSON 배열: ["매출","CAC","신규가입"]
    free_tags   TEXT,    -- JSON 배열: ["채널별-분리","유료광고"]
    file_path   TEXT NOT NULL,
    summary     TEXT,
    recurring   INTEGER DEFAULT 0   -- Phase 3 정기화 대비
);
```

**태그 구조 (C안 — B 중심):**
- `domain_tags`: 비즈니스 용어 (매출, 이탈, CAC, 리텐션 등) — 구조화
- `free_tags`: 분석 특이사항 자유 기술 3개 — 자유
- `type`, `result`: 고정 열거형 — 구조화

---

## 4. MCP 도구 4개

파일: `bi_agent_mcp/tools/history.py`

### 4-1. save_session

```python
def save_session(
    session_id: str,    # YYYY-MM-DD-{slug}
    title: str,
    type: str,          # 6개 유형 중 하나
    result: str,        # confirmed/rejected/inconclusive/in_progress
    domain_tags: list,  # 최대 5개
    free_tags: list,    # 최대 3개
    file_path: str,
    summary: str
) -> str:
    """[History] 완료된 분석 세션을 히스토리 DB에 저장한다."""
```

**호출 시점:** bi-solve G5 완료 후 LLM이 태그 추출 직후

### 4-2. get_similar_sessions

```python
def get_similar_sessions(
    type: str,               # 필수 — 유형 필터
    domain_tags: list = [],  # 선택 — 키워드 매칭
    limit: int = 3
) -> str:
    """[History] 유사한 과거 분석 세션을 반환한다. LLM 없이 태그 매칭."""
```

**호출 시점:** bi-solve G1 완료 직후 자동 호출
**반환 형식:**
```
• 2026-03-15 신규가입자 하락 원인 [확인] — 채널 CAC 급등으로 확인
• 2026-02-08 MRR 감소 진단 [미결] — 계절성 vs 이탈 구분 필요
```
결과 없으면 빈 문자열 반환 (G2로 조용히 진행)

### 4-3. search_history

```python
def search_history(
    query: str = None,    # 텍스트 검색 (제목+태그+요약)
    type: str = None,     # 유형 필터
    result: str = None,   # 결과 필터
    limit: int = 10
) -> str:
    """[History] 히스토리 검색. 태그/텍스트 기반, LLM 없이 실행."""
```

**호출 시점:** /bi-history 스킬에서 호출

### 4-4. tag_session

```python
def tag_session(
    session_id: str,
    add_tags: list
) -> str:
    """[History] 기존 세션에 태그를 추가한다."""
```

**호출 시점:** /bi-history 또는 사용자가 수동으로 태그 추가 시

---

## 5. bi-solve 통합 (skills/bi-solve.md 수정)

### G1 이후 추가 (자동 추천)

```markdown
[G1] 완료 후:
    get_similar_sessions(type={분류된유형}, domain_tags={추출된키워드}) 호출
    → 결과 있으면:
      "참고할 과거 분석이 있습니다:
       {결과 목록}
       확인하시겠어요? (예/건너뛰기)"
      - 예: 해당 세션 파일 경로 안내
      - 건너뛰기: 조용히 G2 진행
    → 결과 없으면: 바로 G2 진행 (안내 없음)
```

### G5 완료 후 추가 (자동 저장)

```markdown
[G5] 가설 검증 완료 후:
    1. 세션 파일 내용 기반 태그 추출 요청:
       "이 세션의 domain_tags(비즈니스 용어 최대 5개)와
        free_tags(분석 특이사항 최대 3개)를 JSON으로 반환해줘"
    2. save_session() 호출
    3. context/sessions/index.md 테이블에 한 줄 추가 (기존 방식 유지)
```

---

## 6. /bi-history 스킬

### 파일 구조 (크로스 플랫폼 표준)

```
skills/bi-history.md                                      ← 단일 소스
.claude/commands/bi-history.md                            ← Claude Code
.gemini/antigravity/global_workflows/bi-history.md        ← Antigravity
AGENTS.md                                                 ← /bi-history 항목 추가
```

### 사용 방법

```
/bi-history                          → 최근 10개 세션 목록
/bi-history "매출"                   → 키워드 검색
/bi-history --type diagnostic        → 진단형 전체
/bi-history --result confirmed       → 가설 확인된 것만
/bi-history "매출 광고" --deep       → LLM 심층 검색
```

### 실행 흐름 (skills/bi-history.md 내용)

```markdown
$ARGUMENTS 없음
    → search_history(limit=10) 호출 → 최근 세션 목록 표시

$ARGUMENTS 있음, --deep 없음
    → search_history(query=$ARGUMENTS, type=..., result=...) 호출
    → 결과 표시 (LLM 없이)

$ARGUMENTS + --deep
    → search_history()로 후보 추출
    → 해당 세션 파일들을 읽고 LLM이 의미 기반 분석
    → "가장 관련 있는 세션: ..." 요약 제공
```

---

## 7. 크로스 플랫폼 어댑터 표준 (전체 프로젝트 적용)

### 원칙

모든 bi-* 스킬은 다음 4개 파일을 항상 함께 가진다:

```
skills/bi-{name}.md                                       ← 단일 소스 (워크플로우 정의)
.claude/commands/bi-{name}.md                             ← Claude Code (/bi-{name})
.gemini/antigravity/global_workflows/bi-{name}.md         ← Antigravity
AGENTS.md                                                 ← Codex 등 (항목 추가)
```

### Phase 2에서 소급 추가할 Antigravity 어댑터 (기존 스킬)

Phase 1에서 누락된 기존 스킬들의 Antigravity 어댑터를 일괄 추가한다:

```
.gemini/antigravity/global_workflows/
├── bi-solve.md      ✅ Phase 1 완료
├── bi-connect.md    ← 소급 추가
├── bi-explore.md    ← 소급 추가
├── bi-analyze.md    ← 소급 추가
├── bi-stats.md      ← 소급 추가
├── bi-ab.md         ← 소급 추가
├── bi-viz.md        ← 소급 추가
├── bi-report.md     ← 소급 추가
└── bi-history.md    ← Phase 2 신규
```

**어댑터 파일 형식 (공통 템플릿):**
```markdown
# /bi-{name} — {설명}

이 워크플로우를 실행할 때 `skills/bi-{name}.md` 파일을 읽고 지침을 따른다.

## 실행 트리거
사용자가 "/bi-{name}" 또는 관련 키워드를 입력할 때 활성화.
```

---

## 8. 파일 맵

| 파일 | 작업 |
|---|---|
| `bi_agent_mcp/tools/history.py` | 신규 |
| `bi_agent_mcp/server.py` | 수정 (도구 4개 등록) |
| `context/sessions/history.db` | 신규 (자동 생성) |
| `skills/bi-history.md` | 신규 |
| `.claude/commands/bi-history.md` | 신규 |
| `.gemini/antigravity/global_workflows/bi-history.md` | 신규 |
| `.gemini/antigravity/global_workflows/bi-{connect,explore,analyze,stats,ab,viz,report}.md` | 신규 (소급 8개) |
| `skills/bi-solve.md` | 수정 (G1 추천 + G5 저장) |
| `AGENTS.md` | 수정 (bi-history 항목) |
| `tests/unit/test_history.py` | 신규 |

---

## 9. 테스트 기준

```python
# 정상 케이스
test_save_session_creates_db_entry()
test_get_similar_sessions_by_type()
test_get_similar_sessions_no_results_returns_empty()
test_search_history_by_keyword()
test_search_history_by_filter()
test_tag_session_adds_tags()

# 에러 케이스
test_save_session_invalid_type()
test_search_history_empty_db()
```

---

## 10. 제외 범위

- Phase 3 (Ad-hoc → 정기화): `recurring` 컬럼만 미리 추가, 기능은 미구현
- LLM 기반 자동 태그 개선 (현재 1회 호출로 충분)
- 히스토리 시각화 대시보드
