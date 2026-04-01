"""
Airbyte 연동 도구.
"""
import json
import logging
from typing import Dict

import httpx

logger = logging.getLogger(__name__)

# 메모리 캐시: {conn_id: {"url": ..., "username": ..., "password": ...}}
_airbyte_connections: Dict[str, dict] = {}


def connect_airbyte(
    url: str,
    username: str,
    password: str,
    conn_id: str = "default",
) -> str:
    """[Airbyte] Airbyte 서버 연결 및 상태 검증.

    Args:
        url: Airbyte 서버 URL (예: http://localhost:8000)
        username: Basic Auth 사용자명
        password: Basic Auth 비밀번호
        conn_id: 연결 식별자 (기본값: "default")

    Returns:
        상태 메시지
    """
    url = url.rstrip("/")
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                f"{url}/api/v1/health",
                auth=(username, password),
            )
        if resp.status_code == 401:
            return "[ERROR] Airbyte 인증 실패: username 또는 password를 확인하세요."
        if resp.status_code == 400:
            return f"[ERROR] Airbyte 요청 오류: {resp.text}"
        if resp.status_code != 200:
            return f"[ERROR] Airbyte 연결 실패: HTTP {resp.status_code}"

    except httpx.RequestError as e:
        return f"[ERROR] Airbyte 연결 중 네트워크 오류: {e}"

    _airbyte_connections[conn_id] = {"url": url, "username": username, "password": password}
    return f"[SUCCESS] Airbyte 연결 성공 (conn_id={conn_id})"


def list_airbyte_sources(
    conn_id: str,
    workspace_id: str,
) -> str:
    """[Airbyte] Workspace의 Sources 목록 조회.

    Args:
        conn_id: 연결 식별자
        workspace_id: Airbyte Workspace ID

    Returns:
        Sources 목록 (JSON)
    """
    if conn_id not in _airbyte_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_airbyte()를 먼저 호출하세요."

    creds = _airbyte_connections[conn_id]
    url = creds["url"]
    auth = (creds["username"], creds["password"])

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                f"{url}/api/v1/sources/list",
                auth=auth,
                json={"workspaceId": workspace_id},
            )

        if resp.status_code == 401:
            return "[ERROR] Airbyte 인증 만료: connect_airbyte()로 재연결하세요."
        if resp.status_code == 404:
            return f"[ERROR] Workspace ID '{workspace_id}'를 찾을 수 없습니다."
        if resp.status_code != 200:
            return f"[ERROR] Sources 목록 조회 실패: HTTP {resp.status_code}"

        data = resp.json()
        sources = data.get("sources", [])

        if not sources:
            return json.dumps({"sources": [], "total": 0}, ensure_ascii=False, indent=2)

        result = {
            "sources": [
                {
                    "sourceId": s.get("sourceId", ""),
                    "name": s.get("name", ""),
                    "sourceName": s.get("sourceName", ""),
                    "connectionConfiguration": s.get("connectionConfiguration", {}),
                }
                for s in sources
            ],
            "total": len(sources),
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    except httpx.RequestError as e:
        return f"[ERROR] Sources 목록 조회 중 네트워크 오류: {e}"
    except Exception as e:
        logger.error("Airbyte sources 조회 예외: %s", e)
        return f"[ERROR] Sources 목록 조회 중 예외 발생: {e}"


def list_airbyte_connections(
    conn_id: str,
    workspace_id: str,
) -> str:
    """[Airbyte] Workspace의 Connections 목록 조회.

    Args:
        conn_id: 연결 식별자
        workspace_id: Airbyte Workspace ID

    Returns:
        Connections 목록 (JSON)
    """
    if conn_id not in _airbyte_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_airbyte()를 먼저 호출하세요."

    creds = _airbyte_connections[conn_id]
    url = creds["url"]
    auth = (creds["username"], creds["password"])

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                f"{url}/api/v1/connections/list",
                auth=auth,
                json={"workspaceId": workspace_id},
            )

        if resp.status_code == 401:
            return "[ERROR] Airbyte 인증 만료: connect_airbyte()로 재연결하세요."
        if resp.status_code == 404:
            return f"[ERROR] Workspace ID '{workspace_id}'를 찾을 수 없습니다."
        if resp.status_code != 200:
            return f"[ERROR] Connections 목록 조회 실패: HTTP {resp.status_code}"

        data = resp.json()
        connections = data.get("connections", [])

        if not connections:
            return json.dumps({"connections": [], "total": 0}, ensure_ascii=False, indent=2)

        result = {
            "connections": [
                {
                    "connectionId": c.get("connectionId", ""),
                    "name": c.get("name", ""),
                    "status": c.get("status", ""),
                    "sourceId": c.get("sourceId", ""),
                    "destinationId": c.get("destinationId", ""),
                    "syncCatalog": c.get("syncCatalog", {}),
                }
                for c in connections
            ],
            "total": len(connections),
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    except httpx.RequestError as e:
        return f"[ERROR] Connections 목록 조회 중 네트워크 오류: {e}"
    except Exception as e:
        logger.error("Airbyte connections 조회 예외: %s", e)
        return f"[ERROR] Connections 목록 조회 중 예외 발생: {e}"


def get_airbyte_sync_status(
    conn_id: str,
    connection_id: str,
    limit: int = 5,
) -> str:
    """[Airbyte] Connection의 최근 sync job 상태 조회.

    Args:
        conn_id: 연결 식별자
        connection_id: Airbyte Connection ID
        limit: 조회할 최근 job 수 (기본값: 5)

    Returns:
        최근 sync job 상태 (JSON)
    """
    if conn_id not in _airbyte_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_airbyte()를 먼저 호출하세요."

    creds = _airbyte_connections[conn_id]
    url = creds["url"]
    auth = (creds["username"], creds["password"])

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                f"{url}/api/v1/jobs/list",
                auth=auth,
                json={
                    "configTypes": ["sync"],
                    "configId": connection_id,
                    "pagination": {"pageSize": limit, "rowOffset": 0},
                },
            )

        if resp.status_code == 401:
            return "[ERROR] Airbyte 인증 만료: connect_airbyte()로 재연결하세요."
        if resp.status_code == 404:
            return f"[ERROR] Connection ID '{connection_id}'를 찾을 수 없습니다."
        if resp.status_code != 200:
            return f"[ERROR] Sync 상태 조회 실패: HTTP {resp.status_code}"

        data = resp.json()
        jobs = data.get("jobs", [])

        if not jobs:
            return json.dumps({"jobs": [], "total": 0}, ensure_ascii=False, indent=2)

        result = {
            "jobs": [
                {
                    "jobId": j.get("job", {}).get("id", ""),
                    "status": j.get("job", {}).get("status", ""),
                    "configType": j.get("job", {}).get("configType", ""),
                    "createdAt": j.get("job", {}).get("createdAt", ""),
                    "updatedAt": j.get("job", {}).get("updatedAt", ""),
                    "bytesSynced": j.get("attempts", [{}])[-1].get("summary", {}).get("bytesCommitted", 0) if j.get("attempts") else 0,
                    "recordsSynced": j.get("attempts", [{}])[-1].get("summary", {}).get("recordsCommitted", 0) if j.get("attempts") else 0,
                }
                for j in jobs
            ],
            "total": len(jobs),
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    except httpx.RequestError as e:
        return f"[ERROR] Sync 상태 조회 중 네트워크 오류: {e}"
    except Exception as e:
        logger.error("Airbyte sync 상태 조회 예외: %s", e)
        return f"[ERROR] Sync 상태 조회 중 예외 발생: {e}"
