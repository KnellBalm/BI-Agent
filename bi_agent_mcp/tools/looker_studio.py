"""
Looker Studio (Google Sheets API) 연동 도구.
"""
import json
import logging
from typing import Dict, Optional

import httpx

try:
    from google.oauth2 import service_account as _sa
    _HAS_GOOGLE_AUTH = True
except ImportError:
    _HAS_GOOGLE_AUTH = False

logger = logging.getLogger(__name__)

SHEETS_API_BASE = "https://sheets.googleapis.com/v4/spreadsheets"
LOOKER_STUDIO_BASE = "https://lookerstudio.google.com/reporting"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_looker_studio_connections: Dict[str, dict] = {}


def connect_looker_studio(conn_id: str, credentials_json: str) -> str:
    """[LookerStudio] Google Service Account로 Looker Studio / Google Sheets API 연결.

    Args:
        conn_id: 이 연결에 부여할 식별자
        credentials_json: Service Account JSON 파일 경로 또는 JSON 문자열

    Returns:
        연결 성공/실패 메시지
    """
    if not _HAS_GOOGLE_AUTH:
        return "[ERROR] google-auth 패키지가 필요합니다: pip install google-auth"

    # 파일 경로면 읽기
    raw = credentials_json.strip()
    if not raw.startswith("{"):
        try:
            with open(raw, "r", encoding="utf-8") as f:
                raw = f.read()
        except OSError as e:
            return f"[ERROR] credentials 파일을 읽을 수 없습니다: {e}"

    try:
        cred_info = json.loads(raw)
    except json.JSONDecodeError as e:
        return f"[ERROR] credentials JSON 파싱 실패: {e}"

    try:
        creds = _sa.Credentials.from_service_account_info(cred_info, scopes=SCOPES)
        creds.refresh(httpx.Client())
    except Exception as e:
        return f"[ERROR] Google 인증 실패: {e}"

    _looker_studio_connections[conn_id] = {
        "credentials": creds,
    }
    return f"[SUCCESS] Looker Studio 연결 성공 (conn_id='{conn_id}')"


def _get_access_token(conn_id: str):
    """내부 헬퍼: 유효한 액세스 토큰 반환."""
    if conn_id not in _looker_studio_connections:
        return None, f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."
    creds = _looker_studio_connections[conn_id]["credentials"]
    try:
        from google.auth.transport.requests import Request as _GRequest
        import requests as _req
        creds.refresh(_GRequest(session=_req.Session()))
    except Exception:
        pass
    return creds.token, ""


def get_sheet_data(conn_id: str, spreadsheet_id: str, range_notation: str) -> str:
    """[LookerStudio] Google Sheets 특정 범위 데이터 조회.

    Args:
        conn_id: Looker Studio 연결 ID
        spreadsheet_id: Spreadsheet ID (URL에서 /d/<ID>/ 부분)
        range_notation: A1 표기법 범위 (예: "Sheet1!A1:D50")

    Returns:
        마크다운 테이블
    """
    token, err = _get_access_token(conn_id)
    if err:
        return err

    url = f"{SHEETS_API_BASE}/{spreadsheet_id}/values/{range_notation}"
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, headers={"Authorization": f"Bearer {token}"})
        if resp.status_code == 401:
            return "[ERROR] Google 인증 만료: connect_looker_studio()를 다시 호출하세요."
        if resp.status_code == 403:
            return "[ERROR] 접근 권한 없음: Service Account에 Sheets 읽기 권한을 부여하세요."
        if resp.status_code == 404:
            return f"[ERROR] 스프레드시트를 찾을 수 없습니다: {spreadsheet_id}"
        if resp.status_code != 200:
            return f"[ERROR] Sheets API 오류: HTTP {resp.status_code} - {resp.text}"

        data = resp.json()
        values = data.get("values", [])
        if not values:
            return "데이터가 없습니다."

        headers = values[0]
        rows = values[1:]
        lines = [
            "| " + " | ".join(str(h) for h in headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
        ]
        for row in rows:
            padded = list(row) + [""] * (len(headers) - len(row))
            lines.append("| " + " | ".join(str(c) for c in padded) + " |")

        return "\n".join(lines)

    except httpx.RequestError as e:
        return f"[ERROR] 네트워크 오류: {e}"
    except Exception as e:
        return f"[ERROR] 데이터 조회 중 예외 발생: {e}"


def list_sheets(conn_id: str, spreadsheet_id: str) -> str:
    """[LookerStudio] Google Spreadsheet 내 시트(탭) 목록 조회.

    Args:
        conn_id: Looker Studio 연결 ID
        spreadsheet_id: Spreadsheet ID

    Returns:
        시트 목록 마크다운
    """
    token, err = _get_access_token(conn_id)
    if err:
        return err

    url = f"{SHEETS_API_BASE}/{spreadsheet_id}"
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                url,
                params={"fields": "sheets.properties"},
                headers={"Authorization": f"Bearer {token}"},
            )
        if resp.status_code == 401:
            return "[ERROR] Google 인증 만료: connect_looker_studio()를 다시 호출하세요."
        if resp.status_code == 404:
            return f"[ERROR] 스프레드시트를 찾을 수 없습니다: {spreadsheet_id}"
        if resp.status_code != 200:
            return f"[ERROR] Sheets API 오류: HTTP {resp.status_code}"

        sheets = resp.json().get("sheets", [])
        if not sheets:
            return "시트가 없습니다."

        lines = [f"## 스프레드시트 시트 목록 ({len(sheets)}개)", ""]
        for s in sheets:
            props = s.get("properties", {})
            idx = props.get("index", "?")
            title = props.get("title", "Unknown")
            row_count = props.get("gridProperties", {}).get("rowCount", "?")
            col_count = props.get("gridProperties", {}).get("columnCount", "?")
            lines.append(f"- [{idx}] **{title}** ({row_count}행 × {col_count}열)")

        return "\n".join(lines)

    except httpx.RequestError as e:
        return f"[ERROR] 네트워크 오류: {e}"
    except Exception as e:
        return f"[ERROR] 시트 목록 조회 중 예외 발생: {e}"


def append_sheet_data(conn_id: str, spreadsheet_id: str, range_notation: str, values_json: str) -> str:
    """[LookerStudio] Google Sheets에 행 데이터 추가(append).

    Args:
        conn_id: Looker Studio 연결 ID
        spreadsheet_id: Spreadsheet ID
        range_notation: 추가할 범위 (예: "Sheet1!A1")
        values_json: JSON 배열 문자열 (예: '[["val1","val2"],["val3","val4"]]')

    Returns:
        성공/실패 메시지
    """
    token, err = _get_access_token(conn_id)
    if err:
        return err

    try:
        values = json.loads(values_json)
    except json.JSONDecodeError as e:
        return f"[ERROR] values_json 파싱 실패: {e}"

    url = f"{SHEETS_API_BASE}/{spreadsheet_id}/values/{range_notation}:append"
    payload = {"values": values}
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                url,
                json=payload,
                params={"valueInputOption": "USER_ENTERED"},
                headers={"Authorization": f"Bearer {token}"},
            )
        if resp.status_code == 401:
            return "[ERROR] Google 인증 만료: connect_looker_studio()를 다시 호출하세요."
        if resp.status_code == 403:
            return "[ERROR] 쓰기 권한 없음: Service Account에 Sheets 편집 권한을 부여하세요."
        if resp.status_code not in (200, 201):
            return f"[ERROR] 데이터 추가 실패: HTTP {resp.status_code} - {resp.text}"

        result = resp.json()
        updated = result.get("updates", {}).get("updatedRows", "?")
        return f"[SUCCESS] {updated}행이 추가되었습니다."

    except httpx.RequestError as e:
        return f"[ERROR] 네트워크 오류: {e}"
    except Exception as e:
        return f"[ERROR] 데이터 추가 중 예외 발생: {e}"


def get_spreadsheet_metadata(conn_id: str, spreadsheet_id: str) -> str:
    """[LookerStudio] Google Spreadsheet 메타데이터(제목, 시트 수, URL 등) 조회.

    Args:
        conn_id: Looker Studio 연결 ID
        spreadsheet_id: Spreadsheet ID

    Returns:
        메타데이터 마크다운
    """
    token, err = _get_access_token(conn_id)
    if err:
        return err

    url = f"{SHEETS_API_BASE}/{spreadsheet_id}"
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                url,
                params={"fields": "spreadsheetId,properties,sheets.properties"},
                headers={"Authorization": f"Bearer {token}"},
            )
        if resp.status_code == 401:
            return "[ERROR] Google 인증 만료: connect_looker_studio()를 다시 호출하세요."
        if resp.status_code == 404:
            return f"[ERROR] 스프레드시트를 찾을 수 없습니다: {spreadsheet_id}"
        if resp.status_code != 200:
            return f"[ERROR] Sheets API 오류: HTTP {resp.status_code}"

        data = resp.json()
        props = data.get("properties", {})
        title = props.get("title", "Unknown")
        locale = props.get("locale", "?")
        tz = props.get("timeZone", "?")
        sheets = data.get("sheets", [])

        lines = [
            f"## 스프레드시트 메타데이터",
            f"- **ID**: {spreadsheet_id}",
            f"- **제목**: {title}",
            f"- **로케일**: {locale}",
            f"- **타임존**: {tz}",
            f"- **시트 수**: {len(sheets)}개",
        ]
        return "\n".join(lines)

    except httpx.RequestError as e:
        return f"[ERROR] 네트워크 오류: {e}"
    except Exception as e:
        return f"[ERROR] 메타데이터 조회 중 예외 발생: {e}"


# ── 새 명세 호환 alias/추가 함수 ─────────────────────────────────────────────


def list_looker_studio_sheets(conn_id: str, spreadsheet_id: str) -> str:
    """[LookerStudio] 스프레드시트의 시트(탭) 목록 반환.

    Args:
        conn_id: Looker Studio 연결 ID
        spreadsheet_id: Spreadsheet ID

    Returns:
        시트 목록 마크다운
    """
    return list_sheets(conn_id, spreadsheet_id)


def read_looker_studio_sheet(
    conn_id: str,
    spreadsheet_id: str,
    sheet_name: str = "Sheet1",
    limit: int = 500,
) -> str:
    """[LookerStudio] 시트 데이터를 마크다운 테이블로 반환.

    Args:
        conn_id: Looker Studio 연결 ID
        spreadsheet_id: Spreadsheet ID
        sheet_name: 시트 이름 (기본값: "Sheet1")
        limit: 최대 행 수 (기본값: 500)

    Returns:
        마크다운 테이블
    """
    range_notation = f"{sheet_name}!A1:{_col_letter(500)}{limit + 1}"
    return get_sheet_data(conn_id, spreadsheet_id, range_notation)


def _col_letter(n: int) -> str:
    """열 번호를 엑셀 열 문자로 변환 (1→A, 26→Z, 27→AA)."""
    result = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def write_to_looker_studio_sheet(
    conn_id: str,
    spreadsheet_id: str,
    sheet_name: str,
    data_json: str,
    mode: str = "append",
) -> str:
    """[LookerStudio] 시트에 데이터 쓰기 (append 또는 overwrite).

    Args:
        conn_id: Looker Studio 연결 ID
        spreadsheet_id: Spreadsheet ID
        sheet_name: 대상 시트 이름
        data_json: JSON 배열 문자열 (예: '[{"col1": "val1"}, {"col1": "val2"}]')
        mode: "append" 또는 "overwrite"

    Returns:
        성공/실패 메시지
    """
    if mode not in ("append", "overwrite"):
        return f"[ERROR] mode는 'append' 또는 'overwrite'여야 합니다. 입력값: '{mode}'"

    if conn_id not in _looker_studio_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    try:
        records = json.loads(data_json)
    except json.JSONDecodeError as e:
        return f"[ERROR] data_json 파싱 실패: {e}"

    if not isinstance(records, list) or not records:
        return "[ERROR] data_json은 비어있지 않은 JSON 배열이어야 합니다."

    # dict 목록이면 헤더+행 변환, 배열 목록이면 그대로
    if isinstance(records[0], dict):
        headers = list(records[0].keys())
        rows = [headers] + [[str(r.get(h, "")) for h in headers] for r in records]
    else:
        rows = [[str(c) for c in row] for row in records]

    token, err = _get_access_token(conn_id)
    if err:
        return err

    range_notation = f"{sheet_name}!A1"

    if mode == "overwrite":
        # 먼저 clear
        clear_url = f"{SHEETS_API_BASE}/{spreadsheet_id}/values/{sheet_name}:clear"
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(
                    clear_url,
                    headers={"Authorization": f"Bearer {token}"},
                )
            if resp.status_code not in (200, 204):
                return f"[ERROR] 시트 초기화 실패: HTTP {resp.status_code}"
        except httpx.RequestError as e:
            return f"[ERROR] 네트워크 오류 (clear): {e}"

    values_json = json.dumps(rows)
    return append_sheet_data(conn_id, spreadsheet_id, range_notation, values_json)


def create_looker_studio_report_url(
    report_id: str,
    datasource_alias: str = "",
    params_json: str = "{}",
) -> str:
    """[LookerStudio] Looker Studio 보고서 공유 URL 생성 (연결 불필요).

    Args:
        report_id: Looker Studio 보고서 ID
        datasource_alias: 데이터소스 별칭 (선택)
        params_json: 추가 쿼리 파라미터 JSON 문자열 (예: '{"df1": "include%EE%80%800%EE%80%80IN%EE%80%80value"}')

    Returns:
        공유 URL 문자열
    """
    try:
        params = json.loads(params_json)
    except json.JSONDecodeError as e:
        return f"[ERROR] params_json 파싱 실패: {e}"

    from urllib.parse import urlencode, quote

    base_url = f"{LOOKER_STUDIO_BASE}/{quote(report_id, safe='')}/page/1"

    query_parts = {}
    if datasource_alias:
        query_parts["datasource_alias"] = datasource_alias
    query_parts.update({k: v for k, v in params.items() if isinstance(v, str)})

    if query_parts:
        base_url = f"{base_url}?{urlencode(query_parts)}"

    return base_url
