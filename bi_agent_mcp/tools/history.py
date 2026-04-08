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

    if query:
        q_lower = query.lower()
        rows = [
            row for row in rows
            if q_lower in " ".join([
                row["title"] or "",
                row["domain_tags"] or "",
                row["free_tags"] or "",
                row["summary"] or "",
            ]).lower()
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
        merged = list(dict.fromkeys(existing + add_tags))

        conn.execute(
            "UPDATE sessions SET domain_tags = ? WHERE id = ?",
            (json.dumps(merged, ensure_ascii=False), session_id),
        )
        conn.commit()
        return f"[OK] 태그 추가 완료: {session_id} → {merged}"
    finally:
        conn.close()
