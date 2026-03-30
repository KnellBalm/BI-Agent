"""
Tableau Server/Cloud REST API 연동 도구.
"""
import csv
import io
import logging
import xml.etree.ElementTree as ET
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_tableau_server_connections: dict = {}
# {conn_id: {"server_url": ..., "token": ..., "site_id": ..., "api_version": "3.21"}}

_TABLEAU_NS = "http://tableau.com/api"


def _api_url(conn_id: str, path: str) -> str:
    c = _tableau_server_connections[conn_id]
    return f"{c['server_url']}/api/{c['api_version']}{path}"


def _auth_headers(conn_id: str) -> dict:
    return {"X-Tableau-Auth": _tableau_server_connections[conn_id]["token"]}


def connect_tableau_server(
    server_url: str,
    username: str,
    password: str,
    site_id: str = "",
    api_version: str = "3.21",
    conn_id: str = "default",
) -> str:
    """[Tableau] Tableau Server/Cloud 연결 및 인증 토큰 획득.

    Args:
        server_url: Tableau Server URL (예: https://tableau.company.com)
        username: Tableau 사용자명
        password: Tableau 비밀번호
        site_id: 사이트 ID (기본값 "" = 기본 사이트)
        api_version: REST API 버전 (기본값 3.21)
        conn_id: 연결 식별자
    """
    server_url = server_url.rstrip("/")
    signin_url = f"{server_url}/api/{api_version}/auth/signin"
    body = (
        f"<tsRequest>"
        f'<credentials name="{username}" password="{password}">'
        f'<site contentUrl="{site_id}" />'
        f"</credentials>"
        f"</tsRequest>"
    )
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                signin_url,
                content=body,
                headers={"Content-Type": "application/xml"},
            )
        if resp.status_code == 401:
            return "[ERROR] Tableau 인증 실패: 사용자명 또는 비밀번호를 확인하세요."
        if resp.status_code != 200:
            return f"[ERROR] Tableau 연결 실패: HTTP {resp.status_code} — {resp.text}"

        root = ET.fromstring(resp.text)
        ns = {"t": _TABLEAU_NS}
        creds_el = root.find(".//t:credentials", ns)
        site_el = root.find(".//t:site", ns)
        if creds_el is None:
            return "[ERROR] Tableau 응답에서 인증 토큰을 찾을 수 없습니다."

        token = creds_el.get("token", "")
        resolved_site_id = site_el.get("id", "") if site_el is not None else ""

        _tableau_server_connections[conn_id] = {
            "server_url": server_url,
            "token": token,
            "site_id": resolved_site_id,
            "api_version": api_version,
        }
        return f"[SUCCESS] Tableau Server 연결 성공 (conn_id='{conn_id}', site_id='{resolved_site_id}')"

    except ET.ParseError as e:
        return f"[ERROR] Tableau 응답 XML 파싱 실패: {e}"
    except httpx.RequestError as e:
        return f"[ERROR] Tableau 네트워크 오류: {e}"
    except Exception as e:
        return f"[ERROR] Tableau 연결 중 예외 발생: {e}"


def list_tableau_workbooks(conn_id: str = "default", page_size: int = 100) -> str:
    """[Tableau] 현재 사이트의 워크북 목록 조회.

    Args:
        conn_id: 연결 식별자
        page_size: 한 번에 가져올 최대 워크북 수 (기본값 100)

    Returns:
        워크북 목록 마크다운 테이블
    """
    if conn_id not in _tableau_server_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    c = _tableau_server_connections[conn_id]
    url = _api_url(conn_id, f"/sites/{c['site_id']}/workbooks")
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                url,
                headers=_auth_headers(conn_id),
                params={"pageSize": page_size},
            )
        if resp.status_code != 200:
            return f"[ERROR] 워크북 목록 조회 실패: HTTP {resp.status_code} — {resp.text}"

        root = ET.fromstring(resp.text)
        ns = {"t": _TABLEAU_NS}
        workbooks = root.findall(".//t:workbook", ns)
        if not workbooks:
            return "워크북이 없습니다."

        lines = [
            "| ID | 이름 | 프로젝트 | 소유자 | 최근 수정 |",
            "| --- | --- | --- | --- | --- |",
        ]
        for wb in workbooks:
            wb_id = wb.get("id", "")
            name = wb.get("name", "")
            project = wb.find("t:project", ns)
            project_name = project.get("name", "") if project is not None else ""
            owner = wb.find("t:owner", ns)
            owner_name = owner.get("name", "") if owner is not None else ""
            updated = wb.get("updatedAt", "")
            lines.append(f"| {wb_id} | {name} | {project_name} | {owner_name} | {updated} |")

        return "\n".join(lines)

    except ET.ParseError as e:
        return f"[ERROR] 응답 XML 파싱 실패: {e}"
    except httpx.RequestError as e:
        return f"[ERROR] 네트워크 오류: {e}"
    except Exception as e:
        return f"[ERROR] 워크북 목록 조회 중 예외 발생: {e}"


def list_tableau_views(conn_id: str, workbook_id: str) -> str:
    """[Tableau] 워크북의 뷰(시트) 목록 조회.

    Args:
        conn_id: 연결 식별자
        workbook_id: Tableau 워크북 ID

    Returns:
        뷰 목록 마크다운 테이블
    """
    if conn_id not in _tableau_server_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    c = _tableau_server_connections[conn_id]
    url = _api_url(conn_id, f"/sites/{c['site_id']}/workbooks/{workbook_id}/views")
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, headers=_auth_headers(conn_id))
        if resp.status_code != 200:
            return f"[ERROR] 뷰 목록 조회 실패: HTTP {resp.status_code} — {resp.text}"

        root = ET.fromstring(resp.text)
        ns = {"t": _TABLEAU_NS}
        views = root.findall(".//t:view", ns)
        if not views:
            return f"워크북 '{workbook_id}'에 뷰가 없습니다."

        lines = [
            "| ID | 이름 | 콘텐츠 URL |",
            "| --- | --- | --- |",
        ]
        for view in views:
            view_id = view.get("id", "")
            name = view.get("name", "")
            content_url = view.get("contentUrl", "")
            lines.append(f"| {view_id} | {name} | {content_url} |")

        return "\n".join(lines)

    except ET.ParseError as e:
        return f"[ERROR] 응답 XML 파싱 실패: {e}"
    except httpx.RequestError as e:
        return f"[ERROR] 네트워크 오류: {e}"
    except Exception as e:
        return f"[ERROR] 뷰 목록 조회 중 예외 발생: {e}"


def get_tableau_view_data(conn_id: str, view_id: str, max_rows: int = 500) -> str:
    """[Tableau] 뷰 데이터를 CSV로 가져와 마크다운 테이블 반환.

    Args:
        conn_id: 연결 식별자
        view_id: Tableau 뷰 ID
        max_rows: 최대 반환 행 수 (기본값 500)

    Returns:
        뷰 데이터 마크다운 테이블
    """
    if conn_id not in _tableau_server_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    c = _tableau_server_connections[conn_id]
    url = _api_url(conn_id, f"/sites/{c['site_id']}/views/{view_id}/data.csv")
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                url,
                headers=_auth_headers(conn_id),
                params={"maxRows": max_rows},
            )
        if resp.status_code != 200:
            return f"[ERROR] 뷰 데이터 조회 실패: HTTP {resp.status_code} — {resp.text}"

        reader = csv.reader(io.StringIO(resp.text))
        rows = list(reader)
        if not rows:
            return f"뷰 '{view_id}'에 데이터가 없습니다."

        headers = rows[0]
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
        ]
        for row in rows[1:max_rows + 1]:
            lines.append("| " + " | ".join(row) + " |")

        return "\n".join(lines)

    except httpx.RequestError as e:
        return f"[ERROR] 네트워크 오류: {e}"
    except Exception as e:
        return f"[ERROR] 뷰 데이터 조회 중 예외 발생: {e}"


def refresh_tableau_datasource(conn_id: str, datasource_id: str) -> str:
    """[Tableau] 데이터소스 새로고침(Extract Refresh) 트리거.

    Args:
        conn_id: 연결 식별자
        datasource_id: Tableau 데이터소스 ID

    Returns:
        새로고침 작업 상태 메시지
    """
    if conn_id not in _tableau_server_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    c = _tableau_server_connections[conn_id]
    url = _api_url(conn_id, f"/sites/{c['site_id']}/datasources/{datasource_id}/refresh")
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                url,
                headers={**_auth_headers(conn_id), "Content-Type": "application/xml"},
                content="<tsRequest />",
            )
        if resp.status_code == 404:
            return f"[ERROR] 데이터소스 '{datasource_id}'를 찾을 수 없습니다."
        if resp.status_code not in (200, 202):
            return f"[ERROR] 데이터소스 새로고침 실패: HTTP {resp.status_code} — {resp.text}"

        try:
            root = ET.fromstring(resp.text)
            ns = {"t": _TABLEAU_NS}
            job_el = root.find(".//t:job", ns)
            if job_el is not None:
                job_id = job_el.get("id", "")
                job_status = job_el.get("status", "")
                return f"[SUCCESS] 데이터소스 새로고침 작업 시작 (job_id='{job_id}', status='{job_status}')"
        except ET.ParseError:
            pass

        return f"[SUCCESS] 데이터소스 '{datasource_id}' 새로고침 요청 완료"

    except httpx.RequestError as e:
        return f"[ERROR] 네트워크 오류: {e}"
    except Exception as e:
        return f"[ERROR] 데이터소스 새로고침 중 예외 발생: {e}"
