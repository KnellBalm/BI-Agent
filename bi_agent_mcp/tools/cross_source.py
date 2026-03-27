"""bi-agent 크로스 소스 쿼리 도구 — DB와 파일 데이터를 DuckDB로 조인 쿼리."""
from typing import List

from bi_agent_mcp.tools.db import _connections, _get_conn, _validate_select
from bi_agent_mcp.tools.files import _files
from bi_agent_mcp.config import QUERY_LIMIT


def cross_query(sources: list, sql: str) -> str:
    """[CrossSource] 여러 데이터 소스(DB, 파일)를 DuckDB로 조인 쿼리합니다.

    Args:
        sources: 데이터 소스 목록. 각 항목 형식:
          - DB: {"type": "db", "conn_id": "pg1", "table": "orders", "alias": "orders"}
          - 파일: {"type": "file", "file_id": "excel1", "alias": "products"}
        sql: 실행할 SELECT SQL (alias 이름을 테이블명으로 사용)
    """
    # SELECT 검증
    err = _validate_select(sql)
    if err:
        return f"[ERROR] {err}"

    try:
        import duckdb
        import pandas as pd
    except ImportError as e:
        return f"[ERROR] 필수 패키지가 없습니다: {e}"

    duckdb_conn = duckdb.connect(":memory:")

    try:
        for source in sources:
            src_type = source.get("type")
            alias = source.get("alias")

            if not alias:
                return "[ERROR] 각 소스에 'alias' 필드가 필요합니다."

            if src_type == "db":
                conn_id = source.get("conn_id")
                table = source.get("table")
                if not conn_id:
                    return "[ERROR] DB 소스에 'conn_id' 필드가 필요합니다."
                if not table:
                    return "[ERROR] DB 소스에 'table' 필드가 필요합니다."

                info = _connections.get(conn_id)
                if info is None:
                    return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

                try:
                    conn = _get_conn(info)
                    df = pd.read_sql(f"SELECT * FROM {table}", conn)
                except Exception as e:
                    return f"[ERROR] DB 소스 '{conn_id}' 로드 실패: {e}"

                duckdb_conn.register(alias, df)

            elif src_type == "file":
                file_id = source.get("file_id")
                if not file_id:
                    return "[ERROR] 파일 소스에 'file_id' 필드가 필요합니다."

                file_info = _files.get(file_id)
                if file_info is None:
                    return f"[ERROR] 파일 ID '{file_id}'를 찾을 수 없습니다."

                df = file_info["df"]
                duckdb_conn.register(alias, df)

            else:
                return f"[ERROR] 지원하지 않는 소스 타입: {src_type}"

        # LIMIT 적용하여 실행
        safe_sql = f"SELECT * FROM ({sql}) AS _sub LIMIT {QUERY_LIMIT}"
        try:
            result_df = duckdb_conn.execute(safe_sql).df()
        except Exception as e:
            return f"[ERROR] 조인 쿼리 실패: {e}"

    finally:
        duckdb_conn.close()

    if result_df.empty:
        return "결과 없음"

    # 마크다운 테이블 생성
    cols = result_df.columns.tolist()
    header = "| " + " | ".join(cols) + " |"
    separator = "| " + " | ".join(["---"] * len(cols)) + " |"
    rows_md = []
    for _, row in result_df.iterrows():
        vals = [str(row[c]) for c in cols]
        rows_md.append("| " + " | ".join(vals) + " |")

    sql_preview = sql[:80] + ("..." if len(sql) > 80 else "")
    return (
        f"**{len(result_df)}건 반환** (SQL: `{sql_preview}`)\n\n"
        + header + "\n" + separator + "\n" + "\n".join(rows_md)
    )
