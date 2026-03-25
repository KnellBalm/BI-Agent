"""bi-agent 컨텍스트 도구 — get_context_for_question, get_table_relationships."""
from __future__ import annotations

from bi_agent_mcp.tools.db import _connections, _get_conn


# ──────────────────────────────────────────────
# 내부 헬퍼
# ──────────────────────────────────────────────

def _list_tables(info) -> list[str]:
    """DB 타입별 테이블 목록 반환."""
    db_type = info.db_type

    if db_type == "sqlite":
        import sqlite3
        conn = sqlite3.connect(info.database)
        try:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            return [row[0] for row in cur.fetchall()]
        finally:
            conn.close()

    elif db_type == "postgresql":
        conn = _get_conn(info)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            )
            return [row[0] for row in cur.fetchall()]
        finally:
            conn.close()

    elif db_type == "mysql":
        conn = _get_conn(info)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = DATABASE()"
            )
            return [row["table_name"] if isinstance(row, dict) else row[0] for row in cur.fetchall()]
        finally:
            conn.close()

    elif db_type == "bigquery":
        client = _get_conn(info)
        tables = client.list_tables(info.dataset)
        return [t.table_id for t in tables]

    elif db_type == "snowflake":
        conn = _get_conn(info)
        try:
            cur = conn.cursor()
            cur.execute("SHOW TABLES")
            return [row[1] for row in cur.fetchall()]
        finally:
            conn.close()

    return []


def _get_table_schema_and_sample(info, table_name: str) -> tuple[list[tuple[str, str]], list[list]]:
    """(columns, sample_rows) 반환. columns = [(name, type), ...]"""
    db_type = info.db_type

    if db_type == "sqlite":
        import sqlite3
        conn = sqlite3.connect(info.database)
        try:
            cur = conn.cursor()
            cur.execute(f"PRAGMA table_info({table_name})")
            columns = [(row[1], row[2]) for row in cur.fetchall()]
            cur.execute(f"SELECT * FROM {table_name} LIMIT 3")
            rows = [list(r) for r in cur.fetchall()]
            return columns, rows
        finally:
            conn.close()

    elif db_type == "postgresql":
        conn = _get_conn(info)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = %s ORDER BY ordinal_position",
                (table_name,)
            )
            columns = [(row[0], row[1]) for row in cur.fetchall()]
            from psycopg2 import sql as pg_sql
            cur.execute(pg_sql.SQL("SELECT * FROM {} LIMIT 3").format(pg_sql.Identifier(table_name)))
            rows = [list(r) for r in cur.fetchall()]
            return columns, rows
        finally:
            conn.close()

    elif db_type == "mysql":
        conn = _get_conn(info)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_schema = DATABASE() AND table_name = %s ORDER BY ordinal_position",
                (table_name,)
            )
            raw_cols = cur.fetchall()
            columns = [
                (r["column_name"] if isinstance(r, dict) else r[0],
                 r["data_type"] if isinstance(r, dict) else r[1])
                for r in raw_cols
            ]
            cur.execute(f"SELECT * FROM `{table_name}` LIMIT 3")
            raw_rows = cur.fetchall()
            rows = [list(r.values()) if isinstance(r, dict) else list(r) for r in raw_rows]
            return columns, rows
        finally:
            conn.close()

    elif db_type == "bigquery":
        client = _get_conn(info)
        table_ref = f"{info.project_id}.{info.dataset}.{table_name}"
        bq_table = client.get_table(table_ref)
        columns = [(f.name, f.field_type) for f in bq_table.schema]
        query = f"SELECT * FROM `{table_ref}` LIMIT 3"
        rows = [list(row.values()) for row in client.query(query).result()]
        return columns, rows

    elif db_type == "snowflake":
        conn = _get_conn(info)
        try:
            cur = conn.cursor()
            cur.execute(f"DESCRIBE TABLE {table_name}")
            columns = [(row[0], row[1]) for row in cur.fetchall()]
            cur.execute(f"SELECT * FROM {table_name} LIMIT 3")
            rows = [list(r) for r in cur.fetchall()]
            return columns, rows
        finally:
            conn.close()

    return [], []


def _match_tables(tables: list[str], question: str) -> list[tuple[str, str]]:
    """질문 단어와 테이블명 부분 매칭. [(table_name, matched_word), ...]"""
    words = question.replace(",", " ").replace(".", " ").split()
    matched: list[tuple[str, str]] = []
    seen: set[str] = set()
    for word in words:
        word_lower = word.lower()
        if len(word_lower) < 2:
            continue
        for table in tables:
            table_lower = table.lower()
            if table in seen:
                continue
            if word_lower in table_lower or table_lower in word_lower:
                matched.append((table, word))
                seen.add(table)
    # 매칭 없으면 전체 반환 (최대 5개)
    if not matched:
        return [(t, "") for t in tables[:5]]
    return matched[:5]


def _render_markdown(question: str, table_data: list[tuple[str, str, list[tuple[str, str]], list[list]]]) -> str:
    """(table_name, matched_word, columns, sample_rows) 목록을 Markdown으로 렌더링."""
    lines: list[str] = [f'## 질문 컨텍스트: "{question}"', "", "### 관련 테이블", ""]
    for table_name, matched_word, columns, sample_rows in table_data:
        match_note = f" (매칭: '{matched_word}')" if matched_word else ""
        lines.append(f"#### {table_name}{match_note}")
        lines.append("| 컬럼 | 타입 |")
        lines.append("|------|------|")
        for col_name, col_type in columns:
            lines.append(f"| {col_name} | {col_type} |")
        lines.append("")
        if sample_rows and columns:
            col_names = [c[0] for c in columns]
            lines.append("샘플 데이터:")
            lines.append("| " + " | ".join(col_names) + " |")
            lines.append("| " + " | ".join(["---"] * len(col_names)) + " |")
            for row in sample_rows:
                lines.append("| " + " | ".join(str(v) for v in row) + " |")
            lines.append("")
    return "\n".join(lines)


# ──────────────────────────────────────────────
# Public Tools
# ──────────────────────────────────────────────

def get_context_for_question(conn_id: str, question: str) -> str:
    """자연어 질문에 관련된 테이블/컬럼 컨텍스트를 Markdown으로 반환합니다.

    Args:
        conn_id: connect_db로 등록한 연결 ID
        question: 자연어 질문 (예: "사용자별 주문 수를 알려줘")
    """
    info = _connections.get(conn_id)
    if info is None:
        return f"[ERROR] 연결을 찾을 수 없습니다: {conn_id}"

    try:
        tables = _list_tables(info)
    except Exception as e:
        return f"[ERROR] 테이블 목록 조회 실패: {e}"

    if not tables:
        return f"[ERROR] 연결 '{conn_id}'에서 테이블을 찾을 수 없습니다."

    matched = _match_tables(tables, question)

    table_data = []
    for table_name, matched_word in matched:
        try:
            columns, sample_rows = _get_table_schema_and_sample(info, table_name)
            table_data.append((table_name, matched_word, columns, sample_rows))
        except Exception as e:
            table_data.append((table_name, matched_word, [("(오류)", str(e))], []))

    return _render_markdown(question, table_data)


def get_table_relationships(conn_id: str) -> str:
    """DB의 외래 키 관계를 Mermaid ERD 형식으로 반환합니다.

    Args:
        conn_id: connect_db로 등록한 연결 ID
    """
    info = _connections.get(conn_id)
    if info is None:
        return f"[ERROR] 연결을 찾을 수 없습니다: {conn_id}"

    db_type = info.db_type

    if db_type == "bigquery":
        return "BigQuery는 FK 제약을 지원하지 않습니다. 도메인 컨텍스트를 load_domain_context로 설정하세요."

    try:
        relations: list[tuple[str, str, str, str]] = []  # (from_table, from_col, to_table, to_col)

        if db_type == "sqlite":
            import sqlite3
            conn = sqlite3.connect(info.database)
            try:
                cur = conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cur.fetchall()]
                for table in tables:
                    cur.execute(f"PRAGMA foreign_key_list({table})")
                    for row in cur.fetchall():
                        # row: (id, seq, table, from, to, ...)
                        relations.append((table, row[3], row[2], row[4]))
            finally:
                conn.close()

        elif db_type == "postgresql":
            conn = _get_conn(info)
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT kcu.table_name, kcu.column_name,
                           ccu.table_name AS foreign_table_name,
                           ccu.column_name AS foreign_column_name
                    FROM information_schema.key_column_usage kcu
                    JOIN information_schema.referential_constraints rc
                        ON kcu.constraint_name = rc.constraint_name
                    JOIN information_schema.key_column_usage ccu
                        ON rc.unique_constraint_name = ccu.constraint_name
                    """
                )
                relations = [(row[0], row[1], row[2], row[3]) for row in cur.fetchall()]
            finally:
                conn.close()

        elif db_type == "mysql":
            conn = _get_conn(info)
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT TABLE_NAME, COLUMN_NAME,
                           REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
                    FROM information_schema.KEY_COLUMN_USAGE
                    WHERE REFERENCED_TABLE_NAME IS NOT NULL
                      AND TABLE_SCHEMA = DATABASE()
                    """
                )
                raw = cur.fetchall()
                relations = [
                    (
                        r["TABLE_NAME"] if isinstance(r, dict) else r[0],
                        r["COLUMN_NAME"] if isinstance(r, dict) else r[1],
                        r["REFERENCED_TABLE_NAME"] if isinstance(r, dict) else r[2],
                        r["REFERENCED_COLUMN_NAME"] if isinstance(r, dict) else r[3],
                    )
                    for r in raw
                ]
            finally:
                conn.close()

        elif db_type == "snowflake":
            conn = _get_conn(info)
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT fk.FK_NAME,
                           fk.FK_TABLE_NAME, fk.FK_COLUMN_NAME,
                           fk.PK_TABLE_NAME, fk.PK_COLUMN_NAME
                    FROM (
                        SELECT
                            c.CONSTRAINT_NAME AS FK_NAME,
                            kcu.TABLE_NAME AS FK_TABLE_NAME,
                            kcu.COLUMN_NAME AS FK_COLUMN_NAME,
                            ccu.TABLE_NAME AS PK_TABLE_NAME,
                            ccu.COLUMN_NAME AS PK_COLUMN_NAME
                        FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS c
                        JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
                            ON c.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                        JOIN INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
                            ON c.CONSTRAINT_NAME = rc.CONSTRAINT_NAME
                        JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE ccu
                            ON rc.UNIQUE_CONSTRAINT_NAME = ccu.CONSTRAINT_NAME
                        WHERE c.CONSTRAINT_TYPE = 'FOREIGN KEY'
                    ) fk
                    """
                )
                relations = [(row[1], row[2], row[3], row[4]) for row in cur.fetchall()]
            finally:
                conn.close()

        if not relations:
            return "이 데이터베이스에는 외래 키 관계가 없습니다."

        # Mermaid ERD 생성
        lines = ["erDiagram"]
        seen_rels: set[tuple[str, str]] = set()
        for from_table, _from_col, to_table, _to_col in relations:
            key = (to_table, from_table)
            if key not in seen_rels:
                lines.append(f'    {to_table} ||--o{{ {from_table} : "has"')
                seen_rels.add(key)
        return "\n".join(lines)

    except Exception as e:
        return f"[ERROR] 관계 조회 실패: {e}"
