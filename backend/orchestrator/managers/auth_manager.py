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
            # Ensure the directory has restricted permissions (700)
            os.chmod(self.home_dir, 0o700)
            self.credentials = self._load_credentials()
            # If file exists, ensure it has restricted permissions (600)
            if self.creds_path.exists():
                os.chmod(self.creds_path, 0o600)
            logger.info(f"AuthManager initialized at {self.creds_path}")
        except Exception as e:
            logger.error(f"Failed to initialize AuthManager: {e}")
            self.credentials = {"providers": {}}

    def load_credentials(self):
        """환경 및 로컬 파일에서 인증 정보를 다시 로드합니다."""
        self.credentials = self._load_credentials()
        return self.credentials

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
            # Create file with 600 permissions using os.open for atomicity
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
            mode = 0o600
            with os.fdopen(os.open(self.creds_path, flags, mode), 'w', encoding='utf-8') as f:
                json.dump(self.credentials, f, indent=2)
            logger.info(f"Credentials saved securely to {self.creds_path}")
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

    async def verify_key(self, provider: str, key: str) -> bool:
        """
        입력된 API 키가 유효한지 실제 API 호출을 통해 검증합니다 (Ping test).
        """
        try:
            if provider == "gemini":
                import google.generativeai as genai
                genai.configure(api_key=key)
                model = genai.GenerativeModel('gemini-1.5-flash-8b') # 저렴하고 빠른 모델로 테스트
                # 간단한 응답 생성 테스트
                response = model.generate_content("hello", generation_config={"max_output_tokens": 1})
                return True
            
            elif provider == "claude":
                # httpx를 사용하여 직접 API 호출 (anthropic 패키지가 없을 수 있으므로)
                import httpx
                headers = {
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                async with httpx.AsyncClient() as client:
                    # 빈 메시지 생성을 시도하여 키 유효성 확인
                    response = await client.post(
                        "https://api.anthropic.com/v1/messages",
                        headers=headers,
                        json={
                            "model": "claude-3-haiku-20240307",
                            "max_tokens": 1,
                            "messages": [{"role": "user", "content": "hi"}]
                        },
                        timeout=5.0
                    )
                    return response.status_code == 200
            
            elif provider == "openai":
                import httpx
                headers = {
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                }
                async with httpx.AsyncClient() as client:
                    # 모델 목록 조회로 키 유효성 확인
                    response = await client.get(
                        "https://api.openai.com/v1/models",
                        headers=headers,
                        timeout=5.0
                    )
                    return response.status_code == 200
            
            return False
        except Exception as e:
            logger.error(f"Failed to verify {provider} key: {e}")
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
