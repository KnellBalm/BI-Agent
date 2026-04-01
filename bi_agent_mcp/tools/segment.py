"""
Segment Public API 연동 도구.
"""
import json
import logging
from typing import Dict

import httpx

logger = logging.getLogger(__name__)

_segment_connections: Dict[str, dict] = {}

SEGMENT_API = "https://api.segmentapis.com"


def connect_segment(
    access_token: str,
    workspace_slug: str,
    conn_id: str = "default",
) -> str:
    """[Segment] Segment 워크스페이스 연결 등록.

    Args:
        access_token: Segment Public API Access Token
        workspace_slug: Segment 워크스페이스 슬러그
        conn_id: 연결 식별자 (기본값: "default")

    Returns:
        상태 메시지
    """
    if not access_token or not workspace_slug:
        return "[ERROR] access_token과 workspace_slug이 필요합니다."

    try:
        resp = httpx.get(
            f"{SEGMENT_API}/sources",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15.0,
        )

        if resp.status_code == 401:
            return "[ERROR] Segment 인증 실패: access_token을 확인하세요."
        if resp.status_code != 200:
            return f"[ERROR] Segment API 호출 실패: HTTP {resp.status_code} - {resp.text}"

    except httpx.RequestError as e:
        logger.error("Segment 네트워크 오류: %s", e)
        return f"[ERROR] Segment 네트워크 오류: {e}"

    _segment_connections[conn_id] = {
        "access_token": access_token,
        "workspace_slug": workspace_slug,
    }

    return f"[SUCCESS] Segment 연결 등록 완료 (conn_id='{conn_id}', workspace='{workspace_slug}')"


def get_segment_sources(conn_id: str = "default") -> str:
    """[Segment] Sources 목록 조회.

    Args:
        conn_id: 연결 식별자 (기본값: "default")

    Returns:
        Sources 목록 JSON 또는 에러 메시지
    """
    if conn_id not in _segment_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_segment()을 먼저 호출하세요."

    creds = _segment_connections[conn_id]

    try:
        resp = httpx.get(
            f"{SEGMENT_API}/sources",
            headers={"Authorization": f"Bearer {creds['access_token']}"},
            timeout=15.0,
        )

        if resp.status_code == 401:
            return "[ERROR] Segment 인증 실패: access_token을 확인하세요."
        if resp.status_code != 200:
            return f"[ERROR] Segment API 호출 실패: HTTP {resp.status_code} - {resp.text}"

        data = resp.json()
        sources = data.get("data", {}).get("sources", [])

        result = {
            "total": len(sources),
            "sources": [
                {
                    "id": s.get("id"),
                    "name": s.get("name"),
                    "slug": s.get("slug"),
                    "enabled": s.get("enabled"),
                    "writeKey": s.get("writeKey"),
                }
                for s in sources
            ],
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except httpx.RequestError as e:
        logger.error("Segment Sources 네트워크 오류: %s", e)
        return f"[ERROR] Segment 네트워크 오류: {e}"
    except Exception as e:
        logger.error("Segment Sources 조회 예외: %s", e)
        return f"[ERROR] Segment Sources 조회 중 예외 발생: {e}"


def get_segment_events(
    conn_id: str,
    source_slug: str,
    from_date: str,
    to_date: str,
    limit: int = 100,
) -> str:
    """[Segment] Source 이벤트 위반(Event Violations) 조회.

    Args:
        conn_id: 연결 식별자
        source_slug: Segment Source 슬러그
        from_date: 시작일 (YYYY-MM-DD)
        to_date: 종료일 (YYYY-MM-DD)
        limit: 최대 반환 건수 (기본값: 100)

    Returns:
        이벤트 위반 목록 JSON 또는 에러 메시지
    """
    if conn_id not in _segment_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_segment()을 먼저 호출하세요."

    creds = _segment_connections[conn_id]

    try:
        params = {
            "pagination.count": limit,
        }
        resp = httpx.get(
            f"{SEGMENT_API}/sources/{source_slug}/schema/event-violations",
            headers={"Authorization": f"Bearer {creds['access_token']}"},
            params=params,
            timeout=15.0,
        )

        if resp.status_code == 401:
            return "[ERROR] Segment 인증 실패: access_token을 확인하세요."
        if resp.status_code == 404:
            return f"[ERROR] Source '{source_slug}'를 찾을 수 없습니다."
        if resp.status_code != 200:
            return f"[ERROR] Segment API 호출 실패: HTTP {resp.status_code} - {resp.text}"

        data = resp.json()
        violations = data.get("data", {}).get("eventViolations", [])

        result = {
            "source_slug": source_slug,
            "from_date": from_date,
            "to_date": to_date,
            "total": len(violations),
            "event_violations": violations[:limit],
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except httpx.RequestError as e:
        logger.error("Segment 이벤트 네트워크 오류: %s", e)
        return f"[ERROR] Segment 네트워크 오류: {e}"
    except Exception as e:
        logger.error("Segment 이벤트 조회 예외: %s", e)
        return f"[ERROR] Segment 이벤트 조회 중 예외 발생: {e}"


def get_segment_traits(
    conn_id: str,
    space_id: str,
    limit: int = 100,
) -> str:
    """[Segment] Audience traits(사용자 그룹 정의) 조회.

    Args:
        conn_id: 연결 식별자
        space_id: Segment Space ID
        limit: 최대 반환 건수 (기본값: 100)

    Returns:
        사용자 그룹 정의 목록 JSON 또는 에러 메시지
    """
    if conn_id not in _segment_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_segment()을 먼저 호출하세요."

    creds = _segment_connections[conn_id]

    try:
        params = {
            "pagination.count": limit,
        }
        resp = httpx.get(
            f"{SEGMENT_API}/spaces/{space_id}/user-group-definitions",
            headers={"Authorization": f"Bearer {creds['access_token']}"},
            params=params,
            timeout=15.0,
        )

        if resp.status_code == 401:
            return "[ERROR] Segment 인증 실패: access_token을 확인하세요."
        if resp.status_code == 404:
            return f"[ERROR] Space '{space_id}'를 찾을 수 없습니다."
        if resp.status_code != 200:
            return f"[ERROR] Segment API 호출 실패: HTTP {resp.status_code} - {resp.text}"

        data = resp.json()
        definitions = data.get("data", {}).get("userGroupDefinitions", [])

        result = {
            "space_id": space_id,
            "total": len(definitions),
            "user_group_definitions": definitions[:limit],
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except httpx.RequestError as e:
        logger.error("Segment traits 네트워크 오류: %s", e)
        return f"[ERROR] Segment 네트워크 오류: {e}"
    except Exception as e:
        logger.error("Segment traits 조회 예외: %s", e)
        return f"[ERROR] Segment traits 조회 중 예외 발생: {e}"
