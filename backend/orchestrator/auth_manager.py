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
                    if "providers" not in data: # Migration
                        return {"providers": {
                            "gemini": {"key": data.get("gemini_key"), "token": None},
                            "claude": {"key": data.get("claude_key"), "token": None},
                        }}
                    return data
            except Exception as e:
                logger.error(f"Error loading credentials: {e}")
        return {"providers": {
            "gemini": {"key": None, "token": None},
            "claude": {"key": None, "token": None}
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
        (gcloud auth login 과 유사하게 동작)
        """
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            
            # TODO: 공식 Client ID가 없을 경우를 대비해 사용자에게 안내하거나
            # 사전에 정의된 환경 변수를 참조하도록 설계
            scopes = ['https://www.googleapis.com/auth/generative-language']
            
            # Placeholder for actual OAuth config
            # 실제 운영 시에는 Client ID/Secret을 환경 변수나 설정 파일에서 가져와야 함
            logger.info("Starting Google OAuth login flow...")
            
            # 임시로 AI Studio 안내 유지 (실제 OAuth 구현 전까지)
            url = "https://aistudio.google.com/app/apikey"
            webbrowser.open(url)
            return True
        except Exception as e:
            logger.error(f"OAuth login failed: {e}")
            return False

    def is_authenticated(self, provider: str = "gemini") -> bool:
        """Checks if a provider has an API key or token (including environment variables)."""
        data = self.get_provider_data(provider)
        if data.get("key") or data.get("token"):
            return True
        
        # Fallback to environment variables
        if provider == "gemini" and os.getenv("GEMINI_API_KEY"):
            return True
        elif provider == "claude" and os.getenv("ANTHROPIC_API_KEY"):
            return True
        return False

# Global instance
auth_manager = AuthManager()
