"""
Heap Analytics 연동 도구.
"""
import json
import logging
from typing import Dict

import httpx

logger = logging.getLogger(__name__)

_heap_connections: Dict[str, dict] = {}

HEAP_API = "https://heapanalytics.com/api/v1"


def connect_heap(
    app_id: str,
    api_key: str,
    conn_id: str = "default",
) -> str:
    """[Heap] Heap Analytics 연결 등록.

    Args:
        app_id: Heap 앱 ID
        api_key: Heap API 키
        conn_id: 연결 식별자 (기본값: "default")

    Returns:
        상태 메시지
    """
    if not app_id or not api_key:
        return "[ERROR] app_id와 api_key가 필요합니다."

    _heap_connections[conn_id] = {
        "app_id": app_id,
        "api_key": api_key,
    }

    return f"[SUCCESS] Heap Analytics 연결 등록 완료 (conn_id='{conn_id}')"


def get_heap_events(
    conn_id: str,
    event_name: str,
    from_date: str,
    to_date: str,
    limit: int = 100,
) -> str:
    """[Heap] 이벤트 데이터 조회.

    Args:
        conn_id: 연결 식별자
        event_name: 조회할 이벤트 이름
        from_date: 시작일 (YYYY-MM-DD)
        to_date: 종료일 (YYYY-MM-DD)
        limit: 최대 반환 행 수 (기본값: 100)

    Returns:
        이벤트 데이터 JSON 문자열 또는 에러 메시지
    """
    if conn_id not in _heap_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_heap()을 먼저 호출하세요."

    creds = _heap_connections[conn_id]

    try:
        payload = {
            "app_id": creds["app_id"],
            "event": event_name,
            "start_time": from_date,
            "end_time": to_date,
            "limit": limit,
        }
        headers = {
            "Authorization": f"Bearer {creds['api_key']}",
            "Content-Type": "application/json",
        }
        resp = httpx.post(
            f"{HEAP_API}/query",
            json=payload,
            headers=headers,
            timeout=30.0,
        )

        if resp.status_code == 401:
            return "[ERROR] Heap 인증 실패: api_key를 확인하세요."
        if resp.status_code == 400:
            return f"[ERROR] 잘못된 파라미터: {resp.text}"
        if resp.status_code != 200:
            return f"[ERROR] Heap API 호출 실패: HTTP {resp.status_code} - {resp.text}"

        data = resp.json()
        results = data.get("results", data)

        if not results:
            return "조회된 이벤트 데이터가 없습니다."

        return json.dumps(results, ensure_ascii=False, indent=2)

    except httpx.RequestError as e:
        logger.error("Heap 네트워크 오류: %s", e)
        return f"[ERROR] Heap 네트워크 오류: {e}"
    except Exception as e:
        logger.error("Heap 이벤트 조회 예외: %s", e)
        return f"[ERROR] Heap 이벤트 조회 중 예외 발생: {e}"


def get_heap_funnels(
    conn_id: str,
    funnel_id: str,
    from_date: str,
    to_date: str,
) -> str:
    """[Heap] 퍼널 분석 결과 조회.

    Args:
        conn_id: 연결 식별자
        funnel_id: Heap 퍼널 ID
        from_date: 시작일 (YYYY-MM-DD)
        to_date: 종료일 (YYYY-MM-DD)

    Returns:
        퍼널 분석 결과 JSON 문자열 또는 에러 메시지
    """
    if conn_id not in _heap_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_heap()을 먼저 호출하세요."

    creds = _heap_connections[conn_id]

    try:
        headers = {
            "Authorization": f"Bearer {creds['api_key']}",
            "Content-Type": "application/json",
        }
        params = {
            "app_id": creds["app_id"],
            "funnel_id": funnel_id,
            "start_time": from_date,
            "end_time": to_date,
        }
        resp = httpx.get(
            f"{HEAP_API}/funnels",
            params=params,
            headers=headers,
            timeout=15.0,
        )

        if resp.status_code == 401:
            return "[ERROR] Heap 인증 실패: api_key를 확인하세요."
        if resp.status_code == 400:
            return f"[ERROR] 잘못된 파라미터: {resp.text}"
        if resp.status_code != 200:
            return f"[ERROR] Heap 퍼널 API 호출 실패: HTTP {resp.status_code} - {resp.text}"

        data = resp.json()

        if not data:
            return "퍼널 데이터가 없습니다."

        return json.dumps(data, ensure_ascii=False, indent=2)

    except httpx.RequestError as e:
        logger.error("Heap 퍼널 네트워크 오류: %s", e)
        return f"[ERROR] Heap 네트워크 오류: {e}"
    except Exception as e:
        logger.error("Heap 퍼널 조회 예외: %s", e)
        return f"[ERROR] Heap 퍼널 조회 중 예외 발생: {e}"


def get_heap_user_properties(
    conn_id: str,
    user_id: str,
) -> str:
    """[Heap] 사용자 속성 조회.

    Args:
        conn_id: 연결 식별자
        user_id: Heap 사용자 ID

    Returns:
        사용자 속성 JSON 문자열 또는 에러 메시지
    """
    if conn_id not in _heap_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_heap()을 먼저 호출하세요."

    creds = _heap_connections[conn_id]

    try:
        headers = {
            "Authorization": f"Bearer {creds['api_key']}",
            "Content-Type": "application/json",
        }
        params = {
            "app_id": creds["app_id"],
            "user_id": user_id,
        }
        resp = httpx.get(
            f"{HEAP_API}/users/{user_id}",
            params=params,
            headers=headers,
            timeout=15.0,
        )

        if resp.status_code == 401:
            return "[ERROR] Heap 인증 실패: api_key를 확인하세요."
        if resp.status_code == 404:
            return f"[ERROR] 사용자 ID '{user_id}'를 찾을 수 없습니다."
        if resp.status_code == 400:
            return f"[ERROR] 잘못된 파라미터: {resp.text}"
        if resp.status_code != 200:
            return f"[ERROR] Heap 사용자 API 호출 실패: HTTP {resp.status_code} - {resp.text}"

        data = resp.json()

        if not data:
            return f"사용자 ID '{user_id}'의 속성 데이터가 없습니다."

        return json.dumps(data, ensure_ascii=False, indent=2)

    except httpx.RequestError as e:
        logger.error("Heap 사용자 네트워크 오류: %s", e)
        return f"[ERROR] Heap 네트워크 오류: {e}"
    except Exception as e:
        logger.error("Heap 사용자 조회 예외: %s", e)
        return f"[ERROR] Heap 사용자 속성 조회 중 예외 발생: {e}"
