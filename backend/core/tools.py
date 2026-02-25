"""
BI-Agent 핵심 도구 (Tools) 모듈.

LLM이 자율적으로 호출할 수 있는 최소한의 뾰족한 도구만 제공한다.
모든 도구는 순수 함수로 구현되며, 문자열을 반환한다.
"""
import inspect
import json
import os
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional


# ──────────────────────────────────────────────
# Tool Registry
# ──────────────────────────────────────────────

class ToolRegistry:
    """도구 레지스트리. 도구 등록, 프롬프트 생성, 실행을 담당한다."""

    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, func, params: Dict[str, str] = None):
        """도구를 등록한다. description은 함수의 docstring에서 자동 추출."""
        self._tools[name] = {
            "func": func,
            "description": (func.__doc__ or "").strip(),
            "params": params or {},
        }

    def get_tools_prompt(self) -> str:
        """LLM에 주입할 도구 설명 프롬프트를 생성한다."""
        lines = []
        for name, info in self._tools.items():
            sig = ", ".join(f"{k}: {v}" for k, v in info["params"].items())
            lines.append(f"- **{name}**({sig}): {info['description']}")
        return "\n".join(lines)

    def execute(self, tool_name: str, arguments: Dict[str, Any], context: Dict[str, Any] = None) -> str:
        """도구를 실행하고 결과 문자열을 반환한다."""
        if tool_name not in self._tools:
            return f"[ERROR] 알 수 없는 도구: {tool_name}"
        try:
            func = self._tools[tool_name]["func"]
            sig = inspect.signature(func)
            call_args = arguments.copy()
            if "context" in sig.parameters:
                call_args["context"] = context
            return func(**call_args)
        except Exception as e:
            return f"[ERROR] {tool_name} 실행 오류: {e}"

    @property
    def tool_names(self) -> List[str]:
        return list(self._tools.keys())


# ──────────────────────────────────────────────
# DB 연결 유틸리티
# ──────────────────────────────────────────────

def _get_connection_info(conn_id: Optional[str] = None) -> Optional[dict]:
    """connections.json에서 연결 정보를 가져온다."""
    try:
        from backend.utils.path_config import path_manager
        registry_path = path_manager.get_project_path("default") / "connections.json"
        if not registry_path.exists():
            return None
        with open(registry_path, encoding="utf-8") as f:
            reg = json.load(f)
        if not reg:
            return None
        if conn_id and conn_id in reg:
            return reg[conn_id]
        # 첫 번째 연결 반환
        first_key = next(iter(reg))
        return reg[first_key]
    except Exception:
        return None


def _get_db_path(conn_info: dict) -> Optional[str]:
    """연결 정보에서 SQLite DB 경로를 추출한다."""
    if not conn_info:
        return None
    return conn_info.get("config", {}).get("path")


# ──────────────────────────────────────────────
# 핵심 도구 구현
# ──────────────────────────────────────────────

def list_connections() -> str:
    """현재 등록된 데이터베이스 연결 목록을 조회합니다."""
    try:
        from backend.utils.path_config import path_manager
        registry_path = path_manager.get_project_path("default") / "connections.json"
        if not registry_path.exists():
            return "등록된 연결이 없습니다. /connect 로 먼저 DB를 연결하세요."
        with open(registry_path, encoding="utf-8") as f:
            reg = json.load(f)
        if not reg:
            return "등록된 연결이 없습니다."
        lines = ["등록된 연결 목록:"]
        for cid, info in reg.items():
            lines.append(f"- {cid}: {info.get('name', cid)} ({info.get('type', '?')})")
        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] 연결 목록 조회 실패: {e}"


def analyze_schema(table_name: str = "", context: Dict[str, Any] = None) -> str:
    """데이터베이스 테이블 구조(컬럼, 타입, 행수, 샘플)를 분석합니다. table_name이 비면 전체 테이블 목록을 보여줍니다."""
    conn_info = _get_connection_info()
    if not conn_info:
        return "❌ 활성화된 DB 연결이 없습니다."
    if conn_info.get("type") != "sqlite":
        return f"❌ 현재 SQLite만 지원합니다. (현재: {conn_info.get('type')})"

    db_path = _get_db_path(conn_info)
    if not db_path or not os.path.exists(db_path):
        return f"❌ DB 파일을 찾을 수 없습니다: {db_path}"

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        tables = [t[0] for t in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

        if table_name and table_name not in tables:
            conn.close()
            return f"테이블 '{table_name}'이 없습니다. 존재하는 테이블: {', '.join(tables)}"

        targets = [table_name] if table_name else tables
        result = f"[스키마 분석] DB: {os.path.basename(db_path)}\n"

        for tbl in targets:
            cols = cur.execute(f'PRAGMA table_info("{tbl}")').fetchall()
            count = cur.execute(f'SELECT COUNT(*) FROM "{tbl}"').fetchone()[0]
            result += f"\n📊 {tbl} ({count}행)\n"
            for c in cols:
                col_name, col_type, notnull, _, pk = c[1], c[2], c[3], c[4], c[5]
                flags = []
                if pk: flags.append("PK")
                if notnull: flags.append("NOT NULL")
                flag_str = f" [{', '.join(flags)}]" if flags else ""
                result += f"  - {col_name}: {col_type}{flag_str}\n"

            # 샘플 2행
            samples = cur.execute(f'SELECT * FROM "{tbl}" LIMIT 2').fetchall()
            if samples:
                col_names = [c[1] for c in cols]
                result += "  샘플:\n"
                for row in samples:
                    vals = [f"{col_names[i]}={row[i]}" for i in range(len(col_names))]
                    result += f"    {' | '.join(vals)}\n"

        conn.close()
        return result
    except Exception as e:
        return f"[ERROR] 스키마 분석 오류: {e}"


def query_database(sql_query: str = "", context: Dict[str, Any] = None) -> str:
    """SQL SELECT 쿼리를 실행하고 결과를 마크다운 테이블로 반환합니다. SELECT만 허용."""
    conn_info = _get_connection_info()
    if not conn_info:
        return "❌ 활성화된 DB 연결이 없습니다."
    if conn_info.get("type") != "sqlite":
        return f"❌ 현재 SQLite만 지원합니다."

    db_path = _get_db_path(conn_info)
    if not db_path or not os.path.exists(db_path):
        return f"❌ DB 파일을 찾을 수 없습니다: {db_path}"

    query = sql_query.strip()
    # SQL 코드 블록 제거
    if "```" in query:
        lines = query.split("\n")
        query = "\n".join([l for l in lines if not l.startswith("```")])

    if not query.upper().startswith("SELECT"):
        return "❌ SELECT 쿼리만 허용됩니다."
    dangerous = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE"]
    if any(kw in query.upper() for kw in dangerous):
        return "⚠️ 읽기 전용 모드입니다. SELECT만 허용됩니다."

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description] if cur.description else []
        conn.close()

        if not rows:
            return f"결과 없음 (SQL: `{query}`)"

        # 마크다운 테이블 생성
        header = "| " + " | ".join(columns) + " |"
        separator = "| " + " | ".join(["---"] * len(columns)) + " |"
        data_rows = []
        for row in rows[:50]:  # 최대 50행
            vals = [str(row[i]) for i in range(len(columns))]
            data_rows.append("| " + " | ".join(vals) + " |")

        result = f"**{len(rows)}건 반환** (SQL: `{query}`)\n\n"
        result += header + "\n" + separator + "\n" + "\n".join(data_rows)
        if len(rows) > 50:
            result += f"\n\n... (총 {len(rows)}건 중 50건 표시)"
        return result
    except Exception as e:
        return f"[ERROR] 쿼리 실행 오류: {e}"


def write_markdown(file_path: str = "", content: str = "") -> str:
    """분석 결과를 마크다운 파일로 저장합니다. 기존 파일이 있으면 덮어씁니다."""
    if not file_path:
        return "❌ file_path를 지정하세요."
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"✅ 파일 저장 완료: {path.resolve()}"
    except Exception as e:
        return f"[ERROR] 파일 저장 실패: {e}"


# ──────────────────────────────────────────────
# 기본 레지스트리 빌더
# ──────────────────────────────────────────────

def build_default_registry() -> ToolRegistry:
    """핵심 도구 4개만 등록한 기본 레지스트리를 반환한다."""
    registry = ToolRegistry()

    registry.register("list_connections", list_connections)
    registry.register("analyze_schema", analyze_schema,
                       {"table_name": "분석할 테이블명 (비우면 전체 목록)"})
    registry.register("query_database", query_database,
                       {"sql_query": "실행할 SQL SELECT 쿼리"})
    registry.register("write_markdown", write_markdown,
                       {"file_path": "저장할 파일 경로", "content": "마크다운 내용"})
    return registry
