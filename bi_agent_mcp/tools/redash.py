"""
Redash 연동 도구.
"""
import json
import logging
from typing import Dict, Optional

import httpx

logger = logging.getLogger(__name__)

# 메모리 캐시: {conn_id: {"url": ..., "api_key": ...}}
_redash_connections: Dict[str, dict] = {}


def connect_redash(
    url: str,
    api_key: str,
    conn_id: str = "default",
) -> str:
    """[Redash] Redash 서버 연결 등록.

    Args:
        url: Redash 서버 URL (예: http://localhost:5000)
        api_key: Redash API 키
        conn_id: 연결 식별자 (기본값: "default")

    Returns:
        상태 메시지
    """
    url = url.rstrip("/")
    headers = {"Authorization": f"Key {api_key}"}

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{url}/api/session", headers=headers)

        if resp.status_code == 401:
            return "[ERROR] Redash 인증 실패: api_key를 확인하세요."
        if resp.status_code != 200:
            return f"[ERROR] Redash 연결 실패: HTTP {resp.status_code}"

    except httpx.RequestError as e:
        return f"[ERROR] Redash 연결 중 네트워크 오류: {e}"

    _redash_connections[conn_id] = {"url": url, "api_key": api_key}
    return f"[SUCCESS] Redash 연결 성공 (conn_id={conn_id})"


def list_redash_queries(conn_id: str = "default") -> str:
    """[Redash] 저장된 쿼리 목록 조회.

    Args:
        conn_id: 연결 식별자 (기본값: "default")

    Returns:
        쿼리 목록 JSON 문자열
    """
    if conn_id not in _redash_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_redash()를 먼저 호출하세요."

    creds = _redash_connections[conn_id]
    url = creds["url"]
    headers = {"Authorization": f"Key {creds['api_key']}"}

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{url}/api/queries", headers=headers)

        if resp.status_code == 401:
            return "[ERROR] Redash 인증 만료: connect_redash()로 재연결하세요."
        if resp.status_code != 200:
            return f"[ERROR] 쿼리 목록 조회 실패: HTTP {resp.status_code}"

        data = resp.json()
        results = data.get("results", data) if isinstance(data, dict) else data

        return json.dumps(results, ensure_ascii=False, indent=2)

    except httpx.RequestError as e:
        return f"[ERROR] 쿼리 목록 조회 중 네트워크 오류: {e}"


def run_redash_query(
    conn_id: str,
    query_id: int,
    parameters: Optional[str] = None,
) -> str:
    """[Redash] 쿼리 실행 및 결과 반환.

    Args:
        conn_id: 연결 식별자
        query_id: 실행할 쿼리 ID
        parameters: 파라미터 JSON 문자열 (기본값: None)

    Returns:
        쿼리 결과 JSON 문자열
    """
    if conn_id not in _redash_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_redash()를 먼저 호출하세요."

    creds = _redash_connections[conn_id]
    url = creds["url"]
    headers = {"Authorization": f"Key {creds['api_key']}"}

    params_parsed = {}
    if parameters:
        try:
            params_parsed = json.loads(parameters)
        except json.JSONDecodeError as e:
            return f"[ERROR] parameters JSON 파싱 실패: {e}"

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{url}/api/queries/{query_id}/results",
                headers=headers,
                json={"parameters": params_parsed},
            )

        if resp.status_code == 401:
            return "[ERROR] Redash 인증 만료: connect_redash()로 재연결하세요."
        if resp.status_code == 404:
            return f"[ERROR] 쿼리 ID {query_id}를 찾을 수 없습니다."
        if resp.status_code not in (200, 201):
            return f"[ERROR] 쿼리 실행 실패: HTTP {resp.status_code} - {resp.text}"

        result = resp.json()
        return json.dumps(result, ensure_ascii=False, indent=2)

    except httpx.RequestError as e:
        return f"[ERROR] 쿼리 실행 중 네트워크 오류: {e}"
    except Exception as e:
        logger.error("Redash 쿼리 실행 예외: %s", e)
        return f"[ERROR] 쿼리 실행 중 예외 발생: {e}"


def list_redash_dashboards(conn_id: str = "default") -> str:
    """[Redash] 대시보드 목록 조회.

    Args:
        conn_id: 연결 식별자 (기본값: "default")

    Returns:
        대시보드 목록 JSON 문자열
    """
    if conn_id not in _redash_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_redash()를 먼저 호출하세요."

    creds = _redash_connections[conn_id]
    url = creds["url"]
    headers = {"Authorization": f"Key {creds['api_key']}"}

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{url}/api/dashboards", headers=headers)

        if resp.status_code == 401:
            return "[ERROR] Redash 인증 만료: connect_redash()로 재연결하세요."
        if resp.status_code != 200:
            return f"[ERROR] 대시보드 목록 조회 실패: HTTP {resp.status_code}"

        data = resp.json()
        results = data.get("results", data) if isinstance(data, dict) else data

        return json.dumps(results, ensure_ascii=False, indent=2)

    except httpx.RequestError as e:
        return f"[ERROR] 대시보드 목록 조회 중 네트워크 오류: {e}"
