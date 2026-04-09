"""[Redshift] AWS IAM 임시 자격증명 기반 Redshift 연동 도구."""
import logging
from typing import Dict

import boto3
import psycopg2

from bi_agent_mcp.tools.db import _validate_select

logger = logging.getLogger(__name__)

_redshift_connections: Dict[str, dict] = {}


def _get_redshift_conn(conn_id: str):
    """IAM 임시 자격증명으로 psycopg2 연결 생성."""
    if conn_id not in _redshift_connections:
        raise ValueError(f"연결 ID '{conn_id}'를 찾을 수 없습니다. connect_redshift()를 먼저 호출하세요.")
    info = _redshift_connections[conn_id]

    client = boto3.client("redshift", region_name=info["region"])
    creds = client.get_cluster_credentials(
        DbUser=info["user"],
        DbName=info["database"],
        ClusterIdentifier=info["cluster_id"],
        DurationSeconds=3600,
        AutoCreate=False,
    )

    host = f"{info['cluster_id']}.{info['region']}.redshift.amazonaws.com"
    return psycopg2.connect(
        host=host,
        port=5439,
        database=info["database"],
        user=creds["DbUser"],
        password=creds["DbPassword"],
    )


def connect_redshift(
    cluster_id: str,
    database: str,
    user: str,
    region: str = "ap-northeast-2",
    conn_id: str = "default",
) -> str:
    """[Redshift] AWS IAM 임시 자격증명으로 Redshift에 연결한다.

    Args:
        cluster_id: Redshift 클러스터 ID (예: "my-cluster", 전체 엔드포인트 아님)
        database: 데이터베이스 이름
        user: IAM 사용자명 (boto3 자격증명 환경 필요)
        region: AWS 리전 (기본값: "ap-northeast-2")
        conn_id: 연결 식별자 (기본값: "default")
    """
    try:
        client = boto3.client("redshift", region_name=region)
        creds = client.get_cluster_credentials(
            DbUser=user,
            DbName=database,
            ClusterIdentifier=cluster_id,
            DurationSeconds=3600,
            AutoCreate=False,
        )
        host = f"{cluster_id}.{region}.redshift.amazonaws.com"
        conn = psycopg2.connect(
            host=host,
            port=5439,
            database=database,
            user=creds["DbUser"],
            password=creds["DbPassword"],
        )
        conn.close()
    except Exception as e:
        return f"[ERROR] Redshift IAM 자격증명 발급 또는 연결 실패: {e}"

    _redshift_connections[conn_id] = {
        "cluster_id": cluster_id,
        "database": database,
        "user": user,
        "region": region,
    }
    return f"[OK] Redshift 연결 완료: {conn_id} ({cluster_id}/{database})"


def run_redshift_query(
    conn_id: str,
    sql: str,
    limit: int = 500,
) -> str:
    """[Redshift] Redshift에 SELECT 쿼리를 실행하고 결과를 마크다운 테이블로 반환한다.

    Args:
        conn_id: 연결 식별자
        sql: SELECT 쿼리 (DML 자동 차단)
        limit: 최대 반환 행 수 (기본값: 500)
    """
    err = _validate_select(sql)
    if err:
        return f"[ERROR] {err}"

    if conn_id not in _redshift_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_redshift()를 먼저 호출하세요."

    try:
        conn = _get_redshift_conn(conn_id)
        try:
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM ({sql}) AS _sub LIMIT {limit}")
            rows = cur.fetchall()
            columns = [d[0] for d in cur.description] if cur.description else []
        finally:
            conn.close()
    except Exception as e:
        return f"[ERROR] 쿼리 실행 실패: {e}"

    if not rows:
        return "결과가 없습니다."

    header = " | ".join(columns)
    sep = " | ".join(["---"] * len(columns))
    body_rows = "\n".join(f"| {' | '.join(str(v) for v in row)} |" for row in rows)
    return f"| {header} |\n| {sep} |\n{body_rows}"


def get_redshift_schema(
    conn_id: str,
    schema: str = "public",
) -> str:
    """[Redshift] Redshift 스키마의 테이블 및 컬럼 정보를 반환한다.

    Args:
        conn_id: 연결 식별자
        schema: 조회할 스키마명 (기본값: "public")
    """
    if conn_id not in _redshift_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    sql = f"""
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = '{schema}'
        ORDER BY table_name, ordinal_position
    """
    try:
        conn = _get_redshift_conn(conn_id)
        try:
            cur = conn.cursor()
            cur.execute(sql)
            rows = cur.fetchall()
        finally:
            conn.close()
    except Exception as e:
        return f"[ERROR] 스키마 조회 실패: {e}"

    if not rows:
        return f"스키마 '{schema}'에 테이블이 없습니다."

    lines = [f"## {schema} 스키마\n"]
    current_table = None
    for table_name, column_name, data_type in rows:
        if table_name != current_table:
            lines.append(f"\n### {table_name}")
            current_table = table_name
        lines.append(f"- {column_name}: {data_type}")

    return "\n".join(lines)


def list_redshift_tables(
    conn_id: str,
    schema: str = "public",
) -> str:
    """[Redshift] Redshift 스키마의 테이블 목록을 반환한다.

    Args:
        conn_id: 연결 식별자
        schema: 조회할 스키마명 (기본값: "public")
    """
    if conn_id not in _redshift_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    sql = f"""
        SELECT schemaname, tablename, tableowner
        FROM pg_tables
        WHERE schemaname = '{schema}'
        ORDER BY tablename
    """
    try:
        conn = _get_redshift_conn(conn_id)
        try:
            cur = conn.cursor()
            cur.execute(sql)
            rows = cur.fetchall()
        finally:
            conn.close()
    except Exception as e:
        return f"[ERROR] 테이블 목록 조회 실패: {e}"

    if not rows:
        return f"스키마 '{schema}'에 테이블이 없습니다."

    lines = [f"## {schema} 테이블 목록\n", "| schema | table | owner |", "| --- | --- | --- |"]
    for schemaname, tablename, tableowner in rows:
        lines.append(f"| {schemaname} | {tablename} | {tableowner} |")

    return "\n".join(lines)
