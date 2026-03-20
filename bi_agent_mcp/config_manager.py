"""bi-agent 설정 관리자 — config 파일 + OS keyring 통합."""

import copy
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SERVICE_NAME = "bi-agent"
CONFIG_DIR = Path("~/.config/bi-agent").expanduser()
CONFIG_FILE = CONFIG_DIR / "config.json"

_DEFAULT_CONFIG: dict = {
    "version": 1,
    "datasources": {
        "db": {},
        "ga4": {},
        "amplitude": {},
    },
}


class ConfigManager:
    """비밀 값은 OS keyring에, 비밀이 아닌 값은 config.json에 저장."""

    def save_datasource(
        self, source_type: str, params: dict, secrets: Optional[dict] = None
    ) -> None:
        """데이터 소스 설정을 저장합니다.

        Args:
            source_type: "db", "ga4", "amplitude" 중 하나
            params: 비밀이 아닌 설정 (host, port, database, user 등) → config.json
            secrets: 비밀 값 (password, api_key 등) → OS keyring
        """
        try:
            from bi_agent_mcp.auth.credentials import store_secret

            config = self._load_config()
            config.setdefault("datasources", {})[source_type] = params
            self._save_config(config)
            logger.debug("config.json에 저장: datasources.%s", source_type)

            if secrets:
                for k, v in secrets.items():
                    if v:
                        store_secret(SERVICE_NAME, f"{source_type}_{k}", v)
                        logger.debug("keyring에 저장: %s_%s", source_type, k)
        except Exception as e:
            logger.error("save_datasource 실패: %s", e)
            raise

    def load_datasource(self, source_type: str) -> dict:
        """데이터 소스 설정을 로드합니다. params + secrets를 합쳐서 반환."""
        try:
            from bi_agent_mcp.auth.credentials import get_env_or_secret

            config = self._load_config()
            params = config.get("datasources", {}).get(source_type, {})

            # 알려진 secret 키를 keyring에서 로드
            secret_keys = _SECRET_KEYS.get(source_type, [])
            secrets = {}
            for k in secret_keys:
                env_var = _SECRET_ENV_VARS.get(f"{source_type}_{k}", "")
                val = get_env_or_secret(env_var, SERVICE_NAME, f"{source_type}_{k}")
                if val:
                    secrets[k] = val

            return {**params, **secrets}
        except Exception as e:
            logger.error("load_datasource 실패: %s", e)
            return {}

    def list_datasources(self) -> dict:
        """설정된 데이터 소스 목록을 반환합니다."""
        try:
            from bi_agent_mcp.auth.credentials import get_env_or_secret

            config = self._load_config()
            datasources = config.get("datasources", {})

            db = datasources.get("db", {})
            db_configured = bool(db.get("host") or (db.get("type") == "bigquery" and db.get("project_id")))

            ga4 = datasources.get("ga4", {})
            ga4_configured = bool(ga4.get("property_id") or ga4.get("client_id"))

            # Amplitude: keyring에서도 확인
            amp_api_key = get_env_or_secret(
                "BI_AGENT_AMPLITUDE_API_KEY", SERVICE_NAME, "amplitude_api_key"
            )
            amplitude_configured = bool(amp_api_key)

            return {
                "db": {
                    "configured": db_configured,
                    "type": db.get("type"),
                    "host": db.get("host"),
                },
                "ga4": {
                    "configured": ga4_configured,
                    "property_id": ga4.get("property_id"),
                },
                "amplitude": {
                    "configured": amplitude_configured,
                },
            }
        except Exception as e:
            logger.error("list_datasources 실패: %s", e)
            return {"db": {"configured": False}, "ga4": {"configured": False}, "amplitude": {"configured": False}}

    def is_initialized(self) -> bool:
        """하나 이상의 데이터 소스가 설정되어 있으면 True."""
        sources = self.list_datasources()
        return any(v.get("configured") for v in sources.values())

    def get_missing_config(self) -> list[str]:
        """미설정된 데이터 소스 이름 목록 반환."""
        sources = self.list_datasources()
        return [k for k, v in sources.items() if not v.get("configured")]

    def reset_datasource(self, source_type: str) -> None:
        """데이터 소스 설정을 초기화합니다."""
        try:
            from bi_agent_mcp.auth.credentials import delete_secret

            config = self._load_config()
            config.setdefault("datasources", {})[source_type] = {}
            self._save_config(config)

            for k in _SECRET_KEYS.get(source_type, []):
                try:
                    delete_secret(SERVICE_NAME, f"{source_type}_{k}")
                except Exception:
                    pass
        except Exception as e:
            logger.error("reset_datasource 실패: %s", e)

    def _load_config(self) -> dict:
        """config.json 읽기. 없으면 기본값 반환."""
        if not CONFIG_FILE.exists():
            return copy.deepcopy(_DEFAULT_CONFIG)
        try:
            with CONFIG_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
            # 기본 구조 보장
            data.setdefault("datasources", {})
            return data
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("config.json 읽기 실패, 기본값 사용: %s", e)
            return copy.deepcopy(_DEFAULT_CONFIG)

    def _save_config(self, data: dict) -> None:
        """config.json 저장."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with CONFIG_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")


# 각 데이터 소스의 secret 키 목록
_SECRET_KEYS: dict[str, list[str]] = {
    "db": ["password"],
    "ga4": ["client_secret", "refresh_token"],
    "amplitude": ["api_key", "secret_key"],
}

# secret 키 → 환경변수 이름 매핑
_SECRET_ENV_VARS: dict[str, str] = {
    "db_password": "BI_AGENT_PG_PASSWORD",  # PG 기본값
    "ga4_client_secret": "BI_AGENT_GOOGLE_CLIENT_SECRET",
    "ga4_refresh_token": "BI_AGENT_GA4_REFRESH_TOKEN",
    "amplitude_api_key": "BI_AGENT_AMPLITUDE_API_KEY",
    "amplitude_secret_key": "BI_AGENT_AMPLITUDE_SECRET_KEY",
}
