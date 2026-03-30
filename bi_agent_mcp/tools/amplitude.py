"""
Amplitude Data 연동 도구.
"""
import json
import logging
from typing import Dict, List, Optional
import httpx

from bi_agent_mcp.auth.credentials import store_secret, get_env_or_secret

logger = logging.getLogger(__name__)

# 메모리 캐시 (property_id가 아닌 별도의 식별자가 없으므로 'default'로 사용)
_amplitude_connections: Dict[str, dict] = {}

AMPLITUDE_DASHBOARD_API = "https://amplitude.com/api/2"


def connect_amplitude(api_key: Optional[str] = None, secret_key: Optional[str] = None) -> str:
    """[Amplitude] Amplitude API 키 등록 및 연결 확인.
    키를 전달하지 않으면 환경변수 또는 키체인에 저장된 키를 사용.

    Args:
        api_key: Amplitude API Key
        secret_key: Amplitude Secret Key

    Returns:
        상태 메시지
    """
    service_name = "bi-agent-amplitude"

    # 1. 전달받은 키가 있다면 키체인에 저장
    if api_key and secret_key:
        store_secret(service_name, "api_key", api_key)
        store_secret(service_name, "secret_key", secret_key)

    # 2. 사용할 키 획득 (환경변수 우선 -> 키체인 폴백)
    final_api_key = api_key or get_env_or_secret("BI_AGENT_AMPLITUDE_API_KEY", service_name, "api_key")
    final_secret_key = secret_key or get_env_or_secret("BI_AGENT_AMPLITUDE_SECRET_KEY", service_name, "secret_key")

    if not final_api_key or not final_secret_key:
        return "[ERROR] AMPLITUDE API Key와 Secret Key가 필요합니다."

    # 3. 연결 테스트
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{AMPLITUDE_DASHBOARD_API}/events/list",
                auth=(final_api_key, final_secret_key),
            )
        if resp.status_code == 401:
            return "[ERROR] Amplitude 인증 실패: API Key 또는 Secret Key를 확인하세요."
        if resp.status_code not in (200, 204):
            return f"[ERROR] Amplitude 연결 테스트 실패: HTTP {resp.status_code}"
    except httpx.RequestError as e:
        return f"[ERROR] Amplitude 연결 중 네트워크 오류: {e}"

    # 4. 메모리 상에 등록
    _amplitude_connections["default"] = {
        "api_key": final_api_key,
        "secret_key": final_secret_key,
    }

    return "[SUCCESS] Amplitude 연결 성공"


def get_amplitude_events(
    event_name: str,
    start_date: str,
    end_date: str,
    group_by: Optional[str] = None
) -> str:
    """
    [Amplitude] Amplitude Event Segmentation API 호출을 통해 지표 조회.

    Args:
        event_name: 분석할 이벤트 이름 (예: "Purchase")
        start_date: YYYYMMDD 형태의 시작일 (예: 20260301)
        end_date: YYYYMMDD 형태의 종료일 (예: 20260315)
        group_by: 속성(Property)별로 그룹화할 필드명 (Optional)

    Returns:
        마크다운 테이블
    """
    if "default" not in _amplitude_connections:
        return "[ERROR] 먼저 connect_amplitude() 를 호출하여 키를 등록하세요."

    creds = _amplitude_connections["default"]

    try:
        url = f"{AMPLITUDE_DASHBOARD_API}/events/segmentation"

        params = {
            "e": json.dumps({"event_type": event_name}),
            "start": start_date,
            "end": end_date,
            "m": "uniques",
            "i": 1,
        }
        if group_by:
            params["s"] = json.dumps([{"type": "event", "value": group_by}])

        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                url,
                params=params,
                auth=(creds["api_key"], creds["secret_key"])
            )

            if resp.status_code == 401:
                return "[ERROR] Amplitude 인증 실패: connect_amplitude()로 키를 다시 등록하세요."
            if resp.status_code == 429:
                return "[ERROR] Amplitude API Rate Limit 초과: 잠시 후 다시 시도하세요."
            if resp.status_code == 400:
                return f"[ERROR] 잘못된 파라미터: {resp.text}"
            if resp.status_code != 200:
                return f"[ERROR] Amplitude API 호출 실패: HTTP {resp.status_code} - {resp.text}"

            data = resp.json()

            if "data" not in data or "series" not in data["data"]:
                return "Amplitude에서 반환된 데이터 포맷이 올바르지 않습니다."

            x_values = data["data"].get("xValues", [])
            series = data["data"].get("series", [])
            series_labels = data["data"].get("seriesLabels", [event_name])

            # 마크다운 테이블 생성
            headers = ["Date"] + [str(label) for label in series_labels]
            md_table = [
                "| " + " | ".join(headers) + " |",
                "| " + " | ".join(["---"] * len(headers)) + " |",
            ]

            for i, date_val in enumerate(x_values):
                row = [str(date_val)]
                for s in series:
                    row.append(str(s[i]) if i < len(s) else "0")
                md_table.append("| " + " | ".join(row) + " |")

            return "\n".join(md_table)

    except httpx.RequestError as e:
        logger.error("Amplitude 네트워크 오류: %s", e)
        return f"[ERROR] Amplitude 네트워크 오류: {e}"
    except Exception as e:
        logger.error("Amplitude 연동 예외 발생: %s", e)
        return f"[ERROR] Amplitude 데이터 조회 중 예외 발생: {e}"


def get_amplitude_funnel(
    conn_id: str,
    events: str,
    start_date: str,
    end_date: str,
) -> str:
    """[Amplitude] 퍼널 분석 — 이벤트 시퀀스별 전환율 계산.

    Args:
        conn_id: Amplitude 연결 ID
        events: JSON 문자열 (예: '[{"event_type": "signup"}, {"event_type": "purchase"}]')
        start_date: YYYYMMDD 형태의 시작일
        end_date: YYYYMMDD 형태의 종료일

    Returns:
        퍼널 단계별 전환율 마크다운
    """
    if conn_id not in _amplitude_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    creds = _amplitude_connections[conn_id]

    try:
        events_list = json.loads(events)
    except (json.JSONDecodeError, ValueError) as e:
        return f"[ERROR] events 파라미터가 유효한 JSON이 아닙니다: {e}"

    try:
        resp = httpx.get(
            f"{AMPLITUDE_DASHBOARD_API}/funnels",
            params={
                "e": json.dumps(events_list),
                "start": start_date,
                "end": end_date,
            },
            auth=(creds["api_key"], creds["secret_key"]),
            timeout=15.0,
        )
        if resp.status_code != 200:
            return f"[ERROR] Amplitude API 오류: {resp.status_code}"

        data = resp.json()
        steps = data.get("data", {}).get("steps", [])
        if not steps:
            return "퍼널 데이터가 없습니다."

        lines = ["| 단계 | 이벤트 | 사용자 수 | 전환율 |", "| --- | --- | --- | --- |"]
        for i, step in enumerate(steps):
            event_name = step.get("event", {}).get("event_type", f"Step {i+1}")
            users = step.get("users", 0)
            rate = step.get("conversionRate", 0)
            lines.append(f"| {i+1} | {event_name} | {users} | {rate:.1%} |")

        return "\n".join(lines)

    except httpx.RequestError as e:
        return f"[ERROR] Amplitude 네트워크 오류: {e}"
    except Exception as e:
        return f"[ERROR] 퍼널 분석 중 예외 발생: {e}"


def get_amplitude_retention(
    conn_id: str,
    start_event: str,
    return_event: str,
    start_date: str,
    end_date: str,
) -> str:
    """[Amplitude] 리텐션 분석 — 첫 이벤트 후 재방문율.

    Args:
        conn_id: Amplitude 연결 ID
        start_event: 첫 이벤트 이름
        return_event: 재방문 이벤트 이름
        start_date: YYYYMMDD 형태의 시작일
        end_date: YYYYMMDD 형태의 종료일

    Returns:
        일자별 리텐션율 마크다운
    """
    if conn_id not in _amplitude_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    creds = _amplitude_connections[conn_id]

    try:
        resp = httpx.get(
            f"{AMPLITUDE_DASHBOARD_API}/retention",
            params={
                "se": json.dumps({"event_type": start_event}),
                "re": json.dumps({"event_type": return_event}),
                "start": start_date,
                "end": end_date,
            },
            auth=(creds["api_key"], creds["secret_key"]),
            timeout=15.0,
        )
        if resp.status_code != 200:
            return f"[ERROR] Amplitude API 오류: {resp.status_code}"

        data = resp.json()
        retention_data = data.get("data", {})
        if not retention_data:
            return "리텐션 데이터가 없습니다."

        lines = [f"## 리텐션 분석: {start_event} → {return_event}", ""]
        for date_key, values in retention_data.items():
            if isinstance(values, list):
                rates = [f"Day {i}: {v:.1%}" for i, v in enumerate(values) if v is not None]
                lines.append(f"**{date_key}**: " + ", ".join(rates))

        return "\n".join(lines) if len(lines) > 2 else "리텐션 데이터가 없습니다."

    except httpx.RequestError as e:
        return f"[ERROR] Amplitude 네트워크 오류: {e}"
    except Exception as e:
        return f"[ERROR] 리텐션 분석 중 예외 발생: {e}"


def get_amplitude_cohort(conn_id: str, cohort_id: str) -> str:
    """[Amplitude] 코호트 사용자 목록 조회.

    Args:
        conn_id: Amplitude 연결 ID
        cohort_id: Amplitude 코호트 ID

    Returns:
        코호트 사용자 정보 마크다운
    """
    if conn_id not in _amplitude_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    creds = _amplitude_connections[conn_id]

    try:
        resp = httpx.get(
            f"{AMPLITUDE_DASHBOARD_API}/cohorts/request/{cohort_id}",
            auth=(creds["api_key"], creds["secret_key"]),
            timeout=15.0,
        )
        if resp.status_code != 200:
            return f"[ERROR] Amplitude API 오류: {resp.status_code}"

        data = resp.json()
        cohort = data.get("cohort", data)
        name = cohort.get("name", cohort_id)
        size = cohort.get("size", "알 수 없음")
        definition = cohort.get("definition", {})

        lines = [
            f"## 코호트: {name}",
            f"- ID: {cohort_id}",
            f"- 사용자 수: {size}",
        ]
        if definition:
            lines.append(f"- 정의: {json.dumps(definition, ensure_ascii=False)}")

        return "\n".join(lines)

    except httpx.RequestError as e:
        return f"[ERROR] Amplitude 네트워크 오류: {e}"
    except Exception as e:
        return f"[ERROR] 코호트 조회 중 예외 발생: {e}"


def get_amplitude_user_properties(conn_id: str, user_id: str) -> str:
    """[Amplitude] 사용자 속성 조회.

    Args:
        conn_id: Amplitude 연결 ID
        user_id: 조회할 사용자 ID

    Returns:
        사용자 속성 마크다운
    """
    if conn_id not in _amplitude_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    creds = _amplitude_connections[conn_id]

    try:
        resp = httpx.get(
            f"{AMPLITUDE_DASHBOARD_API}/useractivity",
            params={"user": user_id},
            auth=(creds["api_key"], creds["secret_key"]),
            timeout=15.0,
        )
        if resp.status_code != 200:
            return f"[ERROR] Amplitude API 오류: {resp.status_code}"

        data = resp.json()
        user_data = data.get("userData", {})
        user_props = user_data.get("user_properties", {})

        if not user_props:
            return f"사용자 '{user_id}'의 속성 데이터가 없습니다."

        lines = [f"## 사용자 속성: {user_id}", ""]
        for key, value in user_props.items():
            lines.append(f"- **{key}**: {value}")

        return "\n".join(lines)

    except httpx.RequestError as e:
        return f"[ERROR] Amplitude 네트워크 오류: {e}"
    except Exception as e:
        return f"[ERROR] 사용자 속성 조회 중 예외 발생: {e}"


def get_amplitude_event_types(conn_id: str) -> str:
    """[Amplitude] Lexicon — 등록된 이벤트 타입 목록.

    Args:
        conn_id: Amplitude 연결 ID

    Returns:
        이벤트 타입 목록 마크다운
    """
    if conn_id not in _amplitude_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    creds = _amplitude_connections[conn_id]

    try:
        resp = httpx.get(
            f"{AMPLITUDE_DASHBOARD_API}/taxonomy/event",
            auth=(creds["api_key"], creds["secret_key"]),
            timeout=15.0,
        )
        if resp.status_code != 200:
            return f"[ERROR] Amplitude API 오류: {resp.status_code}"

        data = resp.json()
        event_types = data.get("data", [])

        if not event_types:
            return "등록된 이벤트 타입이 없습니다."

        lines = [f"## Amplitude 이벤트 타입 ({len(event_types)}개)", ""]
        lines += [f"- {et.get('event_type', str(et))}" for et in event_types]

        return "\n".join(lines)

    except httpx.RequestError as e:
        return f"[ERROR] Amplitude 네트워크 오류: {e}"
    except Exception as e:
        return f"[ERROR] 이벤트 타입 조회 중 예외 발생: {e}"
