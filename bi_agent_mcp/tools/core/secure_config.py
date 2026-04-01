"""보안 설정 관리 — 연결 메타데이터 저장, 민감 필드 OS keyring 보호."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_SENSITIVE_KEYS = {"password", "api_key", "secret", "token", "private_key", "credentials_json"}
_DEFAULT_CONFIG_DIR = Path.home() / ".bi-agent"


class SecureConfig:
    """연결 설정을 저장·로드·삭제하는 보안 설정 관리자."""

    def __init__(self, config_dir: Path = _DEFAULT_CONFIG_DIR) -> None:
        self._config_dir = Path(config_dir)
        self._config_file = self._config_dir / "config.json"
        self._config_dir.mkdir(parents=True, exist_ok=True)
        if not self._config_file.exists():
            self._config_file.write_text("{}", encoding="utf-8")

    def _keyring_set(self, conn_id: str, key: str, value: str) -> None:
        try:
            import keyring
            keyring.set_password(f"bi-agent/{conn_id}", key, value)
        except Exception as e:
            logger.warning("keyring 저장 실패 (%s/%s): %s", conn_id, key, e)

    def _keyring_get(self, conn_id: str, key: str) -> Optional[str]:
        try:
            import keyring
            val = keyring.get_password(f"bi-agent/{conn_id}", key)
            if val is not None:
                return val
        except Exception:
            pass
        import os
        env_key = f"BI_AGENT_{conn_id.upper()}_{key.upper()}"
        return os.environ.get(env_key)

    def _keyring_delete(self, conn_id: str, key: str) -> None:
        try:
            import keyring
            keyring.delete_password(f"bi-agent/{conn_id}", key)
        except Exception:
            pass

    def _read_all(self) -> dict:
        try:
            return json.loads(self._config_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _write_all(self, data: dict) -> None:
        self._config_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def save_connection(self, conn_id: str, fields: dict[str, Any]) -> None:
        """연결 정보를 저장한다. 민감 필드는 keyring, 나머지는 config.json."""
        meta: dict[str, Any] = {}
        for k, v in fields.items():
            if k in _SENSITIVE_KEYS:
                self._keyring_set(conn_id, k, str(v))
            else:
                meta[k] = v
        all_data = self._read_all()
        all_data[conn_id] = meta
        self._write_all(all_data)

    def load_connection(self, conn_id: str) -> Optional[dict[str, Any]]:
        """저장된 연결 정보를 반환한다. 없으면 None."""
        all_data = self._read_all()
        if conn_id not in all_data:
            return None
        result = dict(all_data[conn_id])
        for key in _SENSITIVE_KEYS:
            val = self._keyring_get(conn_id, key)
            if val is not None:
                result[key] = val
        return result

    def list_connections(self) -> list[str]:
        """저장된 conn_id 목록을 반환한다."""
        return list(self._read_all().keys())

    def delete_connection(self, conn_id: str) -> None:
        """연결 정보를 삭제한다 (config.json + keyring 모두)."""
        all_data = self._read_all()
        all_data.pop(conn_id, None)
        self._write_all(all_data)
        for key in _SENSITIVE_KEYS:
            self._keyring_delete(conn_id, key)


secure_config = SecureConfig()
