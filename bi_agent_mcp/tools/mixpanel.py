"""
Mixpanel 연동 도구.
"""
import json
import logging
from typing import Dict

import httpx

logger = logging.getLogger(__name__)

_mixpanel_connections: Dict[str, dict] = {}

MIXPANEL_DATA_API = "https://data.mixpanel.com/api/2.0"
MIXPANEL_API = "https://mixpanel.com/api/2.0"


def connect_mixpanel(
    project_token: str,
    api_secret: str,
    conn_id: str = "default",
) -> str:
    """[Mixpanel] Mixpanel 프로젝트 연결 등록.

    Args:
        project_token: Mixpanel 프로젝트 토큰
        api_secret: Mixpanel API Secret
        conn_id: 연결 식별자 (기본값: "default")

    Returns:
        상태 메시지
    """
    if not project_token or not api_secret:
        return "[ERROR] project_token과 api_secret이 필요합니다."

    _mixpanel_connections[conn_id] = {
        "project_token": project_token,
        "api_secret": api_secret,
    }

    return f"[SUCCESS] Mixpanel 연결 등록 완료 (conn_id='{conn_id}')"


def get_mixpanel_events(
    conn_id: str,
    event_names: str,
    from_date: str,
    to_date: str,
    limit: int = 500,
) -> str:
    """[Mixpanel] 이벤트 로그 쿼리.

    Args:
        conn_id: 연결 식별자
        event_names: 쉼표 구분 또는 JSON 배열 문자열 (예: "Purchase,Login" 또는 '["Purchase","Login"]')
        from_date: 시작일 (YYYY-MM-DD)
        to_date: 종료일 (YYYY-MM-DD)
        limit: 최대 반환 행 수 (기본값: 500)

    Returns:
        이벤트 로그 마크다운 테이블 또는 에러 메시지
    """
    if conn_id not in _mixpanel_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_mixpanel()을 먼저 호출하세요."

    creds = _mixpanel_connections[conn_id]

    # event_names 파싱
    event_names = event_names.strip()
    if event_names.startswith("["):
        try:
            names_list = json.loads(event_names)
        except json.JSONDecodeError:
            return "[ERROR] event_names JSON 파싱 실패: 올바른 JSON 배열 형식으로 입력하세요."
    else:
        names_list = [n.strip() for n in event_names.split(",") if n.strip()]

    if not names_list:
        return "[ERROR] event_names가 비어 있습니다."

    try:
        params = {
            "event": json.dumps(names_list),
            "from_date": from_date,
            "to_date": to_date,
            "limit": limit,
        }
        resp = httpx.get(
            f"{MIXPANEL_DATA_API}/export",
            params=params,
            auth=(creds["api_secret"], ""),
            timeout=30.0,
        )

        if resp.status_code == 401:
            return "[ERROR] Mixpanel 인증 실패: api_secret을 확인하세요."
        if resp.status_code == 400:
            return f"[ERROR] 잘못된 파라미터: {resp.text}"
        if resp.status_code != 200:
            return f"[ERROR] Mixpanel API 호출 실패: HTTP {resp.status_code} - {resp.text}"

        # export API는 NDJSON 형식으로 반환
        rows = []
        for line in resp.text.strip().splitlines():
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        if not rows:
            return "조회된 이벤트 데이터가 없습니다."

        # 마크다운 테이블 생성
        headers = ["event", "distinct_id", "time"]
        md_table = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
        ]
        for row in rows[:limit]:
            event = row.get("event", "")
            props = row.get("properties", {})
            distinct_id = props.get("distinct_id", "")
            time_val = props.get("time", "")
            md_table.append(f"| {event} | {distinct_id} | {time_val} |")

        return "\n".join(md_table)

    except httpx.RequestError as e:
        logger.error("Mixpanel 네트워크 오류: %s", e)
        return f"[ERROR] Mixpanel 네트워크 오류: {e}"
    except Exception as e:
        logger.error("Mixpanel 이벤트 조회 예외: %s", e)
        return f"[ERROR] Mixpanel 이벤트 조회 중 예외 발생: {e}"


def get_mixpanel_funnel(
    conn_id: str,
    funnel_id: int,
    from_date: str,
    to_date: str,
) -> str:
    """[Mixpanel] 퍼널 전환율 분석.

    Args:
        conn_id: 연결 식별자
        funnel_id: Mixpanel 퍼널 ID
        from_date: 시작일 (YYYY-MM-DD)
        to_date: 종료일 (YYYY-MM-DD)

    Returns:
        퍼널 단계별 전환율 마크다운 테이블 또는 에러 메시지
    """
    if conn_id not in _mixpanel_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_mixpanel()을 먼저 호출하세요."

    creds = _mixpanel_connections[conn_id]

    try:
        params = {
            "funnel_id": funnel_id,
            "from_date": from_date,
            "to_date": to_date,
        }
        resp = httpx.get(
            f"{MIXPANEL_API}/funnels",
            params=params,
            auth=(creds["api_secret"], ""),
            timeout=15.0,
        )

        if resp.status_code == 401:
            return "[ERROR] Mixpanel 인증 실패: api_secret을 확인하세요."
        if resp.status_code == 400:
            return f"[ERROR] 잘못된 파라미터: {resp.text}"
        if resp.status_code != 200:
            return f"[ERROR] Mixpanel 퍼널 API 호출 실패: HTTP {resp.status_code} - {resp.text}"

        data = resp.json()
        meta = data.get("meta", {})
        dates = meta.get("dates", [])
        steps_data = data.get("data", {})

        if not dates or not steps_data:
            return "퍼널 데이터가 없습니다."

        # 첫 번째 날짜 기준으로 단계별 전환율 표시
        first_date = dates[0] if dates else None
        if not first_date or first_date not in steps_data:
            return "퍼널 날짜 데이터를 찾을 수 없습니다."

        steps = steps_data[first_date].get("steps", [])
        if not steps:
            return "퍼널 단계 데이터가 없습니다."

        headers = ["단계", "이벤트", "사용자 수", "전환율(%)"]
        md_table = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
        ]
        for i, step in enumerate(steps):
            step_label = step.get("step_label", f"Step {i+1}")
            event = step.get("event", "")
            count = step.get("count", 0)
            conversion = step.get("conversion_ratio", 0)
            md_table.append(f"| {i+1} | {event} ({step_label}) | {count} | {conversion*100:.1f}% |")

        return "\n".join(md_table)

    except httpx.RequestError as e:
        logger.error("Mixpanel 퍼널 네트워크 오류: %s", e)
        return f"[ERROR] Mixpanel 네트워크 오류: {e}"
    except Exception as e:
        logger.error("Mixpanel 퍼널 조회 예외: %s", e)
        return f"[ERROR] Mixpanel 퍼널 조회 중 예외 발생: {e}"


def get_mixpanel_retention(
    conn_id: str,
    born_event: str,
    return_event: str,
    from_date: str,
    to_date: str,
) -> str:
    """[Mixpanel] 리텐션 분석.

    Args:
        conn_id: 연결 식별자
        born_event: 코호트 진입 이벤트 (예: "Sign Up")
        return_event: 리텐션 측정 이벤트 (예: "Purchase")
        from_date: 시작일 (YYYY-MM-DD)
        to_date: 종료일 (YYYY-MM-DD)

    Returns:
        리텐션 마크다운 테이블 또는 에러 메시지
    """
    if conn_id not in _mixpanel_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_mixpanel()을 먼저 호출하세요."

    creds = _mixpanel_connections[conn_id]

    try:
        params = {
            "born_event": born_event,
            "event": return_event,
            "from_date": from_date,
            "to_date": to_date,
            "retention_type": "birth",
        }
        resp = httpx.get(
            f"{MIXPANEL_API}/retention",
            params=params,
            auth=(creds["api_secret"], ""),
            timeout=15.0,
        )

        if resp.status_code == 401:
            return "[ERROR] Mixpanel 인증 실패: api_secret을 확인하세요."
        if resp.status_code == 400:
            return f"[ERROR] 잘못된 파라미터: {resp.text}"
        if resp.status_code != 200:
            return f"[ERROR] Mixpanel 리텐션 API 호출 실패: HTTP {resp.status_code} - {resp.text}"

        data = resp.json()
        if not data:
            return "리텐션 데이터가 없습니다."

        headers = ["코호트 날짜", "코호트 크기", "Day 0", "Day 1", "Day 7", "Day 30"]
        md_table = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
        ]

        for date_key, cohort in data.items():
            if not isinstance(cohort, dict):
                continue
            cohort_size = cohort.get("count", 0)
            counts = cohort.get("counts", [])

            def get_rate(idx):
                if idx < len(counts) and cohort_size > 0:
                    return f"{counts[idx]/cohort_size*100:.1f}%"
                return "-"

            d0 = get_rate(0)
            d1 = get_rate(1)
            d7 = get_rate(7)
            d30 = get_rate(30)
            md_table.append(f"| {date_key} | {cohort_size} | {d0} | {d1} | {d7} | {d30} |")

        return "\n".join(md_table)

    except httpx.RequestError as e:
        logger.error("Mixpanel 리텐션 네트워크 오류: %s", e)
        return f"[ERROR] Mixpanel 네트워크 오류: {e}"
    except Exception as e:
        logger.error("Mixpanel 리텐션 조회 예외: %s", e)
        return f"[ERROR] Mixpanel 리텐션 조회 중 예외 발생: {e}"


def get_mixpanel_cohort_count(conn_id: str, cohort_id: int) -> str:
    """[Mixpanel] 코호트 사용자 수 조회.

    Args:
        conn_id: 연결 식별자
        cohort_id: Mixpanel 코호트 ID

    Returns:
        코호트 사용자 수 또는 에러 메시지
    """
    if conn_id not in _mixpanel_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_mixpanel()을 먼저 호출하세요."

    creds = _mixpanel_connections[conn_id]

    try:
        params = {
            "filter_by_cohort": json.dumps({"id": cohort_id}),
            "count_only": "true",
        }
        resp = httpx.get(
            f"{MIXPANEL_API}/engage",
            params=params,
            auth=(creds["api_secret"], ""),
            timeout=15.0,
        )

        if resp.status_code == 401:
            return "[ERROR] Mixpanel 인증 실패: api_secret을 확인하세요."
        if resp.status_code == 400:
            return f"[ERROR] 잘못된 파라미터: {resp.text}"
        if resp.status_code != 200:
            return f"[ERROR] Mixpanel 코호트 API 호출 실패: HTTP {resp.status_code} - {resp.text}"

        data = resp.json()
        total = data.get("total", None)
        if total is None:
            return "[ERROR] 코호트 사용자 수 응답 형식이 올바르지 않습니다."

        return f"코호트 ID {cohort_id} 사용자 수: {total:,}명"

    except httpx.RequestError as e:
        logger.error("Mixpanel 코호트 네트워크 오류: %s", e)
        return f"[ERROR] Mixpanel 네트워크 오류: {e}"
    except Exception as e:
        logger.error("Mixpanel 코호트 조회 예외: %s", e)
        return f"[ERROR] Mixpanel 코호트 조회 중 예외 발생: {e}"
