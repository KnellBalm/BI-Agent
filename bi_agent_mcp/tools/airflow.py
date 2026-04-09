"""[Airflow] Apache Airflow REST API 연동 도구."""
import json
import logging
from typing import Dict, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

_airflow_connections: Dict[str, dict] = {}


def connect_airflow(
    base_url: str,
    username: str,
    password: str,
    conn_id: str = "default",
) -> str:
    """[Airflow] Airflow REST API에 연결한다.

    Args:
        base_url: Airflow 서버 URL (예: "http://airflow.internal:8080")
        username: Airflow 로그인 username
        password: Airflow 로그인 password
        conn_id: 연결 식별자 (기본값: "default")
    """
    base_url = base_url.rstrip("/")
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{base_url}/api/v1/health",
                auth=(username, password),
            )
        if resp.status_code == 401:
            return "[ERROR] Airflow 인증 실패: username 또는 password를 확인하세요."
        if resp.status_code != 200:
            return f"[ERROR] Airflow 연결 실패: HTTP {resp.status_code}"
    except httpx.RequestError as e:
        return f"[ERROR] Airflow 연결 중 네트워크 오류: {e}"

    _airflow_connections[conn_id] = {
        "base_url": base_url,
        "auth": (username, password),
    }
    return f"[OK] Airflow 연결 완료: {conn_id} ({base_url})"


def _get_creds(conn_id: str) -> Tuple[str, Tuple[str, str]]:
    if conn_id not in _airflow_connections:
        raise ValueError(f"연결 ID '{conn_id}'를 찾을 수 없습니다. connect_airflow()를 먼저 호출하세요.")
    info = _airflow_connections[conn_id]
    return info["base_url"], info["auth"]


def list_airflow_dags(
    conn_id: str,
    tags: str = None,
    only_active: bool = True,
    limit: int = 50,
) -> str:
    """[Airflow] DAG 목록과 활성화 상태를 반환한다.

    Args:
        conn_id: 연결 식별자
        tags: 태그 필터 (쉼표 구분, 예: "mart,daily")
        only_active: True이면 활성화된 DAG만 표시
        limit: 최대 반환 수 (기본값: 50)
    """
    if conn_id not in _airflow_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    base_url, auth = _get_creds(conn_id)
    params = {"limit": limit, "only_active": str(only_active).lower()}
    if tags:
        params["tags"] = tags

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{base_url}/api/v1/dags", auth=auth, params=params)
        if resp.status_code != 200:
            return f"[ERROR] DAG 목록 조회 실패: HTTP {resp.status_code}"
        data = resp.json()
    except httpx.RequestError as e:
        return f"[ERROR] 네트워크 오류: {e}"

    dags = data.get("dags", [])
    if not dags:
        return "DAG 목록이 없습니다."

    lines = [f"## DAG 목록 ({data.get('total_entries', len(dags))}개)\n",
             "| DAG ID | 활성화 | 일시정지 | 태그 |",
             "| --- | --- | --- | --- |"]
    for dag in dags:
        tags_str = ", ".join(t.get("name", "") for t in dag.get("tags", []))
        lines.append(f"| {dag['dag_id']} | {dag.get('is_active', '-')} | {dag.get('is_paused', '-')} | {tags_str} |")

    return "\n".join(lines)


def get_dag_status(
    conn_id: str,
    dag_id: str,
) -> str:
    """[Airflow] DAG의 최근 5회 실행 상태를 반환한다.

    Args:
        conn_id: 연결 식별자
        dag_id: DAG ID
    """
    if conn_id not in _airflow_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    base_url, auth = _get_creds(conn_id)
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                f"{base_url}/api/v1/dags/{dag_id}/dagRuns",
                auth=auth,
                params={"limit": 5, "order_by": "-start_date"},
            )
        if resp.status_code == 404:
            return f"[ERROR] DAG '{dag_id}'를 찾을 수 없습니다."
        if resp.status_code != 200:
            return f"[ERROR] DAG 상태 조회 실패: HTTP {resp.status_code}"
        data = resp.json()
    except httpx.RequestError as e:
        return f"[ERROR] 네트워크 오류: {e}"

    runs = data.get("dag_runs", [])
    if not runs:
        return f"DAG '{dag_id}'의 실행 이력이 없습니다."

    lines = [f"## {dag_id} 실행 상태\n",
             "| Run ID | 상태 | 시작 | 종료 |",
             "| --- | --- | --- | --- |"]
    for run in runs:
        lines.append(
            f"| {run.get('dag_run_id', '-')} | {run.get('state', '-')} "
            f"| {run.get('start_date', '-')} | {run.get('end_date', '-')} |"
        )

    return "\n".join(lines)


def trigger_dag(
    conn_id: str,
    dag_id: str,
    conf: str = "{}",
    logical_date: str = None,
) -> str:
    """[Airflow] DAG를 수동으로 트리거한다.

    Args:
        conn_id: 연결 식별자
        dag_id: 트리거할 DAG ID
        conf: DAG 실행 설정 (JSON 문자열, 기본값: "{}")
        logical_date: 논리적 실행 날짜 (ISO 8601, None이면 현재 시각)
    """
    if conn_id not in _airflow_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    base_url, auth = _get_creds(conn_id)
    try:
        conf_dict = json.loads(conf)
    except json.JSONDecodeError:
        return "[ERROR] conf 파라미터가 유효한 JSON이 아닙니다."

    body = {"conf": conf_dict}
    if logical_date:
        body["logical_date"] = logical_date

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                f"{base_url}/api/v1/dags/{dag_id}/dagRuns",
                auth=auth,
                json=body,
            )
        if resp.status_code == 404:
            return f"[ERROR] DAG '{dag_id}'를 찾을 수 없습니다."
        if resp.status_code not in (200, 201):
            return f"[ERROR] DAG 트리거 실패: HTTP {resp.status_code} — {resp.text}"
        data = resp.json()
    except httpx.RequestError as e:
        return f"[ERROR] 네트워크 오류: {e}"

    run_id = data.get("dag_run_id", "-")
    state = data.get("state", "-")
    return f"[OK] DAG 트리거 완료: {run_id} (state: {state})"


def get_task_logs(
    conn_id: str,
    dag_id: str,
    dag_run_id: str,
    task_id: str,
    task_try_number: int = 1,
) -> str:
    """[Airflow] 특정 태스크의 실행 로그를 반환한다.

    Args:
        conn_id: 연결 식별자
        dag_id: DAG ID
        dag_run_id: DAG Run ID (get_dag_status에서 확인)
        task_id: 태스크 ID
        task_try_number: 시도 번호 (기본값: 1)
    """
    if conn_id not in _airflow_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    base_url, auth = _get_creds(conn_id)
    url = (
        f"{base_url}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}"
        f"/taskInstances/{task_id}/logs/{task_try_number}"
    )

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(url, auth=auth)
        if resp.status_code == 404:
            return f"[ERROR] 태스크 로그를 찾을 수 없습니다: {dag_id}/{task_id}"
        if resp.status_code != 200:
            return f"[ERROR] 로그 조회 실패: HTTP {resp.status_code}"
        return resp.text[:5000]  # 최대 5000자
    except httpx.RequestError as e:
        return f"[ERROR] 네트워크 오류: {e}"


def list_dag_runs(
    conn_id: str,
    dag_id: str,
    limit: int = 10,
) -> str:
    """[Airflow] DAG의 최근 실행 이력을 반환한다.

    Args:
        conn_id: 연결 식별자
        dag_id: DAG ID
        limit: 최대 반환 수 (기본값: 10)
    """
    if conn_id not in _airflow_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    base_url, auth = _get_creds(conn_id)
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                f"{base_url}/api/v1/dags/{dag_id}/dagRuns",
                auth=auth,
                params={"limit": limit, "order_by": "-start_date"},
            )
        if resp.status_code != 200:
            return f"[ERROR] 실행 이력 조회 실패: HTTP {resp.status_code}"
        data = resp.json()
    except httpx.RequestError as e:
        return f"[ERROR] 네트워크 오류: {e}"

    runs = data.get("dag_runs", [])
    if not runs:
        return f"DAG '{dag_id}'의 실행 이력이 없습니다."

    lines = [f"## {dag_id} 최근 {limit}회 실행 이력\n",
             "| Run ID | 상태 | 시작 | 종료 |",
             "| --- | --- | --- | --- |"]
    for run in runs:
        lines.append(
            f"| {run.get('dag_run_id', '-')} | {run.get('state', '-')} "
            f"| {run.get('start_date', '-')} | {run.get('end_date', '-')} |"
        )

    return "\n".join(lines)
