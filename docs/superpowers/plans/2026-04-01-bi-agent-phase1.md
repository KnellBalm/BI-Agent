# BI-Agent Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `bi_start()`와 `bi_orchestrate()` 구현으로 자연어 → 분석 계획 end-to-end 흐름을 완성하고, 미커밋 도구 파일들을 git에 반영한다.

**Architecture:** `bi_agent_mcp/tools/orchestrator.py`에 두 함수를 새로 추가한다. `bi_start()`는 요청 의도를 분류해 가이드 모드 또는 오케스트레이터 모드로 분기하고, `bi_orchestrate()`는 스키마 파악 → 의도 분류 → SQL 컨텍스트 → 분석 가이드 → 실행 순서 안내를 순서대로 수행해 종합 분석 계획을 반환한다. MCP 도구 특성상 LLM 호출은 불가하므로 Claude가 반환 결과를 보고 후속 도구(`run_query`, 분석 도구들)를 직접 호출하는 구조다.

**Tech Stack:** Python 3.11+, FastMCP, pandas (기존 패턴 유지)

---

## 파일 구조

| 액션 | 경로 | 역할 |
|------|------|------|
| Create | `bi_agent_mcp/tools/orchestrator.py` | `bi_start`, `bi_orchestrate`, `_classify_intent`, `_guide_mode` |
| Modify | `bi_agent_mcp/server.py` | orchestrator 도구 2개 등록 |
| Create | `tests/unit/test_orchestrator.py` | 단위 테스트 |
| Modify | `CLAUDE.md` | 분석 흐름 가이드 섹션 추가 |

---

## Task 1: 미커밋 파일 git에 반영

**Files:**
- Commit: `bi_agent_mcp/tools/airbyte.py`, `databricks.py`, `dbt_cloud.py`, `grafana.py`, `heap.py`, `redash.py`, `segment.py`
- Commit: `bi_agent_mcp/server.py` (위 도구 등록 포함), `CLAUDE.md`

- [ ] **Step 1: 현재 상태 확인**

```bash
git status
python3 -c "from bi_agent_mcp.server import mcp; print(len(mcp._tool_manager._tools))"
```

Expected: 169개 도구, `??` 파일들 목록 확인

- [ ] **Step 2: 테스트 통과 확인**

```bash
python3 -m pytest tests/unit/ -q --no-header 2>&1 | tail -3
```

Expected: `passed` (실패 없이 통과)

- [ ] **Step 3: 커밋**

```bash
git add bi_agent_mcp/tools/airbyte.py \
        bi_agent_mcp/tools/databricks.py \
        bi_agent_mcp/tools/dbt_cloud.py \
        bi_agent_mcp/tools/grafana.py \
        bi_agent_mcp/tools/heap.py \
        bi_agent_mcp/tools/redash.py \
        bi_agent_mcp/tools/segment.py \
        bi_agent_mcp/server.py \
        CLAUDE.md

git commit -m "feat: 미등록 외부 연동 도구 7개 추가 및 server.py 등록 (airbyte/databricks/dbt/grafana/heap/redash/segment)"
```

---

## Task 2: orchestrator.py 구현

**Files:**
- Create: `bi_agent_mcp/tools/orchestrator.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/unit/test_orchestrator.py` 파일 생성:

```python
"""orchestrator.py 단위 테스트."""
from unittest.mock import patch, MagicMock
import pytest


# ── bi_start 테스트 ──────────────────────────────────────────────────────────

def test_bi_start_no_connection_guides_user():
    """연결 없으면 connect_db 안내를 반환해야 한다."""
    from bi_agent_mcp.tools.orchestrator import bi_start
    with patch("bi_agent_mcp.tools.orchestrator._connections", {}):
        result = bi_start("매출 분석해줘")
    assert "연결" in result
    assert "connect_db" in result


def test_bi_start_guide_mode_for_how_questions():
    """'어떻게' 포함 요청은 가이드 모드를 반환해야 한다."""
    from bi_agent_mcp.tools.orchestrator import bi_start
    mock_conn = {"mydb": MagicMock()}
    with patch("bi_agent_mcp.tools.orchestrator._connections", mock_conn):
        result = bi_start("매출 분석 어떻게 해?")
    assert "가이드" in result or "도구" in result or "워크플로우" in result


def test_bi_start_orchestrator_mode_for_analyze_requests():
    """'분석해줘' 요청 + conn_id 있으면 오케스트레이터 모드를 반환해야 한다."""
    from bi_agent_mcp.tools.orchestrator import bi_start
    mock_conn = {"mydb": MagicMock()}
    with patch("bi_agent_mcp.tools.orchestrator._connections", mock_conn), \
         patch("bi_agent_mcp.tools.orchestrator.bi_orchestrate") as mock_orch:
        mock_orch.return_value = "## BI 분석 실행 계획"
        result = bi_start("이번 달 매출 왜 떨어졌어?", conn_id="mydb")
    mock_orch.assert_called_once_with("이번 달 매출 왜 떨어졌어?", "mydb")
    assert "BI 분석 실행 계획" in result


def test_bi_start_uses_first_connection_when_no_conn_id():
    """conn_id 없어도 연결이 있으면 첫 번째 연결로 오케스트레이터 모드 실행."""
    from bi_agent_mcp.tools.orchestrator import bi_start
    mock_conn = {"first_db": MagicMock()}
    with patch("bi_agent_mcp.tools.orchestrator._connections", mock_conn), \
         patch("bi_agent_mcp.tools.orchestrator.bi_orchestrate") as mock_orch:
        mock_orch.return_value = "## BI 분석 실행 계획"
        bi_start("매출 하락 원인 찾아줘")
    mock_orch.assert_called_once_with("매출 하락 원인 찾아줘", "first_db")


# ── bi_orchestrate 테스트 ────────────────────────────────────────────────────

def test_bi_orchestrate_returns_error_for_unknown_conn():
    """존재하지 않는 conn_id면 [ERROR] 반환."""
    from bi_agent_mcp.tools.orchestrator import bi_orchestrate
    with patch("bi_agent_mcp.tools.orchestrator._connections", {}):
        result = bi_orchestrate("매출 분석", "nonexistent")
    assert result.startswith("[ERROR]")
    assert "nonexistent" in result


def test_bi_orchestrate_returns_full_plan():
    """연결 있으면 SQL 컨텍스트, 도구 가이드, 가설, 다음 단계가 모두 포함된 계획 반환."""
    from bi_agent_mcp.tools.orchestrator import bi_orchestrate
    mock_conn = {"mydb": MagicMock()}
    with patch("bi_agent_mcp.tools.orchestrator._connections", mock_conn), \
         patch("bi_agent_mcp.tools.orchestrator.get_schema", return_value="## Schema\n- orders(id, amount)"), \
         patch("bi_agent_mcp.tools.orchestrator.generate_sql", return_value="## SQL 생성 요청\n질문: 매출"), \
         patch("bi_agent_mcp.tools.orchestrator.bi_tool_selector", return_value="### 핵심 도구\n- revenue_analysis"), \
         patch("bi_agent_mcp.tools.orchestrator.hypothesis_helper", return_value="### 가설\n1. 신규 고객 감소"), \
         patch("bi_agent_mcp.tools.orchestrator.suggest_analysis", return_value="1. 핵심 지표 정의"):
        result = bi_orchestrate("이번 달 매출 왜 떨어졌어?", "mydb")
    assert "SQL" in result
    assert "도구" in result or "핵심" in result
    assert "run_query" in result
    assert "generate_report" in result


def test_bi_orchestrate_dashboard_output_includes_generate_dashboard():
    """output='dashboard'이면 generate_dashboard 안내가 포함돼야 한다."""
    from bi_agent_mcp.tools.orchestrator import bi_orchestrate
    mock_conn = {"mydb": MagicMock()}
    with patch("bi_agent_mcp.tools.orchestrator._connections", mock_conn), \
         patch("bi_agent_mcp.tools.orchestrator.get_schema", return_value="schema"), \
         patch("bi_agent_mcp.tools.orchestrator.generate_sql", return_value="sql context"), \
         patch("bi_agent_mcp.tools.orchestrator.bi_tool_selector", return_value="tools"), \
         patch("bi_agent_mcp.tools.orchestrator.hypothesis_helper", return_value="hypotheses"), \
         patch("bi_agent_mcp.tools.orchestrator.suggest_analysis", return_value="analysis"):
        result = bi_orchestrate("매출 현황", "mydb", output="dashboard")
    assert "generate_dashboard" in result


# ── _classify_intent 테스트 ──────────────────────────────────────────────────

def test_classify_intent_revenue_decline():
    from bi_agent_mcp.tools.orchestrator import _classify_intent
    assert _classify_intent("이번 달 매출 왜 하락했어?") == "revenue_decline"


def test_classify_intent_churn():
    from bi_agent_mcp.tools.orchestrator import _classify_intent
    assert _classify_intent("이탈률이 늘었어") == "churn_increase"


def test_classify_intent_general():
    from bi_agent_mcp.tools.orchestrator import _classify_intent
    assert _classify_intent("데이터 좀 봐줘") == "general"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
python3 -m pytest tests/unit/test_orchestrator.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'bi_agent_mcp.tools.orchestrator'`

- [ ] **Step 3: orchestrator.py 구현**

`bi_agent_mcp/tools/orchestrator.py` 생성:

```python
"""BI 분석 오케스트레이터 — bi_start, bi_orchestrate."""
from __future__ import annotations

from bi_agent_mcp.tools.db import _connections, get_schema
from bi_agent_mcp.tools.text_to_sql import generate_sql
from bi_agent_mcp.tools.bi_helper import bi_tool_selector
from bi_agent_mcp.tools.helper import hypothesis_helper
from bi_agent_mcp.tools.analysis import suggest_analysis

# 가이드 모드 트리거 키워드 (이 키워드가 있으면 방법 안내 우선)
_GUIDE_TRIGGERS = [
    "어떻게", "방법", "뭐부터", "가이드", "어떤 도구", "무엇을",
    "설명", "추천해", "알려줘 방법", "how", "what tool", "guide",
]

# 오케스트레이터 모드 트리거 키워드 (이 키워드가 있으면 분석 계획 생성)
_ORCHESTRATOR_TRIGGERS = [
    "분석해", "분석해줘", "왜", "원인", "파악해", "알아봐",
    "찾아줘", "계산해", "비교해", "어떻게 됐어", "어떤지", "얼마나",
    "떨어졌", "올랐", "늘었", "줄었", "analyze", "why", "cause",
]

# hypothesis_helper가 지원하는 problem_type 목록
_INTENT_MAP = [
    (["매출", "revenue", "sales", "하락", "감소"], "revenue_decline"),
    (["이탈", "churn", "retention"], "churn_increase"),
    (["전환", "conversion", "퍼널", "funnel", "드롭"], "conversion_drop"),
    (["성장", "growth", "증가", "신규"], "user_growth"),
    (["마케팅", "marketing", "캠페인", "campaign", "roas", "cac"], "marketing_effectiveness"),
    (["프로덕트", "product", "기능", "feature", "활성"], "product_performance"),
]


def _classify_intent(query: str) -> str:
    """쿼리에서 문제 유형(problem_type)을 분류한다."""
    q = query.lower()
    for keywords, problem_type in _INTENT_MAP:
        if any(kw in q for kw in keywords):
            return problem_type
    return "general"


def _guide_mode(query: str) -> str:
    """가이드 모드: 도구 추천 + 워크플로우 안내 반환."""
    lines = [
        "## BI 분석 가이드",
        "",
        f"**요청:** {query}",
        "",
        bi_tool_selector(query),
    ]
    return "\n".join(lines)


def bi_start(query: str, conn_id: str = "") -> str:
    """[Orchestrator] 자연어 요청을 받아 가이드 모드 또는 오케스트레이터 모드로 분기합니다.

    요청이 '어떻게 해?', '방법이 뭐야?' 같은 방법 질문이면 도구 추천과 워크플로우를
    안내하는 가이드 모드로 응답합니다. '왜 떨어졌어?', '분석해줘' 같은 실행 요청이면
    bi_orchestrate()를 호출해 end-to-end 분석 계획을 반환합니다.

    연결이 없으면 connect_db 사용 안내를 반환합니다.

    Args:
        query: 자연어 분석 요청. 예: "이번 달 매출 왜 떨어졌어?", "A/B 테스트 어떻게 해?"
        conn_id: connect_db로 등록한 연결 ID (선택, 없으면 첫 번째 연결 사용)

    Returns:
        가이드 또는 분석 계획 마크다운 문자열
    """
    # 연결 없으면 안내 반환
    if not conn_id and not _connections:
        return (
            "## 데이터 소스 연결이 필요합니다\n\n"
            "분석을 시작하려면 먼저 데이터 소스를 연결하세요.\n\n"
            "**DB 연결:**\n"
            "```\n"
            "connect_db(conn_id='mydb', db_type='postgresql', host='...', port=5432, "
            "database='...', username='...', password='...')\n"
            "```\n\n"
            "**파일 연결:**\n"
            "```\n"
            "connect_file(file_path='/path/to/data.csv', conn_id='myfile')\n"
            "```\n\n"
            "연결 후 다시 요청해 주세요."
        )

    query_lower = query.lower()
    is_guide = any(kw in query_lower for kw in _GUIDE_TRIGGERS)
    is_orchestrator = any(kw in query_lower for kw in _ORCHESTRATOR_TRIGGERS)

    # 가이드 트리거만 있으면 가이드 모드
    if is_guide and not is_orchestrator:
        return _guide_mode(query)

    # 오케스트레이터 모드: conn_id 결정
    effective_conn = conn_id or next(iter(_connections), "")
    if effective_conn:
        return bi_orchestrate(query, effective_conn)

    # conn_id도 연결도 없으면 가이드 모드로 fallback
    return _guide_mode(query)


def bi_orchestrate(query: str, conn_id: str, output: str = "report") -> str:
    """[Orchestrator] 자연어 분석 요청을 end-to-end 분석 계획으로 변환합니다.

    스키마 파악 → 의도 분류 → SQL 컨텍스트 생성 → 분석 도구 가이드 → 가설 프레임워크
    → 분석 방향 수립 → 다음 실행 순서 안내 순으로 처리해 종합 분석 계획을 반환합니다.

    MCP 도구 특성상 LLM을 직접 호출할 수 없으므로, 반환된 계획을 보고 Claude가
    run_query, 분석 도구, generate_report를 순서대로 호출합니다.

    Args:
        query: 자연어 분석 요청. 예: "이번 달 매출 왜 떨어졌어?"
        conn_id: connect_db로 등록한 연결 ID
        output: 출력 형식. "report" (기본) 또는 "dashboard"

    Returns:
        종합 분석 계획 마크다운 문자열. [ERROR]로 시작하면 오류.
    """
    if conn_id not in _connections:
        return (
            f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. "
            f"list_connections()로 연결 목록을 확인하세요."
        )

    progress: list[str] = []

    # Step 1: 스키마 파악
    schema = get_schema(conn_id)
    progress.append("→ 연결 및 스키마 확인 완료")

    # Step 2: 의도 분류
    problem_type = _classify_intent(query)
    progress.append(f"→ 분석 의도 분류: {problem_type}")

    # Step 3: 가설 프레임워크 + 도구 가이드
    hypothesis = hypothesis_helper(problem_type, data_context=schema[:500])
    tool_guide = bi_tool_selector(query)
    progress.append("→ 분석 도구 및 가설 프레임워크 수립 완료")

    # Step 4: SQL 컨텍스트 생성
    sql_context = generate_sql(conn_id, query)
    progress.append("→ SQL 생성 컨텍스트 준비 완료")

    # Step 5: 분석 방향 수립
    analysis_guide = suggest_analysis(schema[:1000], query)
    progress.append("→ 분석 방향 수립 완료")

    # 다음 실행 단계 구성
    next_steps = [
        f"1. 위 **SQL 생성** 섹션의 SQL을 `run_query(conn_id='{conn_id}', sql='...')`로 실행하세요",
        f"2. 결과를 받아 **분석 도구 가이드**의 핵심 도구(예: `revenue_analysis`, `trend_analysis`)를 호출하세요",
        f"3. 분석 완료 후 `generate_report(sections=[{{\"title\": \"분석 결과\", \"content\": \"...\"}}])`로 보고서를 저장하세요",
    ]
    if output == "dashboard":
        next_steps.append(
            f"4. 또는 `generate_dashboard(data='...', charts=[{{\"type\": \"line\", \"x\": \"날짜\", \"y\": \"매출\"}}])`로 대시보드를 생성하세요"
        )

    lines = [
        "# BI 분석 실행 계획",
        "",
        f"**요청:** {query}",
        f"**연결:** {conn_id}",
        "",
        "## 실행 로그",
        "\n".join(progress),
        "",
        "---",
        "",
        "## 1단계: SQL 생성",
        "",
        sql_context,
        "",
        "---",
        "",
        "## 2단계: 분석 도구 가이드",
        "",
        tool_guide,
        "",
        "---",
        "",
        "## 3단계: 가설 프레임워크",
        "",
        hypothesis,
        "",
        "---",
        "",
        "## 4단계: 분석 방향",
        "",
        analysis_guide,
        "",
        "---",
        "",
        "## 다음 실행 순서",
        "",
        *next_steps,
    ]

    return "\n".join(lines)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
python3 -m pytest tests/unit/test_orchestrator.py -v 2>&1 | tail -20
```

Expected: 10개 테스트 모두 PASSED

- [ ] **Step 5: 전체 테스트 통과 확인**

```bash
python3 -m pytest tests/unit/ -q --no-header 2>&1 | tail -3
```

Expected: 커버리지 80% 이상, 실패 없음

- [ ] **Step 6: 커밋**

```bash
git add bi_agent_mcp/tools/orchestrator.py tests/unit/test_orchestrator.py
git commit -m "feat: bi_start/bi_orchestrate 오케스트레이터 구현 및 테스트 추가"
```

---

## Task 3: server.py에 orchestrator 도구 등록

**Files:**
- Modify: `bi_agent_mcp/server.py`

- [ ] **Step 1: server.py 끝 부분에 등록 코드 추가**

`bi_agent_mcp/server.py`의 `if __name__ == "__main__":` 바로 앞에 추가:

```python
# orchestrator tools — 단일 진입점 및 end-to-end 분석 오케스트레이터
from bi_agent_mcp.tools.orchestrator import bi_start, bi_orchestrate

mcp.tool()(bi_start)
mcp.tool()(bi_orchestrate)
```

- [ ] **Step 2: 도구 수 확인**

```bash
python3 -c "from bi_agent_mcp.server import mcp; print(len(mcp._tool_manager._tools))"
```

Expected: 171 (기존 169 + bi_start + bi_orchestrate)

- [ ] **Step 3: 커밋**

```bash
git add bi_agent_mcp/server.py
git commit -m "feat: server.py에 bi_start/bi_orchestrate 등록 (도구 수 171개)"
```

---

## Task 4: CLAUDE.md 분석 흐름 가이드 추가

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: CLAUDE.md의 "## 스킬" 섹션 앞에 분석 흐름 가이드 추가**

`CLAUDE.md`에서 `## 스킬` 섹션을 찾아 그 앞에 아래 내용을 삽입:

```markdown
## 분석 흐름 가이드 (어떤 도구를 언제 쓸까?)

### 진입점 (항상 여기서 시작)

| 상황 | 사용할 도구 |
|------|------------|
| 처음 분석 요청 (방법 모름) | `bi_start(query)` |
| 연결 있고 바로 분석 원함 | `bi_start(query, conn_id="...")` |
| 복잡한 분석 직접 제어 | `bi_orchestrate(query, conn_id)` |

### 전체 흐름

```
자연어 요청
    │
bi_start(query, conn_id?)
    │
    ├─ 방법 질문 ("어떻게", "뭐부터") → 가이드 모드
    │   └─ bi_tool_selector() + hypothesis_helper() 반환
    │
    └─ 실행 요청 ("분석해", "왜", "원인") → 오케스트레이터 모드
        └─ bi_orchestrate() 호출
            └─ 스키마 → SQL 컨텍스트 → 도구 안내 → 가설 → 분석 방향 반환
                └─ Claude가 run_query → 분석 도구 → generate_report 순 실행
```

### 데이터 소스별 연결 방법

| 소스 | 도구 |
|------|------|
| PostgreSQL / MySQL / BigQuery | `connect_db` |
| CSV / Excel | `connect_file` |
| Databricks | `connect_databricks` |
| Redash | `connect_redash` |
| Grafana | `connect_grafana` |
| Segment | `connect_segment` |
| dbt Cloud | `connect_dbt_cloud` |
| Airbyte | `connect_airbyte` |
| Mixpanel | `connect_mixpanel` |
| Amplitude | `connect_amplitude` |
| Heap | `connect_heap` |

### BI 출력별 도구

| 출력 형태 | 도구 |
|-----------|------|
| 마크다운 보고서 | `generate_report(sections=[...])` |
| Chart.js HTML 대시보드 | `generate_dashboard(data, charts)` |
| Tableau TWBX | `generate_twbx(data, chart_type, title)` |
| Power BI | `connect_powerbi` → `list_powerbi_reports` |
| QuickSight | `connect_quicksight` → `list_quicksight_dashboards` |

```

- [ ] **Step 2: 도구 수 업데이트**

CLAUDE.md 상단의 `총 도구 수: 157개` 줄을 171개로 수정:

```
- **총 도구 수**: 171개 (2026-04 기준)
```

- [ ] **Step 3: 커밋**

```bash
git add CLAUDE.md
git commit -m "docs: CLAUDE.md 분석 흐름 가이드 및 진입점 도구 안내 추가"
```

---

## 완료 기준 체크리스트

```bash
# 1. 도구 수 확인
python3 -c "from bi_agent_mcp.server import mcp; print(len(mcp._tool_manager._tools))"
# Expected: 171

# 2. 전체 테스트 통과
python3 -m pytest tests/unit/ -q --no-header 2>&1 | tail -3
# Expected: all passed, coverage >= 80%

# 3. bi_start 동작 확인
python3 -c "
from bi_agent_mcp.tools.orchestrator import bi_start
print(bi_start('매출 분석 어떻게 해?'))[:200]
"
# Expected: 가이드 모드 출력

# 4. 커밋 히스토리 확인
git log --oneline -4
```

---

## Task 5: tools/ 디렉토리 구조 재편 (용도·단계별 분할)

**목표:** 40개 파일이 하나의 디렉토리에 혼재된 구조를 4개 하위 패키지로 분리한다.

**Files:**
- Create dirs: `tools/core/`, `tools/sources/`, `tools/analysis/`, `tools/output/`, `tools/helpers/`
- Move: 기존 40개 파일 → 아래 분류에 따라 이동
- Modify: `bi_agent_mcp/server.py` — import 경로 일괄 수정
- Modify: `tests/unit/*.py` — mock.patch 경로 일괄 수정

**목표 디렉토리 구조:**

```
bi_agent_mcp/tools/
├── core/             # 공통 인프라
│   ├── __init__.py
│   ├── db.py         # _connections, _get_conn, connect_db ...
│   └── files.py      # connect_file, query_file ...
├── sources/          # 외부 데이터 소스 연결
│   ├── __init__.py
│   ├── ga4.py
│   ├── amplitude.py
│   ├── mixpanel.py
│   ├── heap.py
│   ├── segment.py
│   ├── airbyte.py
│   ├── databricks.py
│   ├── dbt_cloud.py
│   ├── redash.py
│   ├── grafana.py
│   └── posthog.py
├── analysis/         # 분석 도구
│   ├── __init__.py
│   ├── analytics.py
│   ├── business.py
│   ├── product.py
│   ├── marketing.py
│   ├── stats.py
│   ├── ab_test.py
│   ├── forecast.py
│   ├── anomaly.py
│   ├── text_to_sql.py
│   ├── analysis.py
│   ├── compare.py
│   ├── cross_source.py
│   ├── validation.py
│   └── alerts.py
├── output/           # BI 출력 도구
│   ├── __init__.py
│   ├── dashboard.py
│   ├── tableau.py
│   ├── tableau_server.py
│   ├── powerbi.py
│   ├── quicksight.py
│   ├── looker_studio.py
│   ├── metabase.py
│   └── superset.py
├── helpers/          # 헬퍼·가이드·오케스트레이션
│   ├── __init__.py
│   ├── helper.py
│   ├── viz_helper.py
│   ├── bi_helper.py
│   ├── orchestration.py
│   ├── context.py
│   └── setup.py
└── orchestrator.py   # bi_start, bi_orchestrate (진입점)
```

> **⚠️ 주의:** mock.patch 경로가 모두 바뀐다. `bi_agent_mcp.tools.stats._connections` →
> `bi_agent_mcp.tools.analysis.stats._connections`. 테스트 파일을 먼저 수정하고 이동해야 한다.

- [ ] **Step 1: 하위 디렉토리 생성 및 __init__.py 작성**

```bash
mkdir -p bi_agent_mcp/tools/core \
         bi_agent_mcp/tools/sources \
         bi_agent_mcp/tools/analysis \
         bi_agent_mcp/tools/output \
         bi_agent_mcp/tools/helpers

touch bi_agent_mcp/tools/core/__init__.py \
      bi_agent_mcp/tools/sources/__init__.py \
      bi_agent_mcp/tools/analysis/__init__.py \
      bi_agent_mcp/tools/output/__init__.py \
      bi_agent_mcp/tools/helpers/__init__.py
```

- [ ] **Step 2: git mv로 파일 이동**

```bash
# core
git mv bi_agent_mcp/tools/db.py    bi_agent_mcp/tools/core/db.py
git mv bi_agent_mcp/tools/files.py bi_agent_mcp/tools/core/files.py

# sources
git mv bi_agent_mcp/tools/ga4.py        bi_agent_mcp/tools/sources/ga4.py
git mv bi_agent_mcp/tools/amplitude.py  bi_agent_mcp/tools/sources/amplitude.py
git mv bi_agent_mcp/tools/mixpanel.py   bi_agent_mcp/tools/sources/mixpanel.py
git mv bi_agent_mcp/tools/heap.py       bi_agent_mcp/tools/sources/heap.py
git mv bi_agent_mcp/tools/segment.py    bi_agent_mcp/tools/sources/segment.py
git mv bi_agent_mcp/tools/airbyte.py    bi_agent_mcp/tools/sources/airbyte.py
git mv bi_agent_mcp/tools/databricks.py bi_agent_mcp/tools/sources/databricks.py
git mv bi_agent_mcp/tools/dbt_cloud.py  bi_agent_mcp/tools/sources/dbt_cloud.py
git mv bi_agent_mcp/tools/redash.py     bi_agent_mcp/tools/sources/redash.py
git mv bi_agent_mcp/tools/grafana.py    bi_agent_mcp/tools/sources/grafana.py
git mv bi_agent_mcp/tools/posthog.py    bi_agent_mcp/tools/sources/posthog.py

# analysis
git mv bi_agent_mcp/tools/analytics.py    bi_agent_mcp/tools/analysis/analytics.py
git mv bi_agent_mcp/tools/business.py     bi_agent_mcp/tools/analysis/business.py
git mv bi_agent_mcp/tools/product.py      bi_agent_mcp/tools/analysis/product.py
git mv bi_agent_mcp/tools/marketing.py    bi_agent_mcp/tools/analysis/marketing.py
git mv bi_agent_mcp/tools/stats.py        bi_agent_mcp/tools/analysis/stats.py
git mv bi_agent_mcp/tools/ab_test.py      bi_agent_mcp/tools/analysis/ab_test.py
git mv bi_agent_mcp/tools/forecast.py     bi_agent_mcp/tools/analysis/forecast.py
git mv bi_agent_mcp/tools/anomaly.py      bi_agent_mcp/tools/analysis/anomaly.py
git mv bi_agent_mcp/tools/text_to_sql.py  bi_agent_mcp/tools/analysis/text_to_sql.py
git mv bi_agent_mcp/tools/analysis.py     bi_agent_mcp/tools/analysis/analysis.py
git mv bi_agent_mcp/tools/compare.py      bi_agent_mcp/tools/analysis/compare.py
git mv bi_agent_mcp/tools/cross_source.py bi_agent_mcp/tools/analysis/cross_source.py
git mv bi_agent_mcp/tools/validation.py   bi_agent_mcp/tools/analysis/validation.py
git mv bi_agent_mcp/tools/alerts.py       bi_agent_mcp/tools/analysis/alerts.py

# output
git mv bi_agent_mcp/tools/dashboard.py      bi_agent_mcp/tools/output/dashboard.py
git mv bi_agent_mcp/tools/tableau.py        bi_agent_mcp/tools/output/tableau.py
git mv bi_agent_mcp/tools/tableau_server.py bi_agent_mcp/tools/output/tableau_server.py
git mv bi_agent_mcp/tools/powerbi.py        bi_agent_mcp/tools/output/powerbi.py
git mv bi_agent_mcp/tools/quicksight.py     bi_agent_mcp/tools/output/quicksight.py
git mv bi_agent_mcp/tools/looker_studio.py  bi_agent_mcp/tools/output/looker_studio.py
git mv bi_agent_mcp/tools/metabase.py       bi_agent_mcp/tools/output/metabase.py
git mv bi_agent_mcp/tools/superset.py       bi_agent_mcp/tools/output/superset.py

# helpers
git mv bi_agent_mcp/tools/helper.py        bi_agent_mcp/tools/helpers/helper.py
git mv bi_agent_mcp/tools/viz_helper.py    bi_agent_mcp/tools/helpers/viz_helper.py
git mv bi_agent_mcp/tools/bi_helper.py     bi_agent_mcp/tools/helpers/bi_helper.py
git mv bi_agent_mcp/tools/orchestration.py bi_agent_mcp/tools/helpers/orchestration.py
git mv bi_agent_mcp/tools/context.py       bi_agent_mcp/tools/helpers/context.py
git mv bi_agent_mcp/tools/setup.py         bi_agent_mcp/tools/helpers/setup.py
```

- [ ] **Step 3: 각 이동된 파일 내부 import 경로 수정**

이동된 파일들 중 `bi_agent_mcp.tools.*` import를 사용하는 파일을 모두 수정:

```bash
# 수정 필요한 파일 목록 확인
grep -rl "from bi_agent_mcp.tools\." bi_agent_mcp/tools/ --include="*.py"
```

각 파일에서 `from bi_agent_mcp.tools.db import` →
`from bi_agent_mcp.tools.core.db import` 등으로 변경.

- [ ] **Step 4: server.py import 경로 일괄 수정**

`bi_agent_mcp/server.py`의 모든 import를 새 경로로 수정:

```python
# 예시: 변경 전 → 변경 후
from bi_agent_mcp.tools.db import ...          → from bi_agent_mcp.tools.core.db import ...
from bi_agent_mcp.tools.files import ...       → from bi_agent_mcp.tools.core.files import ...
from bi_agent_mcp.tools.ga4 import ...         → from bi_agent_mcp.tools.sources.ga4 import ...
from bi_agent_mcp.tools.amplitude import ...   → from bi_agent_mcp.tools.sources.amplitude import ...
from bi_agent_mcp.tools.analytics import ...   → from bi_agent_mcp.tools.analysis.analytics import ...
from bi_agent_mcp.tools.business import ...    → from bi_agent_mcp.tools.analysis.business import ...
from bi_agent_mcp.tools.dashboard import ...   → from bi_agent_mcp.tools.output.dashboard import ...
from bi_agent_mcp.tools.tableau import ...     → from bi_agent_mcp.tools.output.tableau import ...
from bi_agent_mcp.tools.helper import ...      → from bi_agent_mcp.tools.helpers.helper import ...
from bi_agent_mcp.tools.bi_helper import ...   → from bi_agent_mcp.tools.helpers.bi_helper import ...
# (전체 패턴은 동일하게 적용)
```

- [ ] **Step 5: 테스트 파일 mock.patch 경로 일괄 수정**

```bash
# 현재 mock.patch 경로 목록 확인
grep -rn "patch(\"bi_agent_mcp.tools\." tests/unit/ | head -20
```

`tests/unit/` 아래 모든 파일에서:
- `bi_agent_mcp.tools.stats.` → `bi_agent_mcp.tools.analysis.stats.`
- `bi_agent_mcp.tools.business.` → `bi_agent_mcp.tools.analysis.business.`
- `bi_agent_mcp.tools.db.` → `bi_agent_mcp.tools.core.db.`
- (전체 패턴 동일하게 적용)

- [ ] **Step 6: 서버 로드 및 테스트 통과 확인**

```bash
python3 -c "from bi_agent_mcp.server import mcp; print(len(mcp._tool_manager._tools))"
python3 -m pytest tests/unit/ -q --no-header 2>&1 | tail -3
```

Expected: 도구 수 동일, 모든 테스트 통과

- [ ] **Step 7: 커밋**

```bash
git add -A
git commit -m "refactor: tools/ 디렉토리 core/sources/analysis/output/helpers 5개 패키지로 분리"
```

---

## Task 6: 보안 Config 관리 (SecureConfig)

**목표:** 연결 정보(API 키, DB 비밀번호 등)를 `~/.bi-agent/config.json`에 저장하고, 민감 필드는 OS keyring으로 보호한다.

**Files:**
- Create: `bi_agent_mcp/tools/core/secure_config.py`
- Modify: `bi_agent_mcp/server.py` — 서버 시작 시 저장된 연결 자동 복원
- Create: `tests/unit/test_secure_config.py`

**설계:**

```
~/.bi-agent/
├── config.json        # 비민감 연결 메타데이터 (host, port, db_type 등)
└── .keyring           # OS keyring 사용 (password, api_key 등)
```

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/unit/test_secure_config.py`:

```python
"""SecureConfig 단위 테스트."""
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


def test_save_and_load_non_sensitive_fields(tmp_path):
    """비민감 필드는 config.json에 저장·로드된다."""
    from bi_agent_mcp.tools.core.secure_config import SecureConfig
    cfg = SecureConfig(config_dir=tmp_path)
    cfg.save_connection("mydb", {"host": "localhost", "port": 5432, "db_type": "postgresql"})
    loaded = cfg.load_connection("mydb")
    assert loaded["host"] == "localhost"
    assert loaded["db_type"] == "postgresql"


def test_sensitive_fields_not_stored_in_json(tmp_path):
    """password, api_key는 config.json에 평문으로 저장되지 않는다."""
    from bi_agent_mcp.tools.core.secure_config import SecureConfig
    cfg = SecureConfig(config_dir=tmp_path)
    with patch.object(cfg, "_keyring_set") as mock_ks:
        cfg.save_connection("mydb", {"host": "localhost", "password": "secret123"})
    config_file = tmp_path / "config.json"
    raw = json.loads(config_file.read_text())
    assert "password" not in raw.get("mydb", {})
    mock_ks.assert_called_once_with("mydb", "password", "secret123")


def test_load_returns_none_for_unknown_conn(tmp_path):
    """존재하지 않는 conn_id 조회는 None을 반환한다."""
    from bi_agent_mcp.tools.core.secure_config import SecureConfig
    cfg = SecureConfig(config_dir=tmp_path)
    assert cfg.load_connection("unknown") is None


def test_list_connections_returns_all_saved(tmp_path):
    """저장된 모든 연결 ID 목록을 반환한다."""
    from bi_agent_mcp.tools.core.secure_config import SecureConfig
    cfg = SecureConfig(config_dir=tmp_path)
    cfg.save_connection("db1", {"host": "h1"})
    cfg.save_connection("db2", {"host": "h2"})
    ids = cfg.list_connections()
    assert set(ids) == {"db1", "db2"}


def test_delete_connection(tmp_path):
    """연결 삭제 후 조회하면 None이 반환된다."""
    from bi_agent_mcp.tools.core.secure_config import SecureConfig
    cfg = SecureConfig(config_dir=tmp_path)
    cfg.save_connection("db1", {"host": "h1"})
    cfg.delete_connection("db1")
    assert cfg.load_connection("db1") is None
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
python3 -m pytest tests/unit/test_secure_config.py -v 2>&1 | head -10
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: secure_config.py 구현**

`bi_agent_mcp/tools/core/secure_config.py`:

```python
"""보안 설정 관리 — 연결 메타데이터 저장, 민감 필드 OS keyring 보호."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# 민감 필드 목록 — keyring에 저장
_SENSITIVE_KEYS = {"password", "api_key", "secret", "token", "private_key", "credentials_json"}

_DEFAULT_CONFIG_DIR = Path.home() / ".bi-agent"


class SecureConfig:
    """연결 설정을 저장·로드·삭제하는 보안 설정 관리자.

    비민감 필드는 config_dir/config.json에 저장한다.
    password, api_key 등 민감 필드는 OS keyring에 저장한다.
    keyring을 쓸 수 없는 환경(CI, Docker)에서는 환경변수 BI_AGENT_{CONN_ID}_{KEY} 로 fallback한다.
    """

    def __init__(self, config_dir: Path = _DEFAULT_CONFIG_DIR) -> None:
        self._config_dir = Path(config_dir)
        self._config_file = self._config_dir / "config.json"
        self._config_dir.mkdir(parents=True, exist_ok=True)
        # config.json이 없으면 빈 파일 생성
        if not self._config_file.exists():
            self._config_file.write_text("{}", encoding="utf-8")

    # ── keyring 래퍼 ─────────────────────────────────────────────────────────

    def _keyring_set(self, conn_id: str, key: str, value: str) -> None:
        """OS keyring에 민감 값을 저장한다. 실패 시 경고 로그."""
        try:
            import keyring
            keyring.set_password(f"bi-agent/{conn_id}", key, value)
        except Exception as e:
            logger.warning("keyring 저장 실패 (%s/%s): %s", conn_id, key, e)

    def _keyring_get(self, conn_id: str, key: str) -> Optional[str]:
        """OS keyring에서 민감 값을 로드한다. 없으면 환경변수 fallback."""
        try:
            import keyring
            val = keyring.get_password(f"bi-agent/{conn_id}", key)
            if val is not None:
                return val
        except Exception:
            pass
        # 환경변수 fallback: BI_AGENT_MYDB_PASSWORD
        import os
        env_key = f"BI_AGENT_{conn_id.upper()}_{key.upper()}"
        return os.environ.get(env_key)

    def _keyring_delete(self, conn_id: str, key: str) -> None:
        """OS keyring에서 민감 값을 삭제한다."""
        try:
            import keyring
            keyring.delete_password(f"bi-agent/{conn_id}", key)
        except Exception:
            pass

    # ── config.json 래퍼 ─────────────────────────────────────────────────────

    def _read_all(self) -> dict:
        try:
            return json.loads(self._config_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _write_all(self, data: dict) -> None:
        self._config_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── public API ────────────────────────────────────────────────────────────

    def save_connection(self, conn_id: str, fields: dict[str, Any]) -> None:
        """연결 정보를 저장한다. 민감 필드는 keyring, 나머지는 config.json."""
        meta: dict[str, Any] = {}
        for k, v in fields.items():
            if k in _SENSITIVE_KEYS:
                self._keyring_set(conn_id, k, str(v))
            else:
                meta[k] = v
        all_data = self._read_all()
        all_data[conn_id] = meta
        self._write_all(all_data)

    def load_connection(self, conn_id: str) -> Optional[dict[str, Any]]:
        """저장된 연결 정보를 반환한다. 없으면 None."""
        all_data = self._read_all()
        if conn_id not in all_data:
            return None
        result = dict(all_data[conn_id])
        # keyring에서 민감 필드 복원
        for key in _SENSITIVE_KEYS:
            val = self._keyring_get(conn_id, key)
            if val is not None:
                result[key] = val
        return result

    def list_connections(self) -> list[str]:
        """저장된 conn_id 목록을 반환한다."""
        return list(self._read_all().keys())

    def delete_connection(self, conn_id: str) -> None:
        """연결 정보를 삭제한다 (config.json + keyring 모두)."""
        all_data = self._read_all()
        all_data.pop(conn_id, None)
        self._write_all(all_data)
        for key in _SENSITIVE_KEYS:
            self._keyring_delete(conn_id, key)


# 싱글턴 인스턴스 — server.py에서 import해서 사용
secure_config = SecureConfig()
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
python3 -m pytest tests/unit/test_secure_config.py -v 2>&1 | tail -10
```

Expected: 5개 테스트 PASSED

- [ ] **Step 5: 커밋**

```bash
git add bi_agent_mcp/tools/core/secure_config.py tests/unit/test_secure_config.py
git commit -m "feat: SecureConfig — 연결 정보 저장/로드, 민감 필드 keyring 보호"
```

---

## Task 7: 다중 계정 지원 (GA4 및 소스 도구)

**목표:** `connect_ga4`를 포함한 소스 도구들이 사용자 정의 `conn_id`로 여러 계정을 동시에 관리할 수 있도록 수정한다.

**현황 문제:** `connect_ga4(property_id="123")` → `property_id`를 키로 사용 → 같은 계정의 다른 property 사용 시 덮어쓰기 발생.

**목표 API:**
```python
connect_ga4(conn_id="ga4_prod",   property_id="123456789")
connect_ga4(conn_id="ga4_staging", property_id="987654321")
get_ga4_report(conn_id="ga4_prod", ...)    # 각각 독립적으로 사용
get_ga4_report(conn_id="ga4_staging", ...)
```

**Files:**
- Modify: `bi_agent_mcp/tools/sources/ga4.py` (Task 5 이후 경로)
- Create: `tests/unit/test_ga4_multi_account.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/unit/test_ga4_multi_account.py`:

```python
"""GA4 다중 계정 지원 테스트."""
from unittest.mock import patch, MagicMock
import pytest


def test_connect_ga4_with_conn_id():
    """conn_id로 GA4 연결을 등록할 수 있다."""
    with patch("bi_agent_mcp.tools.sources.ga4._ga4_connections", {}) as mock_conns, \
         patch("bi_agent_mcp.tools.sources.ga4.BetaAnalyticsDataClient") as mock_client:
        mock_client.return_value = MagicMock()
        from bi_agent_mcp.tools.sources.ga4 import connect_ga4
        result = connect_ga4(conn_id="ga4_prod", property_id="123456789")
    assert "ga4_prod" in result or "성공" in result or "연결" in result


def test_connect_ga4_multiple_accounts():
    """두 개의 GA4 계정을 각각 다른 conn_id로 등록할 수 있다."""
    conns = {}
    with patch("bi_agent_mcp.tools.sources.ga4._ga4_connections", conns), \
         patch("bi_agent_mcp.tools.sources.ga4.BetaAnalyticsDataClient") as mock_client:
        mock_client.return_value = MagicMock()
        from bi_agent_mcp.tools.sources.ga4 import connect_ga4
        connect_ga4(conn_id="ga4_prod",    property_id="111")
        connect_ga4(conn_id="ga4_staging", property_id="222")
    assert "ga4_prod" in conns
    assert "ga4_staging" in conns
    assert conns["ga4_prod"]["property_id"] == "111"
    assert conns["ga4_staging"]["property_id"] == "222"


def test_get_ga4_report_uses_conn_id():
    """get_ga4_report는 conn_id로 올바른 연결을 사용한다."""
    mock_client = MagicMock()
    mock_client.run_report.return_value = MagicMock(
        row_count=1,
        dimension_headers=[MagicMock(name="date")],
        metric_headers=[MagicMock(name="sessions")],
        rows=[MagicMock(
            dimension_values=[MagicMock(value="2024-01-01")],
            metric_values=[MagicMock(value="100")]
        )]
    )
    conns = {"ga4_prod": {"client": mock_client, "property_id": "111"}}
    with patch("bi_agent_mcp.tools.sources.ga4._ga4_connections", conns):
        from bi_agent_mcp.tools.sources.ga4 import get_ga4_report
        result = get_ga4_report(
            conn_id="ga4_prod",
            metrics=["sessions"],
            dimensions=["date"],
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
    assert "sessions" in result or "date" in result


def test_get_ga4_report_error_for_unknown_conn_id():
    """존재하지 않는 conn_id는 [ERROR]를 반환한다."""
    with patch("bi_agent_mcp.tools.sources.ga4._ga4_connections", {}):
        from bi_agent_mcp.tools.sources.ga4 import get_ga4_report
        result = get_ga4_report(
            conn_id="nonexistent",
            metrics=["sessions"],
            dimensions=["date"],
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
    assert result.startswith("[ERROR]")
```

- [ ] **Step 2: ga4.py 수정 — conn_id 파라미터 추가**

`bi_agent_mcp/tools/sources/ga4.py`의 `connect_ga4`와 `get_ga4_report` 시그니처 수정:

```python
# 변경 전
def connect_ga4(property_id: str) -> str:
    ...
    _ga4_connections[property_id] = {"client": client, "property_id": property_id}

# 변경 후
def connect_ga4(conn_id: str, property_id: str) -> str:
    """[Source] Google Analytics 4 데이터 소스에 연결합니다.

    Args:
        conn_id: 이 연결을 식별하는 사용자 정의 ID. 예: "ga4_prod", "ga4_staging"
        property_id: GA4 Property ID (숫자 문자열). 예: "123456789"
    """
    ...
    _ga4_connections[conn_id] = {"client": client, "property_id": property_id}
    return f"GA4 연결 성공: conn_id='{conn_id}', property_id='{property_id}'"
```

```python
# 변경 전
def get_ga4_report(property_id: str, metrics: list, dimensions: list, ...) -> str:
    if property_id not in _ga4_connections:
        ...
    client = _ga4_connections[property_id]["client"]
    prop_id = _ga4_connections[property_id]["property_id"]

# 변경 후
def get_ga4_report(conn_id: str, metrics: list, dimensions: list, ...) -> str:
    """Args:
        conn_id: connect_ga4로 등록한 연결 ID
        ...
    """
    if conn_id not in _ga4_connections:
        return f"[ERROR] GA4 연결 '{conn_id}'를 찾을 수 없습니다. connect_ga4()로 먼저 연결하세요."
    client = _ga4_connections[conn_id]["client"]
    prop_id = _ga4_connections[conn_id]["property_id"]
```

- [ ] **Step 3: 테스트 통과 확인**

```bash
python3 -m pytest tests/unit/test_ga4_multi_account.py -v 2>&1 | tail -10
```

Expected: 4개 테스트 PASSED

- [ ] **Step 4: 전체 테스트 통과 확인**

```bash
python3 -m pytest tests/unit/ -q --no-header 2>&1 | tail -3
```

Expected: 모두 통과, 커버리지 80% 이상

- [ ] **Step 5: 커밋**

```bash
git add bi_agent_mcp/tools/sources/ga4.py tests/unit/test_ga4_multi_account.py
git commit -m "feat: GA4 다중 계정 지원 — connect_ga4에 conn_id 파라미터 추가"
```

---

## 최종 완료 기준 체크리스트 (전체)

```bash
# 1. 디렉토리 구조 확인
ls bi_agent_mcp/tools/

# Expected:
# core/  sources/  analysis/  output/  helpers/  orchestrator.py

# 2. 도구 수 확인
python3 -c "from bi_agent_mcp.server import mcp; print(len(mcp._tool_manager._tools))"
# Expected: 171+

# 3. 전체 테스트 통과
python3 -m pytest tests/unit/ -q --no-header 2>&1 | tail -3
# Expected: all passed, coverage >= 80%

# 4. 다중 GA4 계정 연결 확인
python3 -c "
from bi_agent_mcp.tools.sources.ga4 import _ga4_connections
print('다중 계정 구조 확인')
"

# 5. SecureConfig 동작 확인
python3 -c "
from bi_agent_mcp.tools.core.secure_config import SecureConfig
from pathlib import Path
import tempfile
with tempfile.TemporaryDirectory() as d:
    cfg = SecureConfig(Path(d))
    cfg.save_connection('test', {'host': 'localhost', 'port': 5432})
    print(cfg.load_connection('test'))
"
# Expected: {'host': 'localhost', 'port': 5432}
```
