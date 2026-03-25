"""bi-agent DB 도구 — connect_db, list_connections, get_schema, run_query, profile_table."""
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from psycopg2 import sql as pg_sql

from bi_agent_mcp.auth.credentials import mask_password
from bi_agent_mcp.config import QUERY_LIMIT, BQ_MAX_BYTES_BILLED

_CONN_FILE = Path("~/.config/bi-agent/connections.json").expanduser()

# ──────────────────────────────────────────────
# 쿼리 결과 캐시
# ──────────────────────────────────────────────

# {(conn_id, sql_hash): {"result": str, "expires": float, "hits": int}}
_query_cache: dict = {}
_CACHE_TTL = 300  # 5분
_cache_hits = 0
_cache_misses = 0

# ──────────────────────────────────────────────
# 연결 레지스트리
# ──────────────────────────────────────────────

@dataclass
class ConnectionInfo:
    conn_id: str
    db_type: str    # "postgresql" | "mysql" | "bigquery" | "snowflake"
    host: str
    port: int
    database: str
    user: str
    password: str   # 메모리에만 보관, 절대 로그 출력 금지
    project_id: str = ""
    dataset: str = ""
    account: str = ""
    warehouse: str = ""
    schema_: str = ""
    persisted: bool = False


_connections: Dict[str, ConnectionInfo] = {}


def _save_connections() -> None:
    """비밀번호를 제외한 연결 정보를 JSON 파일에 저장. 실패 시 조용히 무시."""
    try:
        _CONN_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        for cid, info in _connections.items():
            data[cid] = {
                "conn_id": info.conn_id,
                "db_type": info.db_type,
                "host": info.host,
                "port": info.port,
                "database": info.database,
                "user": info.user,
                "project_id": info.project_id,
                "dataset": info.dataset,
                "account": info.account,
                "warehouse": info.warehouse,
                "schema_": info.schema_,
            }
        _CONN_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    except Exception:
        pass


def _load_connections() -> None:
    """파일에서 연결 정보 복원 (password는 빈 문자열). 실패 시 조용히 무시."""
    try:
        if not _CONN_FILE.exists():
            return
        data = json.loads(_CONN_FILE.read_text())
        for cid, d in data.items():
            _connections[cid] = ConnectionInfo(
                conn_id=d["conn_id"],
                db_type=d["db_type"],
                host=d.get("host", ""),
                port=d.get("port", 0),
                database=d.get("database", ""),
                user=d.get("user", ""),
                password="",
                project_id=d.get("project_id", ""),
                dataset=d.get("dataset", ""),
                account=d.get("account", ""),
                warehouse=d.get("warehouse", ""),
                schema_=d.get("schema_", ""),
                persisted=True,
            )
    except Exception:
        pass


def get_connection(conn_id: str) -> Optional[ConnectionInfo]:
    """server.py 또는 다른 tool에서 연결 정보 조회용."""
    return _connections.get(conn_id)


# ──────────────────────────────────────────────
# 보안 검증
# ──────────────────────────────────────────────

BLOCKED_KEYWORDS = {"DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "TRUNCATE"}


def _validate_identifier(name: str) -> Optional[str]:
    """식별자(테이블명, 컬럼명) 정규식 검증. None=통과, str=거부 사유."""
    import re
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_$.]*$', name):
        return f"유효하지 않은 식별자: '{name}'. 영문자, 숫자, _, $, .만 허용됩니다."
    return None


def _validate_select(sql: str) -> Optional[str]:
    """None=통과, str=거부 사유."""
    upper = sql.strip().upper()
    if not upper.startswith("SELECT"):
        return "보안 위반: SELECT 쿼리만 실행할 수 있습니다."
    for kw in BLOCKED_KEYWORDS:
        if kw in upper:
            return f"보안 위반: {kw} 키워드는 허용되지 않습니다."
    return None


# ──────────────────────────────────────────────
# DB 연결 헬퍼
# ──────────────────────────────────────────────

def _make_pg_connection(info: ConnectionInfo):
    import psycopg2
    return psycopg2.connect(
        host=info.host,
        port=info.port,
        dbname=info.database,
        user=info.user,
        password=info.password,
    )


def _make_mysql_connection(info: ConnectionInfo):
    import pymysql
    return pymysql.connect(
        host=info.host,
        port=info.port,
        database=info.database,
        user=info.user,
        password=info.password,
        cursorclass=pymysql.cursors.DictCursor,
    )


def _make_bq_client(info: ConnectionInfo):
    from google.cloud import bigquery
    from bi_agent_mcp.config import BQ_CREDENTIALS_PATH
    if BQ_CREDENTIALS_PATH:
        from google.oauth2 import service_account
        credentials = service_account.Credentials.from_service_account_file(BQ_CREDENTIALS_PATH)
        return bigquery.Client(project=info.project_id, credentials=credentials)
    return bigquery.Client(project=info.project_id)


def _make_snowflake_connection(info: ConnectionInfo):
    import snowflake.connector
    return snowflake.connector.connect(
        account=info.account,
        user=info.user,
        password=info.password,
        warehouse=info.warehouse,
        database=info.database,
        schema=info.schema_ or "PUBLIC",
    )


def _get_conn(info: ConnectionInfo):
    if info.db_type == "postgresql":
        return _make_pg_connection(info)
    elif info.db_type == "mysql":
        return _make_mysql_connection(info)
    elif info.db_type == "bigquery":
        return _make_bq_client(info)
    elif info.db_type == "snowflake":
        return _make_snowflake_connection(info)
    else:
        raise ValueError(f"지원하지 않는 DB 타입: {info.db_type}")


# ──────────────────────────────────────────────
# 테이블명 검증 (SQL Injection 방어)
# ──────────────────────────────────────────────

def _validate_table_name(cur, table_name: str, db_type: str) -> Optional[str]:
    """
    테이블명이 실제 존재하는지 확인한다.
    존재하면 None, 없으면 에러 메시지 문자열 반환.
    SQL Injection 방어: 테이블명을 파라미터 바인딩으로 검증.
    """
    if db_type == "postgresql":
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s",
            (table_name,)
        )
    else:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name = %s",
            (table_name,)
        )
    if cur.fetchone() is None:
        if db_type == "postgresql":
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' ORDER BY table_name LIMIT 20"
            )
        else:
            cur.execute("SHOW TABLES")
        existing = [r[0] for r in cur.fetchall()]
        return f"테이블 '{table_name}'이 없습니다. 존재하는 테이블: {', '.join(existing)}"
    return None


# ──────────────────────────────────────────────
# 마크다운 테이블 헬퍼
# ──────────────────────────────────────────────

def _rows_to_markdown(columns: List[str], rows: list, total: int, sql_preview: str) -> str:
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    data_rows = []
    for row in rows:
        if isinstance(row, dict):
            vals = [str(row.get(c, "")) for c in columns]
        else:
            vals = [str(v) for v in row]
        data_rows.append("| " + " | ".join(vals) + " |")

    result = f"**{total}건 반환** (SQL: `{sql_preview}`)\n\n"
    result += header + "\n" + separator + "\n" + "\n".join(data_rows)
    displayed = len(rows)
    if total > displayed:
        result += f"\n\n(총 {total}건 중 {displayed}건 표시)"
    return result


# ──────────────────────────────────────────────
# MCP Tools
# ──────────────────────────────────────────────

def connect_db(
    db_type: str,
    host: str = "",
    port: int = 0,
    database: str = "",
    user: str = "",
    password: str = "",
    project_id: str = "",
    dataset: str = "",
    account: str = "",
    warehouse: str = "",
    schema_: str = "",
) -> str:
    """PostgreSQL, MySQL, BigQuery, 또는 Snowflake 데이터베이스에 연결하고 연결 ID를 반환합니다.

    Args:
        db_type: 데이터베이스 종류 ("postgresql", "mysql", "bigquery", 또는 "snowflake")
        host: 호스트 주소 (postgresql/mysql)
        port: 포트 번호 (postgresql/mysql)
        database: 데이터베이스 이름 (postgresql/mysql/snowflake)
        user: 사용자명 (postgresql/mysql/snowflake)
        password: 비밀번호 (postgresql/mysql/snowflake)
        project_id: GCP 프로젝트 ID (bigquery)
        dataset: BigQuery 데이터셋 이름 (bigquery)
        account: Snowflake 계정 식별자 (snowflake)
        warehouse: Snowflake 웨어하우스 이름 (snowflake)
        schema_: Snowflake 스키마 이름 (snowflake, 기본값: PUBLIC)
    """
    if db_type not in ("postgresql", "mysql", "bigquery", "snowflake"):
        return f"[ERROR] 지원하지 않는 DB 타입: {db_type}. 'postgresql', 'mysql', 'bigquery', 또는 'snowflake'를 사용하세요."

    from bi_agent_mcp.config import BQ_PROJECT_ID, BQ_DATASET

    conn_id = f"conn_{uuid.uuid4().hex[:8]}"
    info = ConnectionInfo(
        conn_id=conn_id,
        db_type=db_type,
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        project_id=project_id or BQ_PROJECT_ID,
        dataset=dataset or BQ_DATASET,
        account=account,
        warehouse=warehouse,
        schema_=schema_,
    )

    # 연결 테스트
    try:
        if db_type == "bigquery":
            client = _make_bq_client(info)
            list(client.query("SELECT 1").result())
        else:
            conn = _get_conn(info)
            conn.close()
    except Exception as e:
        return f"[ERROR] 연결 실패: {e}"

    _connections[conn_id] = info
    _save_connections()

    if db_type == "bigquery":
        return (
            f"연결 등록 완료: {conn_id}\n"
            f"  타입: {db_type}\n"
            f"  프로젝트: {info.project_id}\n"
            f"  데이터셋: {info.dataset}"
        )
    if db_type == "snowflake":
        return (
            f"연결 등록 완료: {conn_id}\n"
            f"  타입: {db_type}\n"
            f"  계정: {account}\n"
            f"  웨어하우스: {warehouse}\n"
            f"  데이터베이스: {database}\n"
            f"  사용자: {user}"
        )
    return (
        f"연결 등록 완료: {conn_id}\n"
        f"  타입: {db_type}\n"
        f"  호스트: {host}:{port}\n"
        f"  데이터베이스: {database}\n"
        f"  사용자: {user}"
    )


def list_connections() -> str:
    """현재 등록된 데이터베이스 연결 목록을 반환합니다."""
    if not _connections:
        return "등록된 연결이 없습니다. connect_db를 먼저 호출하세요."

    lines = ["등록된 연결 목록:\n"]
    lines.append("| conn_id | 타입 | 호스트 | 데이터베이스 | 사용자 | 비밀번호 | 상태 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for cid, info in _connections.items():
        status = "(저장됨)" if info.persisted else ""
        lines.append(
            f"| {cid} | {info.db_type} | {info.host}:{info.port} "
            f"| {info.database} | {info.user} | {mask_password(info.password)} | {status} |"
        )
    return "\n".join(lines)


def get_schema(conn_id: str, table_name: str = "") -> str:
    """데이터베이스 스키마를 조회합니다. table_name을 지정하면 해당 테이블의 컬럼과 샘플을 반환합니다.

    Args:
        conn_id: connect_db로 얻은 연결 ID
        table_name: 조회할 테이블명 (비우면 전체 테이블 목록 반환)
    """
    info = _connections.get(conn_id)
    if not info:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. list_connections로 확인하세요."

    if info.db_type == "bigquery":
        try:
            client = _make_bq_client(info)
            if not table_name:
                tables = list(client.list_tables(info.dataset))
                if not tables:
                    return f"데이터셋 '{info.dataset}'에 테이블이 없습니다."
                lines = [f"데이터셋 '{info.dataset}' 테이블 목록:\n"]
                for t in tables:
                    lines.append(f"- {t.table_id}")
                return "\n".join(lines)
            else:
                err = _validate_identifier(table_name)
                if err:
                    return f"[ERROR] {err}"
                full_table = f"{info.project_id}.{info.dataset}.{table_name}"
                bq_table = client.get_table(full_table)
                count_result = list(client.query(
                    f"SELECT COUNT(*) AS cnt FROM `{full_table}`"
                ).result())
                count = count_result[0].cnt if count_result else 0
                lines = [f"테이블 '{table_name}' ({count}행)\n"]
                lines.append("| 컬럼명 | 타입 | 모드 | 설명 |")
                lines.append("| --- | --- | --- | --- |")
                for f in bq_table.schema:
                    lines.append(
                        f"| {f.name} | {f.field_type} | {f.mode} | {f.description or ''} |"
                    )
                return "\n".join(lines)
        except Exception as e:
            return f"[ERROR] 스키마 조회 실패: {e}"

    try:
        conn = _get_conn(info)
    except Exception as e:
        return f"[ERROR] 연결 실패: {e}"

    try:
        cur = conn.cursor()

        if info.db_type == "postgresql":
            if not table_name:
                cur.execute("""
                    SELECT table_name, table_type
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)
                rows = cur.fetchall()
                if not rows:
                    return "스키마에 테이블이 없습니다."
                lines = [f"데이터베이스 '{info.database}' 테이블 목록:\n"]
                for r in rows:
                    lines.append(f"- {r[0]} ({r[1]})")
                return "\n".join(lines)
            else:
                # 테이블 존재 여부 검증 (SQL Injection 방어)
                err = _validate_table_name(cur, table_name, info.db_type)
                if err:
                    return f"[ERROR] {err}"

                # 컬럼 정보
                cur.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    ORDER BY ordinal_position
                """, (table_name,))
                cols = cur.fetchall()
                if not cols:
                    return f"[ERROR] 테이블 '{table_name}'을 찾을 수 없습니다."

                # 행 수 (pg_sql.Identifier로 안전하게 삽입)
                cur.execute(pg_sql.SQL("SELECT COUNT(*) FROM {}").format(pg_sql.Identifier(table_name)))
                count = cur.fetchone()[0]

                lines = [f"테이블 '{table_name}' ({count}행)\n"]
                lines.append("| 컬럼명 | 타입 | NULL허용 | 기본값 |")
                lines.append("| --- | --- | --- | --- |")
                for col in cols:
                    lines.append(f"| {col[0]} | {col[1]} | {col[2]} | {col[3] or ''} |")

                # 샘플 2행 (pg_sql.Identifier로 안전하게 삽입)
                cur.execute(pg_sql.SQL("SELECT * FROM {} LIMIT 2").format(pg_sql.Identifier(table_name)))
                samples = cur.fetchall()
                col_names = [c[0] for c in cols]
                if samples:
                    lines.append("\n샘플 데이터:")
                    for row in samples:
                        pairs = [f"{col_names[i]}={row[i]}" for i in range(len(col_names))]
                        lines.append("  " + " | ".join(pairs))
                return "\n".join(lines)

        elif info.db_type == "mysql":
            if not table_name:
                cur.execute("SHOW TABLES")
                rows = cur.fetchall()
                if not rows:
                    return "스키마에 테이블이 없습니다."
                lines = [f"데이터베이스 '{info.database}' 테이블 목록:\n"]
                for r in rows:
                    tname = list(r.values())[0] if isinstance(r, dict) else r[0]
                    lines.append(f"- {tname}")
                return "\n".join(lines)
            else:
                # 테이블 존재 여부 검증 (SQL Injection 방어)
                err = _validate_table_name(cur, table_name, info.db_type)
                if err:
                    return f"[ERROR] {err}"

                err = _validate_identifier(table_name)
                if err:
                    return f"[ERROR] {err}"
                cur.execute(f"DESCRIBE `{table_name}`")
                cols = cur.fetchall()
                if not cols:
                    return f"[ERROR] 테이블 '{table_name}'을 찾을 수 없습니다."

                err = _validate_identifier(table_name)
                if err:
                    return f"[ERROR] {err}"
                cur.execute(f"SELECT COUNT(*) AS cnt FROM `{table_name}`")
                count_row = cur.fetchone()
                count = count_row["cnt"] if isinstance(count_row, dict) else count_row[0]

                lines = [f"테이블 '{table_name}' ({count}행)\n"]
                lines.append("| 컬럼명 | 타입 | NULL허용 | 키 | 기본값 |")
                lines.append("| --- | --- | --- | --- | --- |")
                for col in cols:
                    if isinstance(col, dict):
                        lines.append(
                            f"| {col['Field']} | {col['Type']} | {col['Null']} "
                            f"| {col.get('Key','')} | {col.get('Default','')} |"
                        )
                    else:
                        lines.append(f"| {col[0]} | {col[1]} | {col[2]} | {col[3]} | {col[4]} |")

                err = _validate_identifier(table_name)
                if err:
                    return f"[ERROR] {err}"
                cur.execute(f"SELECT * FROM `{table_name}` LIMIT 2")
                samples = cur.fetchall()
                if samples:
                    lines.append("\n샘플 데이터:")
                    for row in samples:
                        if isinstance(row, dict):
                            pairs = [f"{k}={v}" for k, v in row.items()]
                        else:
                            pairs = [str(v) for v in row]
                        lines.append("  " + " | ".join(pairs))
                return "\n".join(lines)

        elif info.db_type == "snowflake":
            schema_name = info.schema_ or "PUBLIC"
            if not table_name:
                cur.execute(
                    "SELECT table_name, table_type FROM information_schema.tables "
                    "WHERE table_schema = %s ORDER BY table_name",
                    (schema_name.upper(),)
                )
                rows = cur.fetchall()
                if not rows:
                    return f"스키마 '{schema_name}'에 테이블이 없습니다."
                lines = [f"데이터베이스 '{info.database}' 스키마 '{schema_name}' 테이블 목록:\n"]
                for r in rows:
                    lines.append(f"- {r[0]} ({r[1]})")
                return "\n".join(lines)
            else:
                err = _validate_identifier(table_name)
                if err:
                    return f"[ERROR] {err}"
                cur.execute(
                    "SELECT column_name, data_type, is_nullable, column_default "
                    "FROM information_schema.columns "
                    "WHERE table_schema = %s AND table_name = %s "
                    "ORDER BY ordinal_position",
                    (schema_name.upper(), table_name.upper())
                )
                cols = cur.fetchall()
                if not cols:
                    return f"[ERROR] 테이블 '{table_name}'을 찾을 수 없습니다."
                cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                count = cur.fetchone()[0]
                lines = [f"테이블 '{table_name}' ({count}행)\n"]
                lines.append("| 컬럼명 | 타입 | NULL허용 | 기본값 |")
                lines.append("| --- | --- | --- | --- |")
                for col in cols:
                    lines.append(f"| {col[0]} | {col[1]} | {col[2]} | {col[3] or ''} |")
                cur.execute(f'SELECT * FROM "{table_name}" LIMIT 2')
                samples = cur.fetchall()
                col_names = [c[0] for c in cols]
                if samples:
                    lines.append("\n샘플 데이터:")
                    for row in samples:
                        pairs = [f"{col_names[i]}={row[i]}" for i in range(len(col_names))]
                        lines.append("  " + " | ".join(pairs))
                return "\n".join(lines)

        return "[ERROR] 지원하지 않는 DB 타입입니다."
    except Exception as e:
        return f"[ERROR] 스키마 조회 실패: {e}"
    finally:
        conn.close()


def run_query(conn_id: str, sql: str) -> str:
    """SELECT SQL 쿼리를 실행하고 결과를 마크다운 테이블로 반환합니다. SELECT만 허용됩니다.

    Args:
        conn_id: connect_db로 얻은 연결 ID
        sql: 실행할 SELECT SQL 쿼리
    """
    global _cache_hits, _cache_misses

    info = _connections.get(conn_id)
    if not info:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    # SQL 코드 블록 제거
    query = sql.strip()
    if "```" in query:
        lines = query.split("\n")
        query = "\n".join(l for l in lines if not l.startswith("```")).strip()

    error = _validate_select(query)
    if error:
        return f"[ERROR] {error}"

    # 캐시 확인 (SELECT 쿼리만)
    sql_stripped = query.upper()
    cache_key = (conn_id, hashlib.md5(query.encode()).hexdigest())
    if sql_stripped.startswith("SELECT"):
        if cache_key in _query_cache:
            entry = _query_cache[cache_key]
            if time.time() < entry["expires"]:
                _cache_hits += 1
                entry["hits"] += 1
                remaining = int(entry["expires"] - time.time())
                return entry["result"] + f"\n\n*캐시에서 반환됨 (TTL: {remaining}초 남음)*"
        _cache_misses += 1

    try:
        conn = _get_conn(info)
    except Exception as e:
        return f"[ERROR] 연결 실패: {e}"

    try:
        if info.db_type == "bigquery":
            from google.cloud.bigquery import QueryJobConfig
            client = _make_bq_client(info)
            job_config = QueryJobConfig(maximum_bytes_billed=BQ_MAX_BYTES_BILLED)
            safe_query = f"SELECT * FROM ({query}) AS _sub LIMIT {QUERY_LIMIT}"
            rows = list(client.query(safe_query, job_config=job_config).result())
            if not rows:
                return f"결과 없음 (SQL: `{query}`)"
            columns = list(rows[0].keys())
            rows_list = [dict(r) for r in rows]
            sql_preview = query[:80] + ("..." if len(query) > 80 else "")
            return _rows_to_markdown(columns, rows_list, len(rows_list), sql_preview)

        if info.db_type == "postgresql":
            import psycopg2.extras
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            safe_query = f"SELECT * FROM ({query}) AS _sub LIMIT {QUERY_LIMIT}"
            cur.execute(safe_query)
            rows = cur.fetchall()
            columns = list(rows[0].keys()) if rows else (
                [desc[0] for desc in cur.description] if cur.description else []
            )
            rows_list = [dict(r) for r in rows]
        elif info.db_type == "snowflake":
            cur = conn.cursor()
            safe_query = f"SELECT * FROM ({query}) LIMIT {QUERY_LIMIT}"
            cur.execute(safe_query)
            rows_list = cur.fetchall()
            columns = [desc[0] for desc in cur.description] if cur.description else []
        else:
            cur = conn.cursor()
            safe_query = f"SELECT * FROM ({query}) AS _sub LIMIT {QUERY_LIMIT}"
            cur.execute(safe_query)
            rows_list = cur.fetchall()
            columns = [desc[0] for desc in cur.description] if cur.description else []

        if not rows_list:
            return f"결과 없음 (SQL: `{query}`)"

        sql_preview = query[:80] + ("..." if len(query) > 80 else "")
        result = _rows_to_markdown(columns, rows_list, len(rows_list), sql_preview)

        # 쿼리 이력 저장 (순환 import 방지를 위해 직접 저장)
        try:
            import datetime
            _hist_file = Path("~/.config/bi-agent/query_history.json").expanduser()
            _hist_file.parent.mkdir(parents=True, exist_ok=True)
            try:
                history = json.loads(_hist_file.read_text(encoding="utf-8")) if _hist_file.exists() else []
            except Exception:
                history = []
            history.append({
                "timestamp": datetime.datetime.now().isoformat(),
                "conn_id": conn_id,
                "sql": query[:500],
                "row_count": len(rows_list) if isinstance(rows_list, list) else 0,
            })
            history = history[-100:]  # 최대 100개
            _hist_file.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

        # SELECT 쿼리 결과 캐시 저장
        if sql_stripped.startswith("SELECT"):
            _query_cache[cache_key] = {
                "result": result,
                "expires": time.time() + _CACHE_TTL,
                "hits": 0,
            }
        return result
    except Exception as e:
        return f"[ERROR] 쿼리 실행 실패: {e}"
    finally:
        if info.db_type != "bigquery":
            conn.close()


def profile_table(conn_id: str, table_name: str) -> str:
    """테이블의 컬럼별 NULL 비율, 유니크 값 수, min/max를 분석합니다.

    Args:
        conn_id: connect_db로 얻은 연결 ID
        table_name: 분석할 테이블명
    """
    info = _connections.get(conn_id)
    if not info:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    if info.db_type == "bigquery":
        try:
            client = _make_bq_client(info)
            err = _validate_identifier(table_name)
            if err:
                return f"[ERROR] {err}"
            full_table = f"{info.project_id}.{info.dataset}.{table_name}"
            cols_query = f"""
                SELECT column_name, data_type
                FROM `{info.project_id}.{info.dataset}.INFORMATION_SCHEMA.COLUMNS`
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
            """
            col_rows = list(client.query(cols_query).result())
            if not col_rows:
                return f"[ERROR] 테이블 '{table_name}'을 찾을 수 없습니다."

            total_result = list(client.query(
                f"SELECT COUNT(*) AS cnt FROM `{full_table}`"
            ).result())
            total = total_result[0].cnt if total_result else 0

            lines = [f"테이블 '{table_name}' 프로파일링 (전체 {total}행)\n"]
            lines.append("| 컬럼명 | 타입 | NULL수 | NULL% | 유니크수 | min | max |")
            lines.append("| --- | --- | --- | --- | --- | --- | --- |")

            for col_row in col_rows:
                col_name = col_row.column_name
                col_type = col_row.data_type
                stat_query = f"""
                    SELECT
                        COUNTIF(`{col_name}` IS NULL) AS null_count,
                        APPROX_COUNT_DISTINCT(`{col_name}`) AS unique_count,
                        CAST(MIN(`{col_name}`) AS STRING) AS min_val,
                        CAST(MAX(`{col_name}`) AS STRING) AS max_val
                    FROM `{full_table}`
                """
                stat_rows = list(client.query(stat_query).result())
                if stat_rows:
                    s = stat_rows[0]
                    null_count = s.null_count or 0
                    unique_count = s.unique_count or 0
                    min_val = s.min_val or ""
                    max_val = s.max_val or ""
                else:
                    null_count = unique_count = 0
                    min_val = max_val = ""
                null_pct = f"{null_count / total * 100:.1f}%" if total > 0 else "0%"
                lines.append(
                    f"| {col_name} | {col_type} | {null_count} | {null_pct} "
                    f"| {unique_count} | {min_val} | {max_val} |"
                )
            return "\n".join(lines)
        except Exception as e:
            return f"[ERROR] 프로파일링 실패: {e}"

    try:
        conn = _get_conn(info)
    except Exception as e:
        return f"[ERROR] 연결 실패: {e}"

    try:
        cur = conn.cursor()

        if info.db_type == "postgresql":
            # 테이블 존재 여부 검증 (SQL Injection 방어)
            err = _validate_table_name(cur, table_name, info.db_type)
            if err:
                return f"[ERROR] {err}"

            # 컬럼 목록
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))
            cols = cur.fetchall()
            if not cols:
                return f"[ERROR] 테이블 '{table_name}'을 찾을 수 없습니다."

            cur.execute(pg_sql.SQL("SELECT COUNT(*) FROM {}").format(pg_sql.Identifier(table_name)))
            total = cur.fetchone()[0]

            lines = [f"테이블 '{table_name}' 프로파일링 (전체 {total}행)\n"]
            lines.append("| 컬럼명 | 타입 | NULL수 | NULL% | 유니크수 | min | max |")
            lines.append("| --- | --- | --- | --- | --- | --- | --- |")

            for col_name, data_type in cols:
                cur.execute(pg_sql.SQL("""
                    SELECT
                        COUNT(*) - COUNT({col}) AS null_count,
                        COUNT(DISTINCT {col}) AS unique_count,
                        MIN({col}::text) AS min_val,
                        MAX({col}::text) AS max_val
                    FROM {tbl}
                """).format(
                    col=pg_sql.Identifier(col_name),
                    tbl=pg_sql.Identifier(table_name),
                ))
                stat = cur.fetchone()
                null_count = stat[0]
                unique_count = stat[1]
                min_val = stat[2] or ""
                max_val = stat[3] or ""
                null_pct = f"{null_count / total * 100:.1f}%" if total > 0 else "0%"
                lines.append(
                    f"| {col_name} | {data_type} | {null_count} | {null_pct} "
                    f"| {unique_count} | {min_val} | {max_val} |"
                )
            return "\n".join(lines)

        elif info.db_type == "mysql":
            # 테이블 존재 여부 검증 (SQL Injection 방어)
            err = _validate_table_name(cur, table_name, info.db_type)
            if err:
                return f"[ERROR] {err}"

            cur.execute(f"DESCRIBE `{table_name}`")
            cols = cur.fetchall()
            if not cols:
                return f"[ERROR] 테이블 '{table_name}'을 찾을 수 없습니다."

            cur.execute(f"SELECT COUNT(*) AS cnt FROM `{table_name}`")
            count_row = cur.fetchone()
            total = count_row["cnt"] if isinstance(count_row, dict) else count_row[0]

            lines = [f"테이블 '{table_name}' 프로파일링 (전체 {total}행)\n"]
            lines.append("| 컬럼명 | 타입 | NULL수 | NULL% | 유니크수 | min | max |")
            lines.append("| --- | --- | --- | --- | --- | --- | --- |")

            for col in cols:
                col_name = col["Field"] if isinstance(col, dict) else col[0]
                col_type = col["Type"] if isinstance(col, dict) else col[1]
                err = _validate_identifier(col_name)
                if err:
                    return f"[ERROR] {err}"
                cur.execute(f"""
                    SELECT
                        SUM(CASE WHEN `{col_name}` IS NULL THEN 1 ELSE 0 END) AS null_count,
                        COUNT(DISTINCT `{col_name}`) AS unique_count,
                        MIN(CAST(`{col_name}` AS CHAR)) AS min_val,
                        MAX(CAST(`{col_name}` AS CHAR)) AS max_val
                    FROM `{table_name}`
                """)
                stat = cur.fetchone()
                if isinstance(stat, dict):
                    null_count = stat["null_count"] or 0
                    unique_count = stat["unique_count"] or 0
                    min_val = stat["min_val"] or ""
                    max_val = stat["max_val"] or ""
                else:
                    null_count = stat[0] or 0
                    unique_count = stat[1] or 0
                    min_val = stat[2] or ""
                    max_val = stat[3] or ""
                null_pct = f"{null_count / total * 100:.1f}%" if total > 0 else "0%"
                lines.append(
                    f"| {col_name} | {col_type} | {null_count} | {null_pct} "
                    f"| {unique_count} | {min_val} | {max_val} |"
                )
            return "\n".join(lines)

        elif info.db_type == "snowflake":
            err = _validate_identifier(table_name)
            if err:
                return f"[ERROR] {err}"
            schema_name = info.schema_ or "PUBLIC"
            cur.execute(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position",
                (schema_name.upper(), table_name.upper())
            )
            cols = cur.fetchall()
            if not cols:
                return f"[ERROR] 테이블 '{table_name}'을 찾을 수 없습니다."
            cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            total = cur.fetchone()[0]
            lines = [f"테이블 '{table_name}' 프로파일링 (전체 {total}행)\n"]
            lines.append("| 컬럼명 | 타입 | NULL수 | NULL% | 유니크수 | min | max |")
            lines.append("| --- | --- | --- | --- | --- | --- | --- |")
            for col_name, col_type in cols:
                cur.execute(f"""
                    SELECT
                        SUM(CASE WHEN "{col_name}" IS NULL THEN 1 ELSE 0 END) AS null_count,
                        COUNT(DISTINCT "{col_name}") AS unique_count,
                        MIN(CAST("{col_name}" AS VARCHAR)) AS min_val,
                        MAX(CAST("{col_name}" AS VARCHAR)) AS max_val
                    FROM "{table_name}"
                """)
                stat = cur.fetchone()
                null_count = stat[0] or 0
                unique_count = stat[1] or 0
                min_val = stat[2] or ""
                max_val = stat[3] or ""
                null_pct = f"{null_count / total * 100:.1f}%" if total > 0 else "0%"
                lines.append(
                    f"| {col_name} | {col_type} | {null_count} | {null_pct} "
                    f"| {unique_count} | {min_val} | {max_val} |"
                )
            return "\n".join(lines)

        return "[ERROR] 지원하지 않는 DB 타입입니다."
    except Exception as e:
        return f"[ERROR] 프로파일링 실패: {e}"
    finally:
        conn.close()


def clear_cache(conn_id: str = "") -> str:
    """쿼리 결과 캐시를 무효화합니다.

    Args:
        conn_id: 특정 연결의 캐시만 삭제. 비워두면 전체 삭제.
    """
    global _query_cache, _cache_hits, _cache_misses

    if conn_id:
        before = len(_query_cache)
        _query_cache = {k: v for k, v in _query_cache.items() if k[0] != conn_id}
        deleted = before - len(_query_cache)
        total = len(_query_cache)
    else:
        deleted = len(_query_cache)
        _query_cache = {}
        total = 0

    total_requests = _cache_hits + _cache_misses
    hit_rate = f"{_cache_hits / total_requests * 100:.1f}%" if total_requests > 0 else "N/A"

    return (
        f"{deleted}개 캐시 항목이 삭제되었습니다.\n"
        f"남은 캐시: {total}개\n"
        f"캐시 히트율: {hit_rate} ({_cache_hits} 히트 / {total_requests} 요청)"
    )


# 모듈 로드 시 저장된 연결 복원
_load_connections()
