"""
Databricks REST API 연동 도구.
"""
import json
import logging
from typing import Dict, Optional

import httpx

logger = logging.getLogger(__name__)

# 메모리 캐시: {conn_id: {"host": ..., "token": ...}}
_databricks_connections: Dict[str, dict] = {}


def connect_databricks(
    host: str,
    token: str,
    conn_id: str = "default",
) -> str:
    """[Databricks] Databricks 워크스페이스 연결 등록 및 검증.

    Args:
        host: Databricks 워크스페이스 URL (예: https://adb-xxxx.azuredatabricks.net)
        token: Databricks Personal Access Token
        conn_id: 연결 식별자 (기본값: "default")

    Returns:
        상태 메시지
    """
    host = host.rstrip("/")
    headers = {"Authorization": f"Bearer {token}"}

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{host}/api/2.0/clusters/list", headers=headers)

        if resp.status_code == 401:
            return "[ERROR] Databricks 인증 실패: token을 확인하세요."
        if resp.status_code == 403:
            return "[ERROR] Databricks 권한 없음: 클러스터 접근 권한을 확인하세요."
        if resp.status_code != 200:
            return f"[ERROR] Databricks 연결 실패: HTTP {resp.status_code}"

    except httpx.RequestError as e:
        return f"[ERROR] Databricks 연결 중 네트워크 오류: {e}"

    _databricks_connections[conn_id] = {"host": host, "token": token}
    return f"[SUCCESS] Databricks 연결 성공 (conn_id={conn_id}, host={host})"


def run_databricks_sql(
    conn_id: str,
    warehouse_id: str,
    sql: str,
    catalog: Optional[str] = None,
    schema: Optional[str] = None,
) -> str:
    """[Databricks] SQL Warehouse에서 SQL 쿼리 실행.

    Args:
        conn_id: 연결 식별자
        warehouse_id: SQL Warehouse ID
        sql: 실행할 SQL 쿼리
        catalog: Unity Catalog 카탈로그명 (선택)
        schema: 스키마명 (선택)

    Returns:
        쿼리 결과 (JSON 문자열)
    """
    if conn_id not in _databricks_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_databricks()를 먼저 호출하세요."

    creds = _databricks_connections[conn_id]
    host = creds["host"]
    headers = {
        "Authorization": f"Bearer {creds['token']}",
        "Content-Type": "application/json",
    }

    payload: dict = {
        "warehouse_id": warehouse_id,
        "statement": sql,
        "wait_timeout": "30s",
    }
    if catalog:
        payload["catalog"] = catalog
    if schema:
        payload["schema"] = schema

    try:
        with httpx.Client(timeout=35.0) as client:
            resp = client.post(
                f"{host}/api/2.0/sql/statements",
                headers=headers,
                json=payload,
            )

        if resp.status_code == 401:
            return "[ERROR] Databricks 인증 만료: connect_databricks()로 재연결하세요."
        if resp.status_code == 400:
            return f"[ERROR] SQL 요청 오류: {resp.text}"
        if resp.status_code != 200:
            return f"[ERROR] SQL 실행 실패: HTTP {resp.status_code} - {resp.text}"

        data = resp.json()
        status = data.get("status", {}).get("state", "")
        if status == "FAILED":
            error_msg = data.get("status", {}).get("error", {}).get("message", "알 수 없는 오류")
            return f"[ERROR] SQL 실행 실패: {error_msg}"

        result = data.get("result", {})
        schema_info = data.get("manifest", {}).get("schema", {}).get("columns", [])
        columns = [col.get("name", "") for col in schema_info]
        rows = result.get("data_array", [])

        output = {
            "status": status,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
        }
        return json.dumps(output, ensure_ascii=False, indent=2)

    except httpx.RequestError as e:
        return f"[ERROR] SQL 실행 중 네트워크 오류: {e}"
    except Exception as e:
        logger.error("Databricks SQL 실행 예외: %s", e)
        return f"[ERROR] SQL 실행 중 예외 발생: {e}"


def list_databricks_clusters(conn_id: str) -> str:
    """[Databricks] 클러스터 목록 조회.

    Args:
        conn_id: 연결 식별자

    Returns:
        클러스터 목록 (JSON 문자열)
    """
    if conn_id not in _databricks_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_databricks()를 먼저 호출하세요."

    creds = _databricks_connections[conn_id]
    host = creds["host"]
    headers = {"Authorization": f"Bearer {creds['token']}"}

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{host}/api/2.0/clusters/list", headers=headers)

        if resp.status_code == 401:
            return "[ERROR] Databricks 인증 만료: connect_databricks()로 재연결하세요."
        if resp.status_code != 200:
            return f"[ERROR] 클러스터 목록 조회 실패: HTTP {resp.status_code}"

        data = resp.json()
        clusters = data.get("clusters", [])

        result = []
        for c in clusters:
            result.append({
                "cluster_id": c.get("cluster_id", ""),
                "cluster_name": c.get("cluster_name", ""),
                "state": c.get("state", ""),
                "spark_version": c.get("spark_version", ""),
                "node_type_id": c.get("node_type_id", ""),
                "num_workers": c.get("num_workers", 0),
            })

        return json.dumps({"clusters": result, "count": len(result)}, ensure_ascii=False, indent=2)

    except httpx.RequestError as e:
        return f"[ERROR] 클러스터 목록 조회 중 네트워크 오류: {e}"


def list_databricks_jobs(conn_id: str, limit: int = 20) -> str:
    """[Databricks] Job 목록 조회.

    Args:
        conn_id: 연결 식별자
        limit: 조회할 최대 Job 수 (기본값: 20)

    Returns:
        Job 목록 (JSON 문자열)
    """
    if conn_id not in _databricks_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_databricks()를 먼저 호출하세요."

    creds = _databricks_connections[conn_id]
    host = creds["host"]
    headers = {"Authorization": f"Bearer {creds['token']}"}

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                f"{host}/api/2.1/jobs/list",
                headers=headers,
                params={"limit": limit},
            )

        if resp.status_code == 401:
            return "[ERROR] Databricks 인증 만료: connect_databricks()로 재연결하세요."
        if resp.status_code != 200:
            return f"[ERROR] Job 목록 조회 실패: HTTP {resp.status_code}"

        data = resp.json()
        jobs = data.get("jobs", [])

        result = []
        for j in jobs:
            settings = j.get("settings", {})
            result.append({
                "job_id": j.get("job_id", ""),
                "job_name": settings.get("name", ""),
                "created_time": j.get("created_time", ""),
                "creator_user_name": j.get("creator_user_name", ""),
            })

        return json.dumps({"jobs": result, "count": len(result)}, ensure_ascii=False, indent=2)

    except httpx.RequestError as e:
        return f"[ERROR] Job 목록 조회 중 네트워크 오류: {e}"
