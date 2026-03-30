"""
Power BI REST API 연동 도구.
"""
import json
import logging

import httpx

logger = logging.getLogger(__name__)

_powerbi_connections: dict = {}
# {conn_id: {"token": ..., "token_type": "Bearer"}}

POWERBI_BASE = "https://api.powerbi.com/v1.0/myorg"


def connect_powerbi(
    client_id: str,
    client_secret: str,
    tenant_id: str,
    conn_id: str = "default",
) -> str:
    """[PowerBI] Power BI REST API 연결 (Azure AD OAuth2 클라이언트 자격증명).

    Args:
        client_id: Azure AD 앱 클라이언트 ID
        client_secret: 클라이언트 시크릿
        tenant_id: Azure AD 테넌트 ID
        conn_id: 연결 식별자

    Returns:
        연결 상태 메시지
    """
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://analysis.windows.net/powerbi/api/.default",
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(token_url, data=data)

        if resp.status_code == 401:
            return "[ERROR] Azure AD 인증 실패: client_id/client_secret/tenant_id를 확인하세요."
        if resp.status_code != 200:
            return f"[ERROR] 토큰 발급 실패: HTTP {resp.status_code} - {resp.text}"

        token_data = resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            return "[ERROR] 응답에 access_token이 없습니다."

        _powerbi_connections[conn_id] = {
            "token": access_token,
            "token_type": token_data.get("token_type", "Bearer"),
        }
        return f"[SUCCESS] Power BI 연결 성공 (conn_id='{conn_id}')"

    except httpx.RequestError as e:
        return f"[ERROR] 네트워크 오류: {e}"
    except Exception as e:
        return f"[ERROR] 연결 중 예외 발생: {e}"


def _auth_headers(conn_id: str) -> tuple[dict, str]:
    """연결 ID에서 Authorization 헤더를 반환. (headers, error_msg)"""
    if conn_id not in _powerbi_connections:
        return {}, f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_powerbi()를 먼저 호출하세요."
    creds = _powerbi_connections[conn_id]
    headers = {"Authorization": f"{creds['token_type']} {creds['token']}"}
    return headers, ""


def list_powerbi_workspaces(conn_id: str = "default") -> str:
    """[PowerBI] Power BI 워크스페이스(그룹) 목록 조회.

    Args:
        conn_id: 연결 식별자

    Returns:
        워크스페이스 목록 마크다운
    """
    headers, err = _auth_headers(conn_id)
    if err:
        return err

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{POWERBI_BASE}/groups", headers=headers)

        if resp.status_code == 401:
            return "[ERROR] 인증 만료: connect_powerbi()로 재연결하세요."
        if resp.status_code != 200:
            return f"[ERROR] 워크스페이스 조회 실패: HTTP {resp.status_code} - {resp.text}"

        workspaces = resp.json().get("value", [])
        if not workspaces:
            return "워크스페이스가 없습니다."

        lines = [
            f"## Power BI 워크스페이스 ({len(workspaces)}개)",
            "",
            "| ID | 이름 | 타입 |",
            "| --- | --- | --- |",
        ]
        for ws in workspaces:
            ws_id = ws.get("id", "")
            ws_name = ws.get("name", "")
            ws_type = ws.get("type", "")
            lines.append(f"| {ws_id} | {ws_name} | {ws_type} |")

        return "\n".join(lines)

    except httpx.RequestError as e:
        return f"[ERROR] 네트워크 오류: {e}"
    except Exception as e:
        return f"[ERROR] 워크스페이스 조회 중 예외 발생: {e}"


def list_powerbi_reports(conn_id: str, workspace_id: str) -> str:
    """[PowerBI] 워크스페이스의 보고서 목록 조회.

    Args:
        conn_id: 연결 식별자
        workspace_id: 워크스페이스(그룹) ID

    Returns:
        보고서 목록 마크다운
    """
    headers, err = _auth_headers(conn_id)
    if err:
        return err

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                f"{POWERBI_BASE}/groups/{workspace_id}/reports",
                headers=headers,
            )

        if resp.status_code == 401:
            return "[ERROR] 인증 만료: connect_powerbi()로 재연결하세요."
        if resp.status_code == 404:
            return f"[ERROR] 워크스페이스 '{workspace_id}'를 찾을 수 없습니다."
        if resp.status_code != 200:
            return f"[ERROR] 보고서 조회 실패: HTTP {resp.status_code} - {resp.text}"

        reports = resp.json().get("value", [])
        if not reports:
            return f"워크스페이스 '{workspace_id}'에 보고서가 없습니다."

        lines = [
            f"## Power BI 보고서 ({len(reports)}개) — 워크스페이스: {workspace_id}",
            "",
            "| ID | 이름 | 데이터셋 ID |",
            "| --- | --- | --- |",
        ]
        for rpt in reports:
            rpt_id = rpt.get("id", "")
            rpt_name = rpt.get("name", "")
            dataset_id = rpt.get("datasetId", "")
            lines.append(f"| {rpt_id} | {rpt_name} | {dataset_id} |")

        return "\n".join(lines)

    except httpx.RequestError as e:
        return f"[ERROR] 네트워크 오류: {e}"
    except Exception as e:
        return f"[ERROR] 보고서 조회 중 예외 발생: {e}"


def get_powerbi_dataset_tables(
    conn_id: str, workspace_id: str, dataset_id: str
) -> str:
    """[PowerBI] 데이터셋의 테이블 목록 조회.

    Args:
        conn_id: 연결 식별자
        workspace_id: 워크스페이스(그룹) ID
        dataset_id: 데이터셋 ID

    Returns:
        테이블 목록 마크다운
    """
    headers, err = _auth_headers(conn_id)
    if err:
        return err

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                f"{POWERBI_BASE}/groups/{workspace_id}/datasets/{dataset_id}/tables",
                headers=headers,
            )

        if resp.status_code == 401:
            return "[ERROR] 인증 만료: connect_powerbi()로 재연결하세요."
        if resp.status_code == 404:
            return f"[ERROR] 데이터셋 '{dataset_id}'을 찾을 수 없습니다."
        if resp.status_code != 200:
            return f"[ERROR] 테이블 조회 실패: HTTP {resp.status_code} - {resp.text}"

        tables = resp.json().get("value", [])
        if not tables:
            return f"데이터셋 '{dataset_id}'에 테이블이 없습니다."

        lines = [
            f"## Power BI 데이터셋 테이블 ({len(tables)}개) — dataset: {dataset_id}",
            "",
            "| 테이블명 | 컬럼 수 |",
            "| --- | --- |",
        ]
        for tbl in tables:
            tbl_name = tbl.get("name", "")
            columns = tbl.get("columns", [])
            lines.append(f"| {tbl_name} | {len(columns)} |")

        return "\n".join(lines)

    except httpx.RequestError as e:
        return f"[ERROR] 네트워크 오류: {e}"
    except Exception as e:
        return f"[ERROR] 테이블 조회 중 예외 발생: {e}"


def push_powerbi_rows(
    conn_id: str,
    workspace_id: str,
    dataset_id: str,
    table_name: str,
    rows_json: str,
) -> str:
    """[PowerBI] Push 데이터셋 테이블에 행 추가.

    Args:
        conn_id: 연결 식별자
        workspace_id: 워크스페이스(그룹) ID
        dataset_id: Push 데이터셋 ID
        table_name: 대상 테이블명
        rows_json: JSON 배열 문자열 (예: '[{"col": val}, ...]')

    Returns:
        처리 결과 메시지
    """
    headers, err = _auth_headers(conn_id)
    if err:
        return err

    try:
        rows = json.loads(rows_json)
    except (json.JSONDecodeError, ValueError) as e:
        return f"[ERROR] rows_json이 유효한 JSON 배열이 아닙니다: {e}"

    if not isinstance(rows, list):
        return "[ERROR] rows_json은 JSON 배열이어야 합니다 (예: [{...}, {...}])."

    try:
        headers["Content-Type"] = "application/json"
        body = {"rows": rows}

        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                f"{POWERBI_BASE}/groups/{workspace_id}/datasets/{dataset_id}/tables/{table_name}/rows",
                headers=headers,
                json=body,
            )

        if resp.status_code == 401:
            return "[ERROR] 인증 만료: connect_powerbi()로 재연결하세요."
        if resp.status_code == 404:
            return f"[ERROR] 테이블 '{table_name}' 또는 데이터셋 '{dataset_id}'을 찾을 수 없습니다."
        if resp.status_code not in (200, 201):
            return f"[ERROR] 행 추가 실패: HTTP {resp.status_code} - {resp.text}"

        return f"[SUCCESS] {len(rows)}개 행을 테이블 '{table_name}'에 추가했습니다."

    except httpx.RequestError as e:
        return f"[ERROR] 네트워크 오류: {e}"
    except Exception as e:
        return f"[ERROR] 행 추가 중 예외 발생: {e}"
