"""bi-agent 데이터 품질 검증 도구 — validate_data, validate_query_result."""
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from bi_agent_mcp.config import QUERY_LIMIT
from bi_agent_mcp.tools.db import _connections, _get_conn


def _fetch_rows(conn_id: str, sql: str) -> tuple[Optional[str], Optional[List[str]], Optional[List[tuple]]]:
    """주어진 SQL을 실행해 (error, columns, rows) 반환."""
    if conn_id not in _connections:
        return f"연결을 찾을 수 없습니다: {conn_id}", None, None

    info = _connections[conn_id]
    try:
        conn = _get_conn(info)
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()
        return None, columns, rows
    except Exception as e:
        return str(e), None, None


def _apply_rules(columns: List[str], rows: List[tuple], rules: List[Dict[str, Any]]) -> str:
    """규칙 목록을 적용하고 Markdown 결과 문자열 반환."""
    col_index = {c: i for i, c in enumerate(columns)}
    total = len(rows)

    result_rows = []
    pass_count = 0

    for rule in rules:
        col = rule.get("column", "")
        check = rule.get("check", "")
        note = ""

        if col not in col_index:
            result_rows.append((col, check, "⚠️ SKIP", "-", f"컬럼 없음: {col}"))
            continue

        idx = col_index[col]
        values = [r[idx] for r in rows]

        violations = []

        if check == "not_null":
            violations = [v for v in values if v is None]
            rule_label = "not_null"

        elif check == "range":
            min_val = rule.get("min")
            max_val = rule.get("max")
            rule_label = f"range({min_val}-{max_val})"
            for v in values:
                if v is None:
                    continue
                try:
                    fv = float(v)
                    if (min_val is not None and fv < min_val) or (max_val is not None and fv > max_val):
                        violations.append(v)
                except (TypeError, ValueError):
                    violations.append(v)

        elif check == "regex":
            pattern = rule.get("pattern", "")
            rule_label = f"regex({pattern})"
            compiled = re.compile(pattern)
            for v in values:
                if v is None:
                    violations.append(v)
                elif not compiled.match(str(v)):
                    violations.append(v)

        elif check == "enum":
            allowed = set(rule.get("values", []))
            rule_label = f"enum({', '.join(str(x) for x in allowed)})"
            for v in values:
                if v not in allowed:
                    violations.append(v)

        elif check == "freshness":
            max_age_hours = rule.get("max_age_hours", 24)
            rule_label = f"freshness(<{max_age_hours}h)"
            cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
            for v in values:
                if v is None:
                    violations.append(v)
                    continue
                try:
                    if isinstance(v, datetime):
                        ts = v if v.tzinfo else v.replace(tzinfo=timezone.utc)
                    else:
                        ts = datetime.fromisoformat(str(v))
                        if ts.tzinfo is None:
                            ts = ts.replace(tzinfo=timezone.utc)
                    if ts < cutoff:
                        violations.append(v)
                except (ValueError, TypeError):
                    violations.append(v)

        elif check == "unique":
            rule_label = "unique"
            seen = set()
            for v in values:
                sv = str(v) if v is not None else None
                if sv in seen:
                    violations.append(v)
                else:
                    seen.add(sv)

        else:
            result_rows.append((col, check, "⚠️ SKIP", "-", f"알 수 없는 규칙: {check}"))
            continue

        vcount = len(violations)
        if vcount == 0:
            status = "✅ PASS"
            pass_count += 1
        else:
            status = "❌ FAIL"
            samples = [str(x) for x in violations[:3]]
            note = "샘플: " + ", ".join(samples)

        result_rows.append((col, rule_label, status, f"{vcount}/{total}", note))

    # 테이블 렌더링
    lines = [
        "| 컬럼 | 규칙 | 결과 | 위반 수 | 비고 |",
        "|------|------|------|---------|------|",
    ]
    for r in result_rows:
        lines.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} |")

    valid_rules = len([r for r in result_rows if "SKIP" not in r[2]])
    lines.append("")
    lines.append(f"**전체: {pass_count}/{valid_rules} 규칙 통과**")
    return "\n".join(lines)


def validate_data(conn_id: str, table_name: str, rules: list) -> str:
    """[Quality]테이블 전체 데이터에 품질 규칙을 적용하고 결과를 반환합니다.

    Args:
        conn_id: 연결 ID (connect_db로 등록된 ID)
        table_name: 검증할 테이블 이름
        rules: 검증 규칙 목록. 각 규칙은 dict:
            {"column": "age", "check": "not_null"}
            {"column": "age", "check": "range", "min": 0, "max": 150}
            {"column": "email", "check": "regex", "pattern": ".*@.*"}
            {"column": "status", "check": "enum", "values": ["a", "b"]}
            {"column": "created_at", "check": "freshness", "max_age_hours": 24}
            {"column": "id", "check": "unique"}
    """
    if conn_id not in _connections:
        return f"[ERROR] 연결을 찾을 수 없습니다 — {conn_id}"

    # SQL Injection 방어: 테이블명을 알파벳/숫자/_로만 허용
    if not re.match(r'^[A-Za-z0-9_.]+$', table_name):
        return f"[ERROR] 유효하지 않은 테이블명 — {table_name}"

    sql = f"SELECT * FROM {table_name} LIMIT {QUERY_LIMIT}"
    error, columns, rows = _fetch_rows(conn_id, sql)
    if error:
        return f"[ERROR] {error}"

    header = f"## 데이터 품질 검증 결과: {table_name} 테이블\n\n"
    return header + _apply_rules(columns, rows, rules)


def validate_query_result(conn_id: str, sql: str, rules: list) -> str:
    """[Quality]SQL 실행 결과에 품질 규칙을 적용하고 결과를 반환합니다.

    Args:
        conn_id: 연결 ID (connect_db로 등록된 ID)
        sql: 실행할 SELECT SQL 쿼리
        rules: 검증 규칙 목록 (validate_data와 동일한 형식)
    """
    if conn_id not in _connections:
        return f"[ERROR] 연결을 찾을 수 없습니다 — {conn_id}"

    error, columns, rows = _fetch_rows(conn_id, sql)
    if error:
        return f"[ERROR] {error}"

    header = "## 데이터 품질 검증 결과: 쿼리 결과\n\n"
    return header + _apply_rules(columns, rows, rules)
