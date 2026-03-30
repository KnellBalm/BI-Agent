"""
Apache Superset 연동 도구.
"""
import json
import logging
from typing import Dict

import httpx

logger = logging.getLogger(__name__)

_superset_connections: Dict[str, dict] = {}  # {conn_id: {"url": ..., "token": ...}}


def connect_superset(
    url: str,
    username: str,
    password: str,
    conn_id: str = "default",
) -> str:
    """[Superset] Apache Superset 연결 및 JWT 토큰 획득.

    Args:
        url: Superset 서버 URL (예: http://localhost:8088)
        username: 로그인 사용자명
        password: 로그인 비밀번호
        conn_id: 연결 식별자 (기본값: "default")

    Returns:
        상태 메시지
    """
    login_url = f"{url.rstrip('/')}/api/v1/security/login"
    payload = {
        "username": username,
        "password": password,
        "provider": "db",
        "refresh": True,
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(login_url, json=payload)

        if resp.status_code == 401:
            return "[ERROR] Superset 인증 실패: username 또는 password를 확인하세요."
        if resp.status_code != 200:
            return f"[ERROR] Superset 연결 실패: HTTP {resp.status_code} - {resp.text}"

        data = resp.json()
        access_token = data.get("access_token")
        if not access_token:
            return "[ERROR] Superset 응답에 access_token이 없습니다."

    except httpx.RequestError as e:
        return f"[ERROR] Superset 연결 중 네트워크 오류: {e}"

    _superset_connections[conn_id] = {
        "url": url.rstrip("/"),
        "token": access_token,
    }

    return f"[SUCCESS] Superset 연결 성공 (conn_id={conn_id})"


def list_superset_charts(
    conn_id: str,
    page: int = 0,
    page_size: int = 20,
) -> str:
    """[Superset] 차트 목록 조회.

    Args:
        conn_id: 연결 식별자
        page: 페이지 번호 (0부터 시작)
        page_size: 페이지당 항목 수

    Returns:
        차트 목록 마크다운 테이블
    """
    if conn_id not in _superset_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_superset()을 먼저 호출하세요."

    conn = _superset_connections[conn_id]
    url = f"{conn['url']}/api/v1/chart/"
    headers = {"Authorization": f"Bearer {conn['token']}"}
    params = {"q": json.dumps({"page": page, "page_size": page_size})}

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, headers=headers, params=params)

        if resp.status_code == 401:
            return "[ERROR] Superset 인증 만료: connect_superset()으로 다시 연결하세요."
        if resp.status_code != 200:
            return f"[ERROR] 차트 목록 조회 실패: HTTP {resp.status_code} - {resp.text}"

        data = resp.json()
        charts = data.get("result", [])

        if not charts:
            return "조회된 차트가 없습니다."

        lines = [
            "| ID | 이름 | 차트 유형 | 수정일 |",
            "| --- | --- | --- | --- |",
        ]
        for chart in charts:
            chart_id = chart.get("id", "")
            name = chart.get("slice_name", "")
            viz_type = chart.get("viz_type", "")
            changed_on = chart.get("changed_on_humanized", "")
            lines.append(f"| {chart_id} | {name} | {viz_type} | {changed_on} |")

        return "\n".join(lines)

    except httpx.RequestError as e:
        return f"[ERROR] Superset 네트워크 오류: {e}"
    except Exception as e:
        logger.error("Superset 차트 목록 조회 예외: %s", e)
        return f"[ERROR] 차트 목록 조회 중 예외 발생: {e}"


def run_superset_sql(
    conn_id: str,
    database_id: int,
    sql: str,
    limit: int = 500,
) -> str:
    """[Superset] SQL Lab 쿼리 실행.

    Args:
        conn_id: 연결 식별자
        database_id: Superset 데이터베이스 ID
        sql: 실행할 SQL 쿼리
        limit: 최대 행 수 (기본값: 500)

    Returns:
        쿼리 결과 마크다운 테이블
    """
    if conn_id not in _superset_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_superset()을 먼저 호출하세요."

    conn = _superset_connections[conn_id]
    url = f"{conn['url']}/api/v1/sqllab/execute/"
    headers = {"Authorization": f"Bearer {conn['token']}"}
    payload = {
        "database_id": database_id,
        "sql": sql,
        "runAsync": False,
        "limit": limit,
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, headers=headers, json=payload)

        if resp.status_code == 401:
            return "[ERROR] Superset 인증 만료: connect_superset()으로 다시 연결하세요."
        if resp.status_code == 400:
            return f"[ERROR] 잘못된 SQL 또는 파라미터: {resp.text}"
        if resp.status_code != 200:
            return f"[ERROR] SQL 실행 실패: HTTP {resp.status_code} - {resp.text}"

        data = resp.json()
        columns = data.get("columns", [])
        rows = data.get("data", [])

        if not columns:
            return "쿼리 결과가 없습니다."

        col_names = [col.get("name", str(i)) for i, col in enumerate(columns)]
        lines = [
            "| " + " | ".join(col_names) + " |",
            "| " + " | ".join(["---"] * len(col_names)) + " |",
        ]
        for row in rows[:limit]:
            values = [str(row.get(col, "")) for col in col_names]
            lines.append("| " + " | ".join(values) + " |")

        total = data.get("query", {}).get("rows", len(rows))
        lines.append(f"\n총 {total}행 반환")
        return "\n".join(lines)

    except httpx.RequestError as e:
        return f"[ERROR] Superset 네트워크 오류: {e}"
    except Exception as e:
        logger.error("Superset SQL 실행 예외: %s", e)
        return f"[ERROR] SQL 실행 중 예외 발생: {e}"


def list_superset_dashboards(
    conn_id: str,
    page: int = 0,
    page_size: int = 20,
) -> str:
    """[Superset] 대시보드 목록 조회.

    Args:
        conn_id: 연결 식별자
        page: 페이지 번호 (0부터 시작)
        page_size: 페이지당 항목 수

    Returns:
        대시보드 목록 마크다운 테이블
    """
    if conn_id not in _superset_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_superset()을 먼저 호출하세요."

    conn = _superset_connections[conn_id]
    url = f"{conn['url']}/api/v1/dashboard/"
    headers = {"Authorization": f"Bearer {conn['token']}"}
    params = {"q": json.dumps({"page": page, "page_size": page_size})}

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, headers=headers, params=params)

        if resp.status_code == 401:
            return "[ERROR] Superset 인증 만료: connect_superset()으로 다시 연결하세요."
        if resp.status_code != 200:
            return f"[ERROR] 대시보드 목록 조회 실패: HTTP {resp.status_code} - {resp.text}"

        data = resp.json()
        dashboards = data.get("result", [])

        if not dashboards:
            return "조회된 대시보드가 없습니다."

        lines = [
            "| ID | 제목 | 상태 | 수정일 |",
            "| --- | --- | --- | --- |",
        ]
        for dash in dashboards:
            dash_id = dash.get("id", "")
            title = dash.get("dashboard_title", "")
            status = dash.get("status", "")
            changed_on = dash.get("changed_on_humanized", "")
            lines.append(f"| {dash_id} | {title} | {status} | {changed_on} |")

        return "\n".join(lines)

    except httpx.RequestError as e:
        return f"[ERROR] Superset 네트워크 오류: {e}"
    except Exception as e:
        logger.error("Superset 대시보드 목록 조회 예외: %s", e)
        return f"[ERROR] 대시보드 목록 조회 중 예외 발생: {e}"
