"""
Setting Manager — BI-Agent 통합 설정 관리.

API 키, 모델, 언어 등 설정을 단일 인터페이스로 관리한다.
- API 키 → ~/.bi-agent/credentials.json (AuthManager)
- 모델/언어 → .agent/config/user-preferences.yaml
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional

import yaml


# ──────────────────────────────────────────────
# 설정 키 정의
# ──────────────────────────────────────────────

# API 키 관련
_API_KEY_MAP = {
    "gemini_key": "gemini",
    "claude_key": "claude",
    "openai_key": "openai",
}

# preferences.yaml 관련
_PREF_KEYS = {"model", "language"}

# 전체 지원 키 목록 (도움말용)
SETTING_KEYS = {
    "gemini_key":  "Gemini API 키",
    "claude_key":  "Claude API 키",
    "openai_key":  "OpenAI API 키",
    "model":       "기본 LLM 모델 (예: gemini-2.0-flash)",
    "language":    "응답 언어 (ko, en, ja, ...)",
}


class SettingManager:
    """통합 설정 관리자."""

    def __init__(self):
        # user-preferences.yaml 경로
        self._pref_path = self._find_preferences_path()

    # ──────────────────────────────────────────
    # 읽기
    # ──────────────────────────────────────────

    def get_all(self) -> Dict[str, Any]:
        """현재 설정을 모두 읽어 dict로 반환한다. API 키는 마스킹 처리."""
        from backend.orchestrator.managers.auth_manager import auth_manager

        result = {}

        # API Keys (마스킹)
        for setting_key, provider in _API_KEY_MAP.items():
            raw = auth_manager.get_provider_data(provider).get("key")
            if not raw:
                # env fallback
                env_map = {"gemini": "GEMINI_API_KEY", "claude": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}
                raw = os.getenv(env_map.get(provider, ""))
            result[setting_key] = self._mask(raw) if raw else "(미설정)"

        # Preferences
        prefs = self._load_preferences()
        result["model"] = prefs.get("default_cli", "(미설정)")
        result["language"] = prefs.get("language", "(미설정)")

        return result

    def get(self, key: str) -> Optional[str]:
        """단일 키의 값을 반환한다."""
        all_settings = self.get_all()
        return all_settings.get(key)

    # ──────────────────────────────────────────
    # 쓰기
    # ──────────────────────────────────────────

    def set(self, key: str, value: str) -> str:
        """설정값을 저장하고 결과 메시지를 반환한다."""
        if key in _API_KEY_MAP:
            return self._set_api_key(key, value)
        elif key in _PREF_KEYS:
            return self._set_preference(key, value)
        else:
            return f"알 수 없는 설정 키: {key}\n지원 키: {', '.join(SETTING_KEYS.keys())}"

    def _set_api_key(self, key: str, value: str) -> str:
        from backend.orchestrator.managers.auth_manager import auth_manager
        provider = _API_KEY_MAP[key]
        auth_manager.set_provider_key(provider, value)
        return f"✓ {SETTING_KEYS[key]} 저장 완료 ({self._mask(value)})"

    def _set_preference(self, key: str, value: str) -> str:
        prefs = self._load_preferences()
        prefs[key] = value
        self._save_preferences(prefs)
        return f"✓ {SETTING_KEYS[key]} → {value}"

    # ──────────────────────────────────────────
    # 내부 유틸
    # ──────────────────────────────────────────

    @staticmethod
    def _mask(value: str) -> str:
        """API 키를 앞 4자리만 보이게 마스킹."""
        if not value or len(value) < 8:
            return "****"
        return value[:4] + "*" * (len(value) - 4)

    def _find_preferences_path(self) -> Path:
        """user-preferences.yaml 경로를 찾는다."""
        # 프로젝트 루트 기준
        candidates = [
            Path.cwd() / ".agent" / "config" / "user-preferences.yaml",
            Path(__file__).resolve().parent.parent.parent / ".agent" / "config" / "user-preferences.yaml",
        ]
        for p in candidates:
            if p.exists():
                return p
        # 없으면 기본 위치에 생성할 수 있도록 첫 번째 후보 반환
        return candidates[0]

    def _load_preferences(self) -> Dict[str, Any]:
        if self._pref_path.exists():
            try:
                with open(self._pref_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                return {}
        return {}

    def _save_preferences(self, prefs: Dict[str, Any]):
        self._pref_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._pref_path, "w", encoding="utf-8") as f:
            yaml.dump(prefs, f, allow_unicode=True, default_flow_style=False)


# 싱글턴
setting_manager = SettingManager()
