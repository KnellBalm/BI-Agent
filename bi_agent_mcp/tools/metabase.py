"""
Metabase 연동 도구.
"""
import json
import logging
from typing import Dict, Optional

import httpx

logger = logging.getLogger(__name__)

# 메모리 캐시: {conn_id: {"url": ..., "token": ...}}
_metabase_connections: Dict[str, dict] = {}


def connect_metabase(
    url: str,
    username: str,
    password: str,
    conn_id: str = "default",
) -> str:
    """[Metabase] Metabase 서버 연결 및 세션 토큰 획득.

    Args:
        url: Metabase 서버 URL (예: http://localhost:3000)
        username: 로그인 이메일
        password: 로그인 비밀번호
        conn_id: 연결 식별자 (기본값: "default")

    Returns:
        상태 메시지
    """
    url = url.rstrip("/")
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                f"{url}/api/session",
                json={"username": username, "password": password},
            )
        if resp.status_code == 401:
            return "[ERROR] Metabase 인증 실패: username 또는 password를 확인하세요."
        if resp.status_code == 400:
            return f"[ERROR] Metabase 요청 오류: {resp.text}"
        if resp.status_code != 200:
            return f"[ERROR] Metabase 연결 실패: HTTP {resp.status_code}"

        data = resp.json()
        token = data.get("id")
        if not token:
            return "[ERROR] Metabase 응답에서 세션 토큰을 찾을 수 없습니다."

    except httpx.RequestError as e:
        return f"[ERROR] Metabase 연결 중 네트워크 오류: {e}"

    _metabase_connections[conn_id] = {"url": url, "token": token}
    return f"[SUCCESS] Metabase 연결 성공 (conn_id={conn_id})"


def list_metabase_questions(
    conn_id: str,
    collection_id: Optional[int] = None,
) -> str:
    """[Metabase] 저장된 질문(카드) 목록 조회.

    Args:
        conn_id: 연결 식별자
        collection_id: 특정 컬렉션 ID로 필터링 (None이면 전체)

    Returns:
        카드 목록 (마크다운 테이블)
    """
    if conn_id not in _metabase_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_metabase()를 먼저 호출하세요."

    creds = _metabase_connections[conn_id]
    url = creds["url"]
    headers = {"X-Metabase-Session": creds["token"]}

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{url}/api/card", headers=headers)

        if resp.status_code == 401:
            return "[ERROR] Metabase 인증 만료: connect_metabase()로 재연결하세요."
        if resp.status_code != 200:
            return f"[ERROR] 질문 목록 조회 실패: HTTP {resp.status_code}"

        cards = resp.json()

        # collection_id 필터
        if collection_id is not None:
            cards = [c for c in cards if c.get("collection_id") == collection_id]

        if not cards:
            return "저장된 질문이 없습니다."

        lines = ["| ID | 이름 | 데이터베이스 | 업데이트 |",
                 "| --- | --- | --- | --- |"]
        for c in cards:
            card_id = c.get("id", "")
            name = c.get("name", "")
            db = (c.get("database_id") or "")
            updated = (c.get("updated_at") or "")[:10]
            lines.append(f"| {card_id} | {name} | {db} | {updated} |")

        return "\n".join(lines)

    except httpx.RequestError as e:
        return f"[ERROR] 질문 목록 조회 중 네트워크 오류: {e}"


def run_metabase_question(
    conn_id: str,
    card_id: int,
    parameters: str = "[]",
) -> str:
    """[Metabase] 저장된 질문 실행 및 데이터 반환.

    Args:
        conn_id: 연결 식별자
        card_id: 실행할 카드(질문) ID
        parameters: 파라미터 JSON 문자열 (기본값: "[]")

    Returns:
        쿼리 결과 (마크다운 테이블)
    """
    if conn_id not in _metabase_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_metabase()를 먼저 호출하세요."

    creds = _metabase_connections[conn_id]
    url = creds["url"]
    headers = {"X-Metabase-Session": creds["token"]}

    try:
        params_parsed = json.loads(parameters)
    except json.JSONDecodeError as e:
        return f"[ERROR] parameters JSON 파싱 실패: {e}"

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{url}/api/card/{card_id}/query/json",
                headers=headers,
                json={"parameters": params_parsed},
            )

        if resp.status_code == 401:
            return "[ERROR] Metabase 인증 만료: connect_metabase()로 재연결하세요."
        if resp.status_code == 404:
            return f"[ERROR] 카드 ID {card_id}를 찾을 수 없습니다."
        if resp.status_code != 200:
            return f"[ERROR] 질문 실행 실패: HTTP {resp.status_code} - {resp.text}"

        rows = resp.json()
        if not rows:
            return "쿼리 결과가 없습니다."

        columns = list(rows[0].keys())
        lines = ["| " + " | ".join(columns) + " |",
                 "| " + " | ".join(["---"] * len(columns)) + " |"]
        for row in rows:
            lines.append("| " + " | ".join(str(row.get(c, "")) for c in columns) + " |")

        return "\n".join(lines)

    except httpx.RequestError as e:
        return f"[ERROR] 질문 실행 중 네트워크 오류: {e}"
    except Exception as e:
        logger.error("Metabase 질문 실행 예외: %s", e)
        return f"[ERROR] 질문 실행 중 예외 발생: {e}"


def list_metabase_dashboards(conn_id: str) -> str:
    """[Metabase] 대시보드 목록 조회.

    Args:
        conn_id: 연결 식별자

    Returns:
        대시보드 목록 (마크다운 테이블)
    """
    if conn_id not in _metabase_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_metabase()를 먼저 호출하세요."

    creds = _metabase_connections[conn_id]
    url = creds["url"]
    headers = {"X-Metabase-Session": creds["token"]}

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{url}/api/dashboard", headers=headers)

        if resp.status_code == 401:
            return "[ERROR] Metabase 인증 만료: connect_metabase()로 재연결하세요."
        if resp.status_code != 200:
            return f"[ERROR] 대시보드 목록 조회 실패: HTTP {resp.status_code}"

        dashboards = resp.json()
        if not dashboards:
            return "저장된 대시보드가 없습니다."

        lines = ["| ID | 이름 | 업데이트 |",
                 "| --- | --- | --- |"]
        for d in dashboards:
            dash_id = d.get("id", "")
            name = d.get("name", "")
            updated = (d.get("updated_at") or "")[:10]
            lines.append(f"| {dash_id} | {name} | {updated} |")

        return "\n".join(lines)

    except httpx.RequestError as e:
        return f"[ERROR] 대시보드 목록 조회 중 네트워크 오류: {e}"
