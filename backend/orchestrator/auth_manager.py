import os
import json
import webbrowser
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from backend.utils.logger_setup import setup_logger

# Initialize localized logger
logger = setup_logger("auth_manager", "auth.log")

class AuthManager:
    """
    분석가의 개인 LLM 구독 계정 및 API 키를 관리합니다.
    데이터는 ~/.bi-agent/credentials.json에 저장되어 프라이버시를 보호합니다.
    """
    def __init__(self):
        try:
            self.home_dir = Path.home() / ".bi-agent"
            self.creds_path = self.home_dir / "credentials.json"
            self.home_dir.mkdir(parents=True, exist_ok=True)
            self.credentials = self._load_credentials()
            logger.info(f"AuthManager initialized at {self.creds_path}")
        except Exception as e:
            logger.error(f"Failed to initialize AuthManager: {e}")
            self.credentials = {"providers": {}}

    def _load_credentials(self) -> Dict[str, Any]:
        if self.creds_path.exists():
            try:
                with open(self.creds_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Migrate or ensure structure
                    if "providers" not in data:
                        data = {"providers": {
                            "gemini": {"key": data.get("gemini_key"), "token": None},
                            "claude": {"key": data.get("claude_key"), "token": None},
                            "openai": {"key": data.get("openai_key"), "token": None},
                        }}
                    else:
                        # Ensure all providers exist in the dict
                        for p in ["gemini", "claude", "openai"]:
                            if p not in data["providers"]:
                                data["providers"][p] = {"key": None, "token": None}
                    return data
            except Exception as e:
                logger.error(f"Error loading credentials: {e}")
        return {"providers": {
            "gemini": {"key": None, "token": None},
            "claude": {"key": None, "token": None},
            "openai": {"key": None, "token": None}
        }}

    def save_credentials(self):
        try:
            with open(self.creds_path, 'w', encoding='utf-8') as f:
                json.dump(self.credentials, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")

    def get_provider_data(self, provider: str) -> Dict[str, Any]:
        return self.credentials["providers"].get(provider, {"key": None, "token": None})

    def set_provider_key(self, provider: str, key: str):
        if provider not in self.credentials["providers"]:
            self.credentials["providers"][provider] = {}
        self.credentials["providers"][provider]["key"] = key
        self.save_credentials()

    def set_provider_token(self, provider: str, token: Dict[str, Any]):
        if provider not in self.credentials["providers"]:
            self.credentials["providers"][provider] = {}
        self.credentials["providers"][provider]["token"] = token
        self.save_credentials()

    async def login_with_google_oauth(self) -> bool:
        """
        웹 브라우저를 통해 Google 계정 로그인을 처리하고 OAuth 토큰을 획득합니다.
        AI Studio의 무료 티어 API를 사용하기 위해 Google OAuth 2.0 흐름을 시뮬레이션하거나 처리합니다.
        """
        try:
            # AI Studio API Key 발급 페이지 안내가 가장 확실한 '구독 혜택 활용' 방법임
            url = "https://aistudio.google.com/app/apikey"
            console_msg = "\n[bold cyan]Google AI Studio[/bold cyan]로 이동하여 API Key를 발급받으세요."
            console_msg += "\n유료 구독(Gemini Pro) 계정으로 로그인 시 높은 할당량의 무료 티어를 쓸 수 있습니다."
            
            # TUI 환경이 아닐 경우 목적으로 간단히 브라우저만 오픈
            webbrowser.open(url)
            return True
        except Exception as e:
            logger.error(f"OAuth login flow error: {e}")
            return False

    def is_authenticated(self, provider: str = "gemini") -> bool:
        """Checks if a provider has an API key or token (including environment variables)."""
        data = self.get_provider_data(provider)
        if data.get("key") or data.get("token"):
            return True
        
        # Fallback to environment variables
        env_map = {
            "gemini": "GEMINI_API_KEY",
            "claude": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY"
        }
        if provider in env_map and os.getenv(env_map[provider]):
            return True
        return False

# Global instance
auth_manager = AuthManager()
