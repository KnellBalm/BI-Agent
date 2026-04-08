# Phase 2 Analysis History 강화 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** SQLite 기반 분석 히스토리 인덱스를 구축하고, bi-solve에 자동 추천/저장을 통합하며, /bi-history 검색 스킬과 크로스 플랫폼 어댑터를 완성한다.

**Architecture:** history.py에 4개 MCP 도구(save_session / get_similar_sessions / search_history / tag_session)를 구현한다. DB는 `context/sessions/history.db`에 자동 생성된다. bi-solve G1에서 유사 세션을 자동 추천하고, G5 완료 시 세션을 자동 저장한다. /bi-history 스킬은 기본적으로 SQL 필터링만 사용하고, --deep 옵션이 있을 때만 LLM을 호출한다.

**Tech Stack:** Python 3.11, sqlite3 (표준 라이브러리), json (표준 라이브러리), FastMCP

---

## 파일 맵

| 파일 | 작업 | 책임 |
|------|------|------|
| `bi_agent_mcp/tools/history.py` | 신규 | 4개 MCP 도구, SQLite 연결 |
| `bi_agent_mcp/server.py` | 수정 | history 도구 4개 등록 |
| `tests/unit/test_history.py` | 신규 | history 도구 단위 테스트 8개 |
| `skills/bi-history.md` | 신규 | bi-history 단일 소스 |
| `.claude/commands/bi-history.md` | 신규 | Claude Code 어댑터 |
| `.gemini/antigravity/global_workflows/bi-history.md` | 신규 | Antigravity 어댑터 |
| `.gemini/antigravity/global_workflows/bi-connect.md` | 신규 | 소급 Antigravity 어댑터 |
| `.gemini/antigravity/global_workflows/bi-explore.md` | 신규 | 소급 Antigravity 어댑터 |
| `.gemini/antigravity/global_workflows/bi-analyze.md` | 신규 | 소급 Antigravity 어댑터 |
| `.gemini/antigravity/global_workflows/bi-stats.md` | 신규 | 소급 Antigravity 어댑터 |
| `.gemini/antigravity/global_workflows/bi-ab.md` | 신규 | 소급 Antigravity 어댑터 |
| `.gemini/antigravity/global_workflows/bi-viz.md` | 신규 | 소급 Antigravity 어댑터 |
| `.gemini/antigravity/global_workflows/bi-report.md` | 신규 | 소급 Antigravity 어댑터 |
| `.gemini/antigravity/global_workflows/bi-help.md` | 신규 | 소급 Antigravity 어댑터 |
| `skills/bi-solve.md` | 수정 | G1 자동 추천 + G5 자동 저장 추가 |
| `AGENTS.md` | 수정 | /bi-history 항목 추가 |

---

### Task 1: tests/unit/test_history.py — 실패하는 테스트 먼저 작성

**Files:**
- Create: `tests/unit/test_history.py`

- [ ] **Step 1: 테스트 파일 생성**

```python
"""bi_agent_mcp.tools.history 단위 테스트."""
import json
import sqlite3
from unittest.mock import patch
import pytest

from bi_agent_mcp.tools.history import (
    save_session,
    get_similar_sessions,
    search_history,
    tag_session,
)


@pytest.fixture(autouse=True)
def tmp_db(tmp_path):
    """각 테스트마다 임시 DB 경로를 사용."""
    db_path = tmp_path / "history.db"
    with patch("bi_agent_mcp.tools.history._DB_PATH", db_path):
        yield db_path


def _save(
    session_id="2026-03-15-매출-하락",
    title="신규가입자 하락",
    type_="diagnostic",
    result="confirmed",
    domain_tags=None,
    free_tags=None,
):
    if domain_tags is None:
        domain_tags = ["매출", "CAC", "신규가입"]
    if free_tags is None:
        free_tags = ["채널별-분리"]
    return save_session(
        session_id=session_id,
        title=title,
        type=type_,
        result=result,
        domain_tags=domain_tags,
        free_tags=free_tags,
        file_path=f"context/sessions/{session_id}.md",
        summary="채널 CAC 급등으로 신규가입자 하락 확인",
    )


class TestSaveSession:
    def test_saves_entry_to_db(self, tmp_db):
        result = _save()
        assert "[OK]" in result
        conn = sqlite3.connect(str(tmp_db))
        row = conn.execute(
            "SELECT * FROM sessions WHERE id = '2026-03-15-매출-하락'"
        ).fetchone()
        assert row is not None
        conn.close()

    def test_invalid_type_returns_error(self):
        result = save_session(
            "id", "title", "invalid_type", "confirmed", [], [], "path", "summary"
        )
        assert "[ERROR]" in result
        assert "type" in result

    def test_invalid_result_returns_error(self):
        result = save_session(
            "id", "title", "diagnostic", "unknown_result", [], [], "path", "summary"
        )
        assert "[ERROR]" in result
        assert "result" in result

    def test_domain_tags_stored_as_json_array(self, tmp_db):
        _save(domain_tags=["매출", "CAC"])
        conn = sqlite3.connect(str(tmp_db))
        row = conn.execute("SELECT domain_tags FROM sessions").fetchone()
        assert json.loads(row[0]) == ["매출", "CAC"]
        conn.close()

    def test_replace_on_duplicate_session_id(self, tmp_db):
        _save(title="원래 제목")
        _save(title="수정된 제목")
        conn = sqlite3.connect(str(tmp_db))
        count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        assert count == 1
        conn.close()


class TestGetSimilarSessions:
    def test_returns_matching_session_by_tag(self, tmp_db):
        _save(domain_tags=["매출", "CAC"])
        result = get_similar_sessions(type="diagnostic", domain_tags=["매출"])
        assert "신규가입자 하락" in result

    def test_no_match_returns_empty_string(self, tmp_db):
        result = get_similar_sessions(type="diagnostic", domain_tags=["전환율"])
        assert result == ""

    def test_type_filter_excludes_other_types(self, tmp_db):
        _save(type_="diagnostic")
        result = get_similar_sessions(type="exploratory")
        assert result == ""

    def test_invalid_type_returns_error(self):
        result = get_similar_sessions(type="invalid")
        assert "[ERROR]" in result

    def test_limit_respected(self, tmp_db):
        for i in range(5):
            _save(
                session_id=f"2026-0{i+1}-01-test",
                title=f"세션{i}",
                domain_tags=["매출"],
            )
        result = get_similar_sessions(
            type="diagnostic", domain_tags=["매출"], limit=2
        )
        assert result.count("•") == 2


class TestSearchHistory:
    def test_returns_all_when_no_filter(self, tmp_db):
        _save()
        result = search_history()
        assert "신규가입자 하락" in result

    def test_keyword_filter_title_match(self, tmp_db):
        _save(title="신규가입자 하락")
        result = search_history(query="신규가입자")
        assert "신규가입자 하락" in result

    def test_keyword_no_match_returns_no_results_message(self, tmp_db):
        _save()
        result = search_history(query="존재하지않는키워드xyz")
        assert "없음" in result

    def test_type_filter_excludes_other_types(self, tmp_db):
        _save(type_="diagnostic")
        result = search_history(type="exploratory")
        assert "신규가입자" not in result

    def test_result_filter_excludes_other_results(self, tmp_db):
        _save(result="confirmed")
        result = search_history(result="rejected")
        assert "신규가입자" not in result

    def test_empty_db_returns_no_sessions_message(self, tmp_db):
        result = search_history()
        assert "없습니다" in result

    def test_invalid_type_returns_error(self):
        result = search_history(type="invalid")
        assert "[ERROR]" in result

    def test_invalid_result_returns_error(self):
        result = search_history(result="invalid")
        assert "[ERROR]" in result


class TestTagSession:
    def test_adds_new_tags(self, tmp_db):
        _save(domain_tags=["매출"])
        result = tag_session("2026-03-15-매출-하락", ["CAC", "광고비"])
        assert "[OK]" in result
        conn = sqlite3.connect(str(tmp_db))
        tags = json.loads(
            conn.execute("SELECT domain_tags FROM sessions").fetchone()[0]
        )
        assert "CAC" in tags
        assert "매출" in tags
        conn.close()

    def test_deduplicates_existing_tags(self, tmp_db):
        _save(domain_tags=["매출"])
        tag_session("2026-03-15-매출-하락", ["매출", "CAC"])
        conn = sqlite3.connect(str(tmp_db))
        tags = json.loads(
            conn.execute("SELECT domain_tags FROM sessions").fetchone()[0]
        )
        assert tags.count("매출") == 1
        conn.close()

    def test_invalid_session_id_returns_error(self, tmp_db):
        result = tag_session("not-existing-id", ["tag"])
        assert "[ERROR]" in result
```

- [ ] **Step 2: 테스트 실행 — ImportError 확인**

```bash
python3 -m pytest tests/unit/test_history.py -q --no-header 2>&1 | head -20
```

예상 출력: `ImportError: cannot import name 'save_session' from 'bi_agent_mcp.tools.history'` (모듈 없음)

---

### Task 2: bi_agent_mcp/tools/history.py — 4개 MCP 도구 구현

**Files:**
- Create: `bi_agent_mcp/tools/history.py`

- [ ] **Step 1: history.py 생성**

```python
"""[History] 분석 세션 히스토리 저장/검색 도구 — SQLite 기반."""
import json
import sqlite3
from pathlib import Path

_DB_PATH = Path(__file__).parents[2] / "context" / "sessions" / "history.db"

_VALID_TYPES = {
    "diagnostic", "exploratory", "comparative",
    "predictive", "decision", "monitoring",
}
_VALID_RESULTS = {"confirmed", "rejected", "inconclusive", "in_progress"}


def _get_conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id          TEXT PRIMARY KEY,
            date        TEXT NOT NULL,
            title       TEXT NOT NULL,
            type        TEXT NOT NULL,
            result      TEXT,
            domain_tags TEXT,
            free_tags   TEXT,
            file_path   TEXT NOT NULL,
            summary     TEXT,
            recurring   INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn


def save_session(
    session_id: str,
    title: str,
    type: str,
    result: str,
    domain_tags: list,
    free_tags: list,
    file_path: str,
    summary: str,
) -> str:
    """[History] 완료된 분석 세션을 히스토리 DB에 저장한다.

    Args:
        session_id: 세션 ID (YYYY-MM-DD-{slug} 형식)
        title: 분석 제목
        type: 분석 유형 (diagnostic/exploratory/comparative/predictive/decision/monitoring)
        result: 결과 (confirmed/rejected/inconclusive/in_progress)
        domain_tags: 비즈니스 용어 태그 목록 (최대 5개)
        free_tags: 분석 특이사항 자유 태그 목록 (최대 3개)
        file_path: 세션 파일 경로
        summary: 분석 요약 (1-2문장)
    """
    if type not in _VALID_TYPES:
        return f"[ERROR] 유효하지 않은 type: '{type}'. 허용값: {sorted(_VALID_TYPES)}"
    if result and result not in _VALID_RESULTS:
        return f"[ERROR] 유효하지 않은 result: '{result}'. 허용값: {sorted(_VALID_RESULTS)}"

    date = session_id[:10] if len(session_id) >= 10 else ""

    conn = _get_conn()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO sessions
               (id, date, title, type, result, domain_tags, free_tags, file_path, summary)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                date,
                title,
                type,
                result or None,
                json.dumps(domain_tags, ensure_ascii=False),
                json.dumps(free_tags, ensure_ascii=False),
                file_path,
                summary,
            ),
        )
        conn.commit()
        return f"[OK] 세션 저장 완료: {session_id}"
    finally:
        conn.close()


def get_similar_sessions(
    type: str,
    domain_tags: list = None,
    limit: int = 3,
) -> str:
    """[History] 유사한 과거 분석 세션을 반환한다. LLM 없이 태그 매칭.

    Args:
        type: 분석 유형 필터 (필수)
        domain_tags: 매칭할 도메인 태그 목록 (선택, 없으면 type만 필터)
        limit: 반환할 최대 세션 수 (기본값: 3)
    """
    if type not in _VALID_TYPES:
        return f"[ERROR] 유효하지 않은 type: '{type}'. 허용값: {sorted(_VALID_TYPES)}"

    if domain_tags is None:
        domain_tags = []

    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM sessions WHERE type = ? ORDER BY date DESC",
            (type,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return ""

    # 태그 매칭 점수 계산
    scored = []
    for row in rows:
        stored = json.loads(row["domain_tags"] or "[]")
        stored_lower = [t.lower() for t in stored]
        score = sum(1 for tag in domain_tags if tag.lower() in stored_lower)
        scored.append((score, row))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:limit]

    result_map = {
        "confirmed": "확인",
        "rejected": "기각",
        "inconclusive": "미결",
        "in_progress": "진행중",
    }
    lines = []
    for _, row in top:
        result_str = result_map.get(row["result"] or "", "—")
        summary = (row["summary"] or "")[:60]
        lines.append(f"• {row['date']} {row['title']} [{result_str}] — {summary}")

    return "\n".join(lines)


def search_history(
    query: str = None,
    type: str = None,
    result: str = None,
    limit: int = 10,
) -> str:
    """[History] 히스토리 검색. 태그/텍스트 기반, LLM 없이 실행.

    Args:
        query: 텍스트 검색어 (제목+태그+요약에서 검색, 선택)
        type: 유형 필터 (선택)
        result: 결과 필터 (선택)
        limit: 반환할 최대 세션 수 (기본값: 10)
    """
    if type and type not in _VALID_TYPES:
        return f"[ERROR] 유효하지 않은 type: '{type}'. 허용값: {sorted(_VALID_TYPES)}"
    if result and result not in _VALID_RESULTS:
        return f"[ERROR] 유효하지 않은 result: '{result}'. 허용값: {sorted(_VALID_RESULTS)}"

    conn = _get_conn()
    try:
        sql = "SELECT * FROM sessions WHERE 1=1"
        params: list = []
        if type:
            sql += " AND type = ?"
            params.append(type)
        if result:
            sql += " AND result = ?"
            params.append(result)
        sql += " ORDER BY date DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    if not rows:
        return "저장된 세션이 없습니다."

    # 텍스트 필터 (post-query, SQL LIKE보다 다국어 안전)
    if query:
        q_lower = query.lower()
        rows = [
            row
            for row in rows
            if q_lower
            in " ".join(
                [
                    row["title"] or "",
                    row["domain_tags"] or "",
                    row["free_tags"] or "",
                    row["summary"] or "",
                ]
            ).lower()
        ]

    if not rows:
        return f"'{query}' 검색 결과 없음."

    result_map = {
        "confirmed": "확인",
        "rejected": "기각",
        "inconclusive": "미결",
        "in_progress": "진행중",
    }
    type_map = {
        "diagnostic": "진단",
        "exploratory": "탐색",
        "comparative": "비교",
        "predictive": "예측",
        "decision": "결정",
        "monitoring": "모니터링",
    }

    lines = [f"검색 결과 {len(rows)}건:", ""]
    for row in rows:
        result_str = result_map.get(row["result"] or "", "—")
        type_str = type_map.get(row["type"], row["type"])
        summary = (row["summary"] or "")[:80]
        lines.append(
            f"• [{row['date']}] {row['title']} | {type_str} | {result_str}"
        )
        if summary:
            lines.append(f"  {summary}")
        lines.append(f"  파일: {row['file_path']}")

    return "\n".join(lines)


def tag_session(
    session_id: str,
    add_tags: list,
) -> str:
    """[History] 기존 세션에 태그를 추가한다.

    Args:
        session_id: 태그를 추가할 세션 ID
        add_tags: 추가할 태그 목록
    """
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not row:
            return f"[ERROR] 세션 ID '{session_id}'를 찾을 수 없습니다."

        existing = json.loads(row["domain_tags"] or "[]")
        merged = list(dict.fromkeys(existing + add_tags))  # 순서 유지 중복 제거

        conn.execute(
            "UPDATE sessions SET domain_tags = ? WHERE id = ?",
            (json.dumps(merged, ensure_ascii=False), session_id),
        )
        conn.commit()
        return f"[OK] 태그 추가 완료: {session_id} → {merged}"
    finally:
        conn.close()
```

- [ ] **Step 2: 테스트 실행 — 전부 통과 확인**

```bash
python3 -m pytest tests/unit/test_history.py -v --no-header 2>&1 | tail -30
```

예상 출력: `20 passed` (모든 테스트 통과)

- [ ] **Step 3: 커밋**

```bash
git add bi_agent_mcp/tools/history.py tests/unit/test_history.py
git commit -m "feat: [History] SQLite 기반 세션 히스토리 도구 4개 + 단위 테스트"
```

---

### Task 3: bi_agent_mcp/server.py — history 도구 4개 등록

**Files:**
- Modify: `bi_agent_mcp/server.py` (끝에서 두 번째 블록 — dbt_cloud 등록 바로 뒤)

- [ ] **Step 1: 현재 server.py의 마지막 등록 블록 확인**

```bash
tail -30 bi_agent_mcp/server.py
```

- [ ] **Step 2: history 도구 등록 블록 추가**

server.py에서 가장 마지막 `register_tool` 블록 뒤, `if __name__` 블록 앞에 다음을 추가한다:

```python
# history tools — 분석 세션 히스토리 저장/검색 (Phase 2)
from bi_agent_mcp.tools.history import (
    save_session,
    get_similar_sessions,
    search_history,
    tag_session,
)

register_tool(save_session, is_core=False)
register_tool(get_similar_sessions, is_core=False)
register_tool(search_history, is_core=False)
register_tool(tag_session, is_core=False)
```

- [ ] **Step 3: 도구 등록 확인**

```bash
python3 -c "
import os; os.environ['BI_AGENT_LOAD_ALL']='true'
from bi_agent_mcp.server import mcp
tools = list(mcp._tool_manager._tools.keys())
history_tools = [t for t in tools if t in ['save_session','get_similar_sessions','search_history','tag_session']]
print('History tools registered:', history_tools)
print('Total tools:', len(tools))
"
```

예상 출력:
```
History tools registered: ['save_session', 'get_similar_sessions', 'search_history', 'tag_session']
Total tools: 176
```

- [ ] **Step 4: 전체 테스트 — 기존 테스트 깨지지 않았는지 확인**

```bash
python3 -m pytest tests/unit/ -q --no-header 2>&1 | tail -5
```

예상 출력: `N passed` (기존 + 신규 테스트 모두 통과)

- [ ] **Step 5: 커밋**

```bash
git add bi_agent_mcp/server.py
git commit -m "feat: server.py에 history 도구 4개 등록"
```

---

### Task 4: skills/bi-history.md + 플랫폼 어댑터 2개

**Files:**
- Create: `skills/bi-history.md`
- Create: `.claude/commands/bi-history.md`
- Create: `.gemini/antigravity/global_workflows/bi-history.md`

- [ ] **Step 1: skills/bi-history.md 생성 (단일 소스)**

```markdown
# bi-history — 분석 히스토리 검색

과거 분석 세션을 검색하고 관리한다.
기본 검색은 LLM 없이 SQL 필터링만 사용한다. --deep 옵션이 있을 때만 LLM을 호출한다.

## 실행 규칙

1. 기본 검색은 LLM 없이 search_history() 하나로 완결한다
2. --deep 옵션이 명시된 경우에만 세션 파일을 읽고 LLM 분석을 수행한다
3. 결과에는 항상 세션 파일 경로(file_path)를 포함한다

---

## 실행 흐름

### $ARGUMENTS가 없는 경우 → 최근 목록

`search_history(limit=10)` 호출 → 최근 세션 10개 표시

### $ARGUMENTS가 있는 경우 (--deep 없음) → 키워드/필터 검색

`$ARGUMENTS`에서 다음을 파싱한다:
- `--type {값}`: 유형 필터 (diagnostic/exploratory/comparative/predictive/decision/monitoring)
- `--result {값}`: 결과 필터 (confirmed/rejected/inconclusive/in_progress)
- 위 플래그를 제외한 나머지 텍스트: query 검색어

`search_history(query=..., type=..., result=...)` 호출 → 결과 표시

### $ARGUMENTS + --deep → LLM 심층 검색

1. 위 방법으로 `search_history()`로 후보 추출
2. 결과의 각 `file_path`를 읽어 세션 내용 로드
3. LLM이 "가장 관련 있는 세션: ..." 형식으로 의미 기반 요약 제공

---

## 사용 예시

```
/bi-history                          → 최근 10개 세션 목록
/bi-history "매출"                   → 매출 관련 세션 검색
/bi-history --type diagnostic        → 진단형 전체 목록
/bi-history --result confirmed       → 가설 확인된 세션만
/bi-history "매출 광고" --deep       → LLM 심층 검색
```

## 사용 MCP 도구

- `search_history(query, type, result, limit)` — 히스토리 검색 (LLM 없음)
- `tag_session(session_id, add_tags)` — 기존 세션에 태그 추가
```

- [ ] **Step 2: .claude/commands/bi-history.md 생성 (Claude Code 어댑터)**

```markdown
# /bi-history — 분석 히스토리 검색

## 실행

이 스킬을 실행하기 전에 `skills/bi-history.md` 파일을 읽고 그 안의 지침을 정확히 따른다.

## 시작 방법

`$ARGUMENTS`가 없으면: `search_history(limit=10)`으로 최근 10개 표시
`$ARGUMENTS`가 있으면: 키워드/필터 파싱 후 `search_history()` 호출
`--deep` 플래그 있으면: 세션 파일 읽기 + LLM 심층 분석
```

- [ ] **Step 3: .gemini/antigravity/global_workflows/bi-history.md 생성 (Antigravity 어댑터)**

```markdown
# /bi-history — 분석 히스토리 검색 (Antigravity)

이 워크플로우를 실행할 때 `skills/bi-history.md` 파일을 읽고 지침을 따른다.

## 실행 트리거

사용자가 다음 중 하나를 말할 때 활성화:
- "bi-history", "히스토리 검색", "이전 분석", "과거 세션 찾아줘"

## Antigravity 팁

- `context/sessions/` 디렉토리를 사이드바에 열어두면 검색 결과의 파일을 바로 열 수 있다
- `--deep` 검색 시 세션 파일을 참조 탭으로 열어 LLM 분석 결과와 비교할 수 있다
```

- [ ] **Step 4: 커밋**

```bash
git add skills/bi-history.md .claude/commands/bi-history.md .gemini/antigravity/global_workflows/bi-history.md
git commit -m "feat: /bi-history 스킬 + Claude Code / Antigravity 어댑터"
```

---

### Task 5: 소급 Antigravity 어댑터 8개

**Files:**
- Create: `.gemini/antigravity/global_workflows/bi-connect.md`
- Create: `.gemini/antigravity/global_workflows/bi-explore.md`
- Create: `.gemini/antigravity/global_workflows/bi-analyze.md`
- Create: `.gemini/antigravity/global_workflows/bi-stats.md`
- Create: `.gemini/antigravity/global_workflows/bi-ab.md`
- Create: `.gemini/antigravity/global_workflows/bi-viz.md`
- Create: `.gemini/antigravity/global_workflows/bi-report.md`
- Create: `.gemini/antigravity/global_workflows/bi-help.md`

- [ ] **Step 1: bi-connect.md 생성**

파일: `.gemini/antigravity/global_workflows/bi-connect.md`

```markdown
# /bi-connect — 데이터 소스 연결 및 컨텍스트 로드

이 워크플로우를 실행할 때 `.claude/commands/bi-connect.md` 파일을 읽고 지침을 따른다.

## 실행 트리거

사용자가 다음 중 하나를 말할 때 활성화:
- "bi-connect", "데이터 연결", "DB 연결", "CSV 연결"
```

- [ ] **Step 2: bi-explore.md 생성**

파일: `.gemini/antigravity/global_workflows/bi-explore.md`

```markdown
# /bi-explore — 데이터 탐색

이 워크플로우를 실행할 때 `.claude/commands/bi-explore.md` 파일을 읽고 지침을 따른다.

## 실행 트리거

사용자가 다음 중 하나를 말할 때 활성화:
- "bi-explore", "데이터 탐색", "데이터 파악", "분포 확인"
```

- [ ] **Step 3: bi-analyze.md 생성**

파일: `.gemini/antigravity/global_workflows/bi-analyze.md`

```markdown
# /bi-analyze — 도메인 기반 심층 분석

이 워크플로우를 실행할 때 `.claude/commands/bi-analyze.md` 파일을 읽고 지침을 따른다.

## 실행 트리거

사용자가 다음 중 하나를 말할 때 활성화:
- "bi-analyze", "심층 분석", "원인 분석", "세그먼트 분석"
```

- [ ] **Step 4: bi-stats.md 생성**

파일: `.gemini/antigravity/global_workflows/bi-stats.md`

```markdown
# /bi-stats — 통계 분석

이 워크플로우를 실행할 때 `.claude/commands/bi-stats.md` 파일을 읽고 지침을 따른다.

## 실행 트리거

사용자가 다음 중 하나를 말할 때 활성화:
- "bi-stats", "통계 분석", "t-검정", "가설 검정", "ANOVA", "카이제곱"
```

- [ ] **Step 5: bi-ab.md 생성**

파일: `.gemini/antigravity/global_workflows/bi-ab.md`

```markdown
# /bi-ab — A/B 테스트 분석

이 워크플로우를 실행할 때 `.claude/commands/bi-ab.md` 파일을 읽고 지침을 따른다.

## 실행 트리거

사용자가 다음 중 하나를 말할 때 활성화:
- "bi-ab", "A/B 테스트", "실험 분석", "대조군 분석"
```

- [ ] **Step 6: bi-viz.md 생성**

파일: `.gemini/antigravity/global_workflows/bi-viz.md`

```markdown
# /bi-viz — 시각화 생성

이 워크플로우를 실행할 때 `.claude/commands/bi-viz.md` 파일을 읽고 지침을 따른다.

## 실행 트리거

사용자가 다음 중 하나를 말할 때 활성화:
- "bi-viz", "시각화", "대시보드 만들어줘", "Tableau", "차트"
```

- [ ] **Step 7: bi-report.md 생성**

파일: `.gemini/antigravity/global_workflows/bi-report.md`

```markdown
# /bi-report — 분석 리포트 생성

이 워크플로우를 실행할 때 `.claude/commands/bi-report.md` 파일을 읽고 지침을 따른다.

## 실행 트리거

사용자가 다음 중 하나를 말할 때 활성화:
- "bi-report", "리포트 생성", "분석 결과 정리", "보고서 만들어줘"
```

- [ ] **Step 8: bi-help.md 생성**

파일: `.gemini/antigravity/global_workflows/bi-help.md`

```markdown
# /bi-help — BI 분석 가이드

이 워크플로우를 실행할 때 `.claude/commands/bi-help.md` 파일을 읽고 지침을 따른다.

## 실행 트리거

사용자가 다음 중 하나를 말할 때 활성화:
- "bi-help", "어떤 도구를 써야 하나", "분석 방법 추천", "도구 선택"
```

- [ ] **Step 9: 8개 파일 존재 확인**

```bash
ls .gemini/antigravity/global_workflows/
```

예상 출력: `bi-ab.md  bi-analyze.md  bi-connect.md  bi-explore.md  bi-help.md  bi-history.md  bi-report.md  bi-solve.md  bi-stats.md  bi-viz.md`

- [ ] **Step 10: 커밋**

```bash
git add .gemini/antigravity/global_workflows/bi-connect.md \
        .gemini/antigravity/global_workflows/bi-explore.md \
        .gemini/antigravity/global_workflows/bi-analyze.md \
        .gemini/antigravity/global_workflows/bi-stats.md \
        .gemini/antigravity/global_workflows/bi-ab.md \
        .gemini/antigravity/global_workflows/bi-viz.md \
        .gemini/antigravity/global_workflows/bi-report.md \
        .gemini/antigravity/global_workflows/bi-help.md
git commit -m "feat: 기존 bi-* 스킬 Antigravity 어댑터 8개 소급 추가"
```

---

### Task 6: skills/bi-solve.md — G1 자동 추천 + G5 자동 저장 통합

**Files:**
- Modify: `skills/bi-solve.md`

현재 `skills/bi-solve.md`는 G1~G5를 정의한다. G1 완료 직후 자동 추천 블록을, G5 완료 직후 자동 저장 블록을 추가한다.

- [ ] **Step 1: G1 섹션 끝에 자동 추천 블록 추가**

`### [G1] 문제 분류` 섹션의 마지막 줄 ("예: ...") 바로 뒤에 다음 내용을 추가한다:

```markdown

**[G1 완료 후 — 유사 세션 자동 추천]**

유형이 확정되면 즉시 `get_similar_sessions()` 를 호출한다:
```
get_similar_sessions(type={확정된유형}, domain_tags={문제에서추출한핵심키워드})
```

- **결과 있으면:**
  ```
  참고할 과거 분석이 있습니다:
  {결과 목록}
  확인하시겠어요? (예/건너뛰기)
  ```
  - 예: 해당 세션 파일 경로를 안내하고 내용 요약
  - 건너뛰기: 조용히 G2 진행

- **결과 없으면:** 바로 G2 진행 (별도 안내 없음)
```

- [ ] **Step 2: G5 섹션 끝에 자동 저장 블록 추가**

`### [G5] 검증 완료` 섹션의 마지막 문단 ("**판단 불가** → ...") 바로 뒤에 다음 내용을 추가한다:

```markdown

**[G5 완료 후 — 히스토리 자동 저장]**

"확인" 또는 "기각" 선택 시 다음 순서로 실행한다:

1. **태그 추출** (LLM 1회 호출):
   세션 파일 내용을 바탕으로 다음을 JSON으로 추출한다:
   - `domain_tags`: 비즈니스 용어 최대 5개 (예: ["매출", "CAC", "신규가입"])
   - `free_tags`: 분석 특이사항 최대 3개 (예: ["채널별-분리", "계절성-제외"])

2. **DB 저장**:
   ```
   save_session(
       session_id=세션파일명_슬러그,  # 예: "2026-04-08-매출-하락"
       title=분석제목,
       type=확정된유형,              # G1에서 확정
       result="confirmed" | "rejected" | "inconclusive",
       domain_tags=[...],
       free_tags=[...],
       file_path="context/sessions/{세션파일명}.md",
       summary=결론_한_두_문장,
   )
   ```

3. **index.md 업데이트** (기존 방식 유지):
   `context/sessions/index.md` 테이블에 한 줄 추가
```

- [ ] **Step 3: 변경 내용 확인**

```bash
grep -n "G1 완료 후\|G5 완료 후" skills/bi-solve.md
```

예상 출력: G1 완료 후와 G5 완료 후 라인 번호가 각각 출력됨

- [ ] **Step 4: 커밋**

```bash
git add skills/bi-solve.md
git commit -m "feat: bi-solve G1 유사 세션 자동 추천 + G5 히스토리 자동 저장 통합"
```

---

### Task 7: AGENTS.md — /bi-history 항목 추가

**Files:**
- Modify: `AGENTS.md`

- [ ] **Step 1: AGENTS.md에 bi-history 섹션 추가**

현재 AGENTS.md의 `## MCP 도구 사용` 섹션 바로 앞에 다음 섹션을 추가한다:

```markdown
## /bi-history — 분석 히스토리 검색

과거 분석 세션을 검색하고 관리한다.

`skills/bi-history.md` 파일을 읽고 지침을 따른다.

### 사용 방법

| 명령 | 동작 |
|------|------|
| `bi-history` (인수 없음) | 최근 10개 세션 목록 |
| `bi-history "매출"` | 키워드로 세션 검색 |
| `bi-history --type diagnostic` | 진단형 세션만 조회 |
| `bi-history --result confirmed` | 가설 확인된 세션만 조회 |
| `bi-history "광고" --deep` | LLM 심층 검색 |

### 사용 MCP 도구

- `search_history(query, type, result, limit)` — 히스토리 검색 (LLM 없음)
- `tag_session(session_id, add_tags)` — 태그 추가

```

- [ ] **Step 2: 확인**

```bash
grep -n "bi-history" AGENTS.md
```

예상 출력: bi-history 관련 라인들이 출력됨

- [ ] **Step 3: 커밋**

```bash
git add AGENTS.md
git commit -m "docs: AGENTS.md에 /bi-history 항목 추가"
```

---

## 최종 검증

- [ ] **전체 테스트 재실행**

```bash
python3 -m pytest tests/unit/ -q --no-header 2>&1 | tail -5
```

예상: 기존 테스트 + 20개 신규 테스트 모두 통과

- [ ] **history 도구 등록 재확인**

```bash
python3 -c "
import os; os.environ['BI_AGENT_LOAD_ALL']='true'
from bi_agent_mcp.server import mcp
tools = list(mcp._tool_manager._tools.keys())
history_tools = [t for t in tools if t in ['save_session','get_similar_sessions','search_history','tag_session']]
print('History tools:', history_tools)
"
```

- [ ] **Antigravity 어댑터 파일 수 확인**

```bash
ls .gemini/antigravity/global_workflows/ | wc -l
```

예상 출력: `10` (bi-solve + bi-history + 8개 소급)
