"""connections.json 기반 다중 연결 관리 — 외부 접근용 API."""
import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "bi-agent"
CONNECTIONS_FILE = CONFIG_DIR / "connections.json"


def load_connections() -> dict:
    """connections.json에서 연결 설정 로드.

    Returns:
        {conn_id: {db_type, host, port, database, user, ...}} 형태의 딕셔너리.
        파일이 없으면 빈 딕셔너리 반환.
    """
    if not CONNECTIONS_FILE.exists():
        return {}
    try:
        with open(CONNECTIONS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        # 최상위가 dict이면 그대로 반환 (db.py의 _save_connections 형식)
        # {"connections": {...}} 형식도 지원
        if "connections" in data and isinstance(data["connections"], dict):
            return data["connections"]
        return data
    except Exception:
        return {}


def save_connections(connections: dict) -> None:
    """연결 설정을 connections.json에 저장.

    Args:
        connections: {conn_id: {db_type, host, ...}} 형태의 딕셔너리.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONNECTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(connections, f, ensure_ascii=False, indent=2)


def get_first_connection_id() -> str:
    """connections.json의 첫 번째 연결 ID 반환. 없으면 빈 문자열."""
    conns = load_connections()
    if not conns:
        return ""
    return next(iter(conns))
