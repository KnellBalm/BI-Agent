"""
Grafana HTTP API 연동 도구.
"""
import json
import logging
from typing import Dict

import httpx

logger = logging.getLogger(__name__)

# 메모리 캐시: {conn_id: {"url": ..., "api_key": ...}}
_grafana_connections: Dict[str, dict] = {}


def connect_grafana(
    url: str,
    api_key: str,
    conn_id: str = "default",
) -> str:
    """[Grafana] Grafana 서버 연결 등록 및 상태 검증.

    Args:
        url: Grafana 서버 URL (예: http://localhost:3000)
        api_key: Grafana API 키
        conn_id: 연결 식별자 (기본값: "default")

    Returns:
        상태 메시지
    """
    url = url.rstrip("/")
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{url}/api/health", headers=headers)

        if resp.status_code == 401:
            return "[ERROR] Grafana 인증 실패: api_key를 확인하세요."
        if resp.status_code != 200:
            return f"[ERROR] Grafana 연결 실패: HTTP {resp.status_code}"

    except httpx.RequestError as e:
        return f"[ERROR] Grafana 연결 중 네트워크 오류: {e}"

    _grafana_connections[conn_id] = {"url": url, "api_key": api_key}
    return f"[SUCCESS] Grafana 연결 성공 (conn_id={conn_id})"


def list_grafana_dashboards(conn_id: str = "default") -> str:
    """[Grafana] 대시보드 목록 조회.

    Args:
        conn_id: 연결 식별자 (기본값: "default")

    Returns:
        대시보드 목록 JSON
    """
    if conn_id not in _grafana_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_grafana()를 먼저 호출하세요."

    creds = _grafana_connections[conn_id]
    url = creds["url"]
    headers = {"Authorization": f"Bearer {creds['api_key']}"}

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{url}/api/search?type=dash-db", headers=headers)

        if resp.status_code == 401:
            return "[ERROR] Grafana 인증 만료: connect_grafana()로 재연결하세요."
        if resp.status_code != 200:
            return f"[ERROR] 대시보드 목록 조회 실패: HTTP {resp.status_code}"

        dashboards = resp.json()
        return json.dumps(dashboards, ensure_ascii=False, indent=2)

    except httpx.RequestError as e:
        return f"[ERROR] 대시보드 목록 조회 중 네트워크 오류: {e}"


def get_grafana_dashboard(conn_id: str, uid: str) -> str:
    """[Grafana] 특정 대시보드 상세 조회.

    Args:
        conn_id: 연결 식별자
        uid: 대시보드 UID

    Returns:
        대시보드 상세 정보 JSON
    """
    if conn_id not in _grafana_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_grafana()를 먼저 호출하세요."

    creds = _grafana_connections[conn_id]
    url = creds["url"]
    headers = {"Authorization": f"Bearer {creds['api_key']}"}

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{url}/api/dashboards/uid/{uid}", headers=headers)

        if resp.status_code == 401:
            return "[ERROR] Grafana 인증 만료: connect_grafana()로 재연결하세요."
        if resp.status_code == 404:
            return f"[ERROR] 대시보드 UID '{uid}'를 찾을 수 없습니다."
        if resp.status_code != 200:
            return f"[ERROR] 대시보드 조회 실패: HTTP {resp.status_code}"

        result = resp.json()
        return json.dumps(result, ensure_ascii=False, indent=2)

    except httpx.RequestError as e:
        return f"[ERROR] 대시보드 조회 중 네트워크 오류: {e}"


def query_grafana_datasource(
    conn_id: str,
    datasource_uid: str,
    query: str,
    from_time: str = "now-1h",
    to_time: str = "now",
) -> str:
    """[Grafana] Grafana datasource 쿼리 실행.

    Args:
        conn_id: 연결 식별자
        datasource_uid: 데이터소스 UID
        query: 쿼리 문자열 (JSON 또는 PromQL 등)
        from_time: 시작 시간 (기본값: "now-1h")
        to_time: 종료 시간 (기본값: "now")

    Returns:
        쿼리 결과 JSON
    """
    if conn_id not in _grafana_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_grafana()를 먼저 호출하세요."

    creds = _grafana_connections[conn_id]
    url = creds["url"]
    headers = {
        "Authorization": f"Bearer {creds['api_key']}",
        "Content-Type": "application/json",
    }

    payload = {
        "queries": [
            {
                "datasource": {"uid": datasource_uid},
                "expr": query,
                "refId": "A",
            }
        ],
        "from": from_time,
        "to": to_time,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(f"{url}/api/ds/query", headers=headers, json=payload)

        if resp.status_code == 401:
            return "[ERROR] Grafana 인증 만료: connect_grafana()로 재연결하세요."
        if resp.status_code == 404:
            return f"[ERROR] 데이터소스 UID '{datasource_uid}'를 찾을 수 없습니다."
        if resp.status_code != 200:
            return f"[ERROR] 데이터소스 쿼리 실패: HTTP {resp.status_code} - {resp.text}"

        result = resp.json()
        return json.dumps(result, ensure_ascii=False, indent=2)

    except httpx.RequestError as e:
        return f"[ERROR] 데이터소스 쿼리 중 네트워크 오류: {e}"
    except Exception as e:
        logger.error("Grafana 데이터소스 쿼리 예외: %s", e)
        return f"[ERROR] 데이터소스 쿼리 중 예외 발생: {e}"
