"""알림(Alert) 도구 — create_alert, check_alerts, list_alerts, delete_alert."""
import json
import logging
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

_ALERTS_FILE = Path("~/.config/bi-agent/alerts.json").expanduser()


def _load_alerts() -> list:
    """저장된 알림 목록을 반환합니다."""
    if not _ALERTS_FILE.exists():
        return []
    try:
        with open(_ALERTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"알림 파일을 읽는 중 오류 발생: {e}")
        return []


def _save_alerts(alerts: list) -> None:
    """알림 목록을 파일에 저장합니다."""
    _ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_ALERTS_FILE, "w", encoding="utf-8") as f:
        json.dump(alerts, f, ensure_ascii=False, indent=2)


def _evaluate_condition(value, condition: str) -> bool:
    """condition 형식: 'gt:100', 'lt:50', 'eq:0', 'ne:0', 'gte:100', 'lte:50'"""
    try:
        op, threshold_str = condition.split(":", 1)
        threshold = float(threshold_str)
        value = float(value)
    except (ValueError, TypeError):
        return False

    op = op.lower()
    if op == "gt":
        return value > threshold
    elif op == "lt":
        return value < threshold
    elif op == "eq":
        return value == threshold
    elif op == "ne":
        return value != threshold
    elif op == "gte":
        return value >= threshold
    elif op == "lte":
        return value <= threshold
    return False


def create_alert(conn_id: str, name: str, sql: str, condition: str, message: str = "") -> str:
    """
    SQL 쿼리 결과에 대한 알림을 등록합니다.

    Args:
        conn_id: DB 연결 ID
        name: 알림 이름
        sql: 모니터링할 SELECT SQL (첫 번째 행의 첫 번째 컬럼값을 평가)
        condition: 조건 (예: "gt:100", "lt:50", "eq:0", "ne:0", "gte:100", "lte:50")
        message: 알림 발생 시 표시할 메시지 (선택)

    Returns:
        등록 결과 메시지
    """
    alert_id = str(uuid.uuid4())
    alerts = _load_alerts()
    alerts.append({
        "alert_id": alert_id,
        "name": name,
        "conn_id": conn_id,
        "sql": sql,
        "condition": condition,
        "message": message,
    })
    try:
        _save_alerts(alerts)
        return f"알림 '{name}' 등록됨 (ID: {alert_id})"
    except Exception as e:
        logger.error(f"알림 저장 중 오류 발생: {e}")
        return f"[ERROR] 알림 저장에 실패했습니다: {e}"


def check_alerts(alert_id: str = "") -> str:
    """
    알림 조건을 평가하고 결과를 반환합니다.

    Args:
        alert_id: 특정 알림 ID (생략 시 전체 알림 평가)

    Returns:
        알림 상태 Markdown 테이블
    """
    from bi_agent_mcp.tools.db import _connections, _get_conn, _validate_select

    alerts = _load_alerts()
    if not alerts:
        return "등록된 알림이 없습니다."

    if alert_id:
        targets = [a for a in alerts if a["alert_id"] == alert_id]
        if not targets:
            return f"[ERROR] 알림 ID '{alert_id}'를 찾을 수 없습니다."
    else:
        targets = alerts

    rows = ["| 알림명 | 조건 | 현재값 | 상태 |", "|--------|------|--------|------|"]

    for alert in targets:
        name = alert.get("name", "")
        condition = alert.get("condition", "")
        conn_id = alert.get("conn_id", "")
        sql = alert.get("sql", "")

        # SELECT 검증
        err = _validate_select(sql)
        if err:
            rows.append(f"| {name} | {condition} | N/A | [ERROR] {err} |")
            continue

        # DB 연결 확인
        if conn_id not in _connections:
            rows.append(f"| {name} | {condition} | N/A | [ERROR] 연결 ID '{conn_id}' 없음 |")
            continue

        info = _connections[conn_id]
        try:
            conn = _get_conn(info)
            cur = conn.cursor()
            cur.execute(sql)
            row = cur.fetchone()
            cur.close()
            conn.close()
        except Exception as e:
            rows.append(f"| {name} | {condition} | N/A | [ERROR] {e} |")
            continue

        if row is None or len(row) == 0:
            rows.append(f"| {name} | {condition} | N/A | [ERROR] 결과 없음 |")
            continue

        value = row[0]
        triggered = _evaluate_condition(value, condition)
        status = "🔴 TRIGGERED" if triggered else "✅ OK"
        rows.append(f"| {name} | {condition} | {value} | {status} |")

    return "\n".join(rows)


def list_alerts() -> str:
    """
    등록된 알림 목록을 Markdown 테이블로 반환합니다.
    """
    alerts = _load_alerts()
    if not alerts:
        return "등록된 알림이 없습니다."

    rows = ["| ID | 알림명 | 연결 ID | 조건 | SQL 미리보기 |", "|----|--------|---------|------|--------------|"]
    for alert in alerts:
        alert_id = alert.get("alert_id", "")
        name = alert.get("name", "")
        conn_id = alert.get("conn_id", "")
        condition = alert.get("condition", "")
        sql_preview = alert.get("sql", "")[:50].replace("\n", " ")
        rows.append(f"| {alert_id[:8]}... | {name} | {conn_id} | {condition} | {sql_preview} |")

    return "\n".join(rows)


def delete_alert(alert_id: str) -> str:
    """
    알림을 삭제합니다.

    Args:
        alert_id: 삭제할 알림 ID

    Returns:
        삭제 결과 메시지
    """
    alerts = _load_alerts()
    target = next((a for a in alerts if a["alert_id"] == alert_id), None)
    if target is None:
        return f"[ERROR] 알림 ID '{alert_id}'를 찾을 수 없습니다."

    name = target.get("name", "")
    alerts = [a for a in alerts if a["alert_id"] != alert_id]
    try:
        _save_alerts(alerts)
        return f"알림 '{name}' 삭제됨"
    except Exception as e:
        logger.error(f"알림 삭제 중 오류 발생: {e}")
        return f"[ERROR] 알림 삭제에 실패했습니다: {e}"
