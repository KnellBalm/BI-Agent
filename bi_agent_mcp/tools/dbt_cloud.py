"""
dbt Cloud Admin API 연동 도구.
"""
import json
import logging
from typing import Dict, Optional

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://cloud.getdbt.com"

# 메모리 캐시: {conn_id: {"api_token": ..., "account_id": ...}}
_dbt_connections: Dict[str, dict] = {}


def connect_dbt_cloud(
    api_token: str,
    account_id: str,
    conn_id: str = "default",
) -> str:
    """[dbtCloud] dbt Cloud 연결 등록 및 계정 정보 검증.

    Args:
        api_token: dbt Cloud API 토큰
        account_id: dbt Cloud 계정 ID
        conn_id: 연결 식별자 (기본값: "default")

    Returns:
        상태 메시지
    """
    headers = {"Authorization": f"Token {api_token}"}
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{BASE_URL}/api/v2/accounts/{account_id}/",
                headers=headers,
            )
        if resp.status_code == 401:
            return "[ERROR] dbt Cloud 인증 실패: api_token을 확인하세요."
        if resp.status_code == 404:
            return f"[ERROR] dbt Cloud 계정 ID '{account_id}'를 찾을 수 없습니다."
        if resp.status_code != 200:
            return f"[ERROR] dbt Cloud 연결 실패: HTTP {resp.status_code}"

        data = resp.json()
        account_name = data.get("data", {}).get("name", account_id)

    except httpx.RequestError as e:
        return f"[ERROR] dbt Cloud 연결 중 네트워크 오류: {e}"

    _dbt_connections[conn_id] = {"api_token": api_token, "account_id": account_id}
    return f"[SUCCESS] dbt Cloud 연결 성공 (conn_id={conn_id}, account={account_name})"


def list_dbt_jobs(
    conn_id: str = "default",
    project_id: Optional[str] = None,
) -> str:
    """[dbtCloud] dbt Cloud Job 목록 조회.

    Args:
        conn_id: 연결 식별자
        project_id: 특정 프로젝트 ID로 필터링 (None이면 전체)

    Returns:
        Job 목록 JSON
    """
    if conn_id not in _dbt_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_dbt_cloud()를 먼저 호출하세요."

    creds = _dbt_connections[conn_id]
    headers = {"Authorization": f"Token {creds['api_token']}"}
    account_id = creds["account_id"]

    params = {}
    if project_id is not None:
        params["project_id"] = project_id

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                f"{BASE_URL}/api/v2/accounts/{account_id}/jobs/",
                headers=headers,
                params=params,
            )
        if resp.status_code == 401:
            return "[ERROR] dbt Cloud 인증 만료: connect_dbt_cloud()로 재연결하세요."
        if resp.status_code != 200:
            return f"[ERROR] Job 목록 조회 실패: HTTP {resp.status_code}"

        data = resp.json()
        jobs = data.get("data", [])
        result = {
            "count": len(jobs),
            "jobs": [
                {
                    "id": j.get("id"),
                    "name": j.get("name"),
                    "project_id": j.get("project_id"),
                    "environment_id": j.get("environment_id"),
                    "state": j.get("state"),
                    "created_at": j.get("created_at"),
                }
                for j in jobs
            ],
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    except httpx.RequestError as e:
        return f"[ERROR] Job 목록 조회 중 네트워크 오류: {e}"


def get_dbt_run_results(
    conn_id: str,
    job_id: str,
    limit: int = 10,
) -> str:
    """[dbtCloud] dbt Cloud Job 최근 실행 결과 조회.

    Args:
        conn_id: 연결 식별자
        job_id: Job ID
        limit: 조회할 최대 실행 수 (기본값: 10)

    Returns:
        실행 결과 목록 JSON
    """
    if conn_id not in _dbt_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_dbt_cloud()를 먼저 호출하세요."

    creds = _dbt_connections[conn_id]
    headers = {"Authorization": f"Token {creds['api_token']}"}
    account_id = creds["account_id"]

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                f"{BASE_URL}/api/v2/accounts/{account_id}/runs/",
                headers=headers,
                params={"job_definition_id": job_id, "limit": limit},
            )
        if resp.status_code == 401:
            return "[ERROR] dbt Cloud 인증 만료: connect_dbt_cloud()로 재연결하세요."
        if resp.status_code != 200:
            return f"[ERROR] 실행 결과 조회 실패: HTTP {resp.status_code}"

        data = resp.json()
        runs = data.get("data", [])
        result = {
            "job_id": job_id,
            "count": len(runs),
            "runs": [
                {
                    "id": r.get("id"),
                    "status": r.get("status"),
                    "status_humanized": r.get("status_humanized"),
                    "created_at": r.get("created_at"),
                    "finished_at": r.get("finished_at"),
                    "duration_humanized": r.get("duration_humanized"),
                    "is_success": r.get("is_success"),
                    "is_error": r.get("is_error"),
                }
                for r in runs
            ],
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    except httpx.RequestError as e:
        return f"[ERROR] 실행 결과 조회 중 네트워크 오류: {e}"


def list_dbt_models(
    conn_id: str,
    project_id: str,
    job_id: Optional[str] = None,
) -> str:
    """[dbtCloud] dbt Cloud 프로젝트 모델 목록 조회.

    Args:
        conn_id: 연결 식별자
        project_id: 프로젝트 ID
        job_id: 특정 Job ID로 필터링 (None이면 전체)

    Returns:
        모델 목록 JSON
    """
    if conn_id not in _dbt_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_dbt_cloud()를 먼저 호출하세요."

    creds = _dbt_connections[conn_id]
    headers = {"Authorization": f"Token {creds['api_token']}"}
    account_id = creds["account_id"]

    params = {}
    if job_id is not None:
        params["job_id"] = job_id

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                f"{BASE_URL}/api/v2/accounts/{account_id}/projects/{project_id}/models/",
                headers=headers,
                params=params,
            )
        if resp.status_code == 401:
            return "[ERROR] dbt Cloud 인증 만료: connect_dbt_cloud()로 재연결하세요."
        if resp.status_code == 404:
            return f"[ERROR] 프로젝트 ID '{project_id}'를 찾을 수 없습니다."
        if resp.status_code != 200:
            return f"[ERROR] 모델 목록 조회 실패: HTTP {resp.status_code}"

        data = resp.json()
        models = data.get("data", [])
        result = {
            "project_id": project_id,
            "count": len(models),
            "models": [
                {
                    "unique_id": m.get("unique_id"),
                    "name": m.get("name"),
                    "schema": m.get("schema"),
                    "database": m.get("database"),
                    "materialization": m.get("config", {}).get("materialized"),
                    "description": m.get("description"),
                }
                for m in models
            ],
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    except httpx.RequestError as e:
        return f"[ERROR] 모델 목록 조회 중 네트워크 오류: {e}"
