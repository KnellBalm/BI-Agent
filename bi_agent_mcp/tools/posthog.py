"""
PostHog 연동 도구.
"""
import json
import logging
from typing import Dict, Optional

import httpx

logger = logging.getLogger(__name__)

_posthog_connections: Dict[str, dict] = {}
# {conn_id: {"api_key": ..., "project_id": ..., "host": "https://app.posthog.com"}}


def connect_posthog(
    api_key: str,
    project_id: str,
    host: str = "https://app.posthog.com",
    conn_id: str = "default",
) -> str:
    """[PostHog] PostHog 프로젝트 연결 등록.

    Args:
        api_key: PostHog Personal API Key
        project_id: PostHog 프로젝트 ID
        host: PostHog 호스트 URL (기본값: https://app.posthog.com)
        conn_id: 연결 식별자 (기본값: "default")

    Returns:
        상태 메시지
    """
    if not api_key:
        return "[ERROR] api_key가 필요합니다."
    if not project_id:
        return "[ERROR] project_id가 필요합니다."

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{host}/api/projects/{project_id}/",
                headers={"Authorization": f"Bearer {api_key}"},
            )
        if resp.status_code == 401:
            return "[ERROR] PostHog 인증 실패: API Key를 확인하세요."
        if resp.status_code == 404:
            return f"[ERROR] PostHog 프로젝트 '{project_id}'를 찾을 수 없습니다."
        if resp.status_code not in (200, 204):
            return f"[ERROR] PostHog 연결 테스트 실패: HTTP {resp.status_code}"
    except httpx.RequestError as e:
        return f"[ERROR] PostHog 연결 중 네트워크 오류: {e}"

    _posthog_connections[conn_id] = {
        "api_key": api_key,
        "project_id": str(project_id),
        "host": host.rstrip("/"),
    }

    return f"[SUCCESS] PostHog 연결 성공 (conn_id={conn_id}, project_id={project_id})"


def get_posthog_events(
    conn_id: str,
    event: Optional[str] = None,
    limit: int = 100,
    after: Optional[str] = None,
    before: Optional[str] = None,
) -> str:
    """[PostHog] 이벤트 로그 쿼리.

    Args:
        conn_id: 연결 식별자
        event: 필터링할 이벤트 이름 (Optional)
        limit: 반환할 이벤트 수 (기본값: 100)
        after: 시작 날짜 (ISO 형식, 예: 2026-03-01)
        before: 종료 날짜 (ISO 형식, 예: 2026-03-31)

    Returns:
        이벤트 목록 (마크다운 테이블)
    """
    if conn_id not in _posthog_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_posthog()를 먼저 호출하세요."

    creds = _posthog_connections[conn_id]
    url = f"{creds['host']}/api/projects/{creds['project_id']}/events/"

    params: dict = {"limit": limit}
    if event:
        params["event"] = event
    if after:
        params["after"] = after
    if before:
        params["before"] = before

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {creds['api_key']}"},
            )

        if resp.status_code == 401:
            return "[ERROR] PostHog 인증 실패: connect_posthog()로 키를 다시 등록하세요."
        if resp.status_code == 429:
            return "[ERROR] PostHog API Rate Limit 초과: 잠시 후 다시 시도하세요."
        if resp.status_code != 200:
            return f"[ERROR] PostHog 이벤트 조회 실패: HTTP {resp.status_code} - {resp.text}"

        data = resp.json()
        results = data.get("results", [])

        if not results:
            return "조회된 이벤트가 없습니다."

        headers = ["timestamp", "event", "distinct_id", "properties"]
        md_table = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
        ]

        for item in results:
            props = item.get("properties", {})
            props_str = json.dumps(props, ensure_ascii=False)[:80] + ("..." if len(json.dumps(props)) > 80 else "")
            row = [
                str(item.get("timestamp", "")),
                str(item.get("event", "")),
                str(item.get("distinct_id", "")),
                props_str,
            ]
            md_table.append("| " + " | ".join(row) + " |")

        return "\n".join(md_table)

    except httpx.RequestError as e:
        logger.error("PostHog 네트워크 오류: %s", e)
        return f"[ERROR] PostHog 네트워크 오류: {e}"
    except Exception as e:
        logger.error("PostHog 이벤트 조회 예외: %s", e)
        return f"[ERROR] PostHog 이벤트 조회 중 예외 발생: {e}"


def get_posthog_insights(conn_id: str, insight_id: Optional[int] = None) -> str:
    """[PostHog] 저장된 인사이트 조회.

    Args:
        conn_id: 연결 식별자
        insight_id: 조회할 인사이트 ID (생략 시 목록 반환)

    Returns:
        인사이트 정보 (마크다운)
    """
    if conn_id not in _posthog_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_posthog()를 먼저 호출하세요."

    creds = _posthog_connections[conn_id]

    if insight_id is not None:
        url = f"{creds['host']}/api/projects/{creds['project_id']}/insights/{insight_id}/"
    else:
        url = f"{creds['host']}/api/projects/{creds['project_id']}/insights/"

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                url,
                headers={"Authorization": f"Bearer {creds['api_key']}"},
            )

        if resp.status_code == 401:
            return "[ERROR] PostHog 인증 실패: connect_posthog()로 키를 다시 등록하세요."
        if resp.status_code == 404:
            return f"[ERROR] 인사이트 ID '{insight_id}'를 찾을 수 없습니다."
        if resp.status_code != 200:
            return f"[ERROR] PostHog 인사이트 조회 실패: HTTP {resp.status_code} - {resp.text}"

        data = resp.json()

        if insight_id is not None:
            lines = [
                f"## 인사이트: {data.get('name', '(이름 없음)')}",
                f"- **ID**: {data.get('id')}",
                f"- **타입**: {data.get('filters', {}).get('insight', 'N/A')}",
                f"- **생성일**: {data.get('created_at', 'N/A')}",
                f"- **설명**: {data.get('description', '')}",
            ]
            return "\n".join(lines)

        results = data.get("results", [])
        if not results:
            return "저장된 인사이트가 없습니다."

        headers = ["id", "name", "type", "created_at"]
        md_table = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
        ]
        for item in results:
            row = [
                str(item.get("id", "")),
                str(item.get("name", "")),
                str(item.get("filters", {}).get("insight", "N/A")),
                str(item.get("created_at", "")),
            ]
            md_table.append("| " + " | ".join(row) + " |")

        return "\n".join(md_table)

    except httpx.RequestError as e:
        logger.error("PostHog 네트워크 오류: %s", e)
        return f"[ERROR] PostHog 네트워크 오류: {e}"
    except Exception as e:
        logger.error("PostHog 인사이트 조회 예외: %s", e)
        return f"[ERROR] PostHog 인사이트 조회 중 예외 발생: {e}"


def get_posthog_feature_flags(conn_id: str) -> str:
    """[PostHog] 피처플래그 목록 및 상태 조회.

    Args:
        conn_id: 연결 식별자

    Returns:
        피처플래그 목록 (마크다운 테이블)
    """
    if conn_id not in _posthog_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_posthog()를 먼저 호출하세요."

    creds = _posthog_connections[conn_id]
    url = f"{creds['host']}/api/projects/{creds['project_id']}/feature_flags/"

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                url,
                headers={"Authorization": f"Bearer {creds['api_key']}"},
            )

        if resp.status_code == 401:
            return "[ERROR] PostHog 인증 실패: connect_posthog()로 키를 다시 등록하세요."
        if resp.status_code != 200:
            return f"[ERROR] PostHog 피처플래그 조회 실패: HTTP {resp.status_code} - {resp.text}"

        data = resp.json()
        results = data.get("results", [])

        if not results:
            return "등록된 피처플래그가 없습니다."

        headers = ["id", "key", "name", "active", "rollout_percentage"]
        md_table = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
        ]
        for flag in results:
            filters = flag.get("filters", {})
            groups = filters.get("groups", [{}])
            rollout = groups[0].get("rollout_percentage", "N/A") if groups else "N/A"
            row = [
                str(flag.get("id", "")),
                str(flag.get("key", "")),
                str(flag.get("name", "")),
                str(flag.get("active", False)),
                str(rollout),
            ]
            md_table.append("| " + " | ".join(row) + " |")

        return "\n".join(md_table)

    except httpx.RequestError as e:
        logger.error("PostHog 네트워크 오류: %s", e)
        return f"[ERROR] PostHog 네트워크 오류: {e}"
    except Exception as e:
        logger.error("PostHog 피처플래그 조회 예외: %s", e)
        return f"[ERROR] PostHog 피처플래그 조회 중 예외 발생: {e}"


def get_posthog_experiments(conn_id: str) -> str:
    """[PostHog] A/B 실험 목록 및 결과 조회.

    Args:
        conn_id: 연결 식별자

    Returns:
        실험 목록 (마크다운 테이블)
    """
    if conn_id not in _posthog_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_posthog()를 먼저 호출하세요."

    creds = _posthog_connections[conn_id]
    url = f"{creds['host']}/api/projects/{creds['project_id']}/experiments/"

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                url,
                headers={"Authorization": f"Bearer {creds['api_key']}"},
            )

        if resp.status_code == 401:
            return "[ERROR] PostHog 인증 실패: connect_posthog()로 키를 다시 등록하세요."
        if resp.status_code != 200:
            return f"[ERROR] PostHog 실험 조회 실패: HTTP {resp.status_code} - {resp.text}"

        data = resp.json()
        results = data.get("results", [])

        if not results:
            return "등록된 실험이 없습니다."

        headers = ["id", "name", "status", "start_date", "end_date", "feature_flag_key"]
        md_table = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
        ]
        for exp in results:
            row = [
                str(exp.get("id", "")),
                str(exp.get("name", "")),
                str(exp.get("status", "")),
                str(exp.get("start_date", "")),
                str(exp.get("end_date", "")),
                str(exp.get("feature_flag_key", "")),
            ]
            md_table.append("| " + " | ".join(row) + " |")

        return "\n".join(md_table)

    except httpx.RequestError as e:
        logger.error("PostHog 네트워크 오류: %s", e)
        return f"[ERROR] PostHog 네트워크 오류: {e}"
    except Exception as e:
        logger.error("PostHog 실험 조회 예외: %s", e)
        return f"[ERROR] PostHog 실험 조회 중 예외 발생: {e}"
