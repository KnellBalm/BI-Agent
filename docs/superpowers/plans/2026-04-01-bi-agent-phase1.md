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
