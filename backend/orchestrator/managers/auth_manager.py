import asyncio
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
        Google OAuth 2.0 PKCE 플로우를 실행하여 토큰을 획득/저장한다.
        브라우저가 열리고, 사용자가 로그인하면 자동으로 토큰이 저장된다.
        """
        try:
            from backend.orchestrator.managers.oauth_handler import google_oauth_login

            tokens = await asyncio.to_thread(google_oauth_login)
            if tokens:
                self.set_provider_token("gemini", tokens)
                logger.info("Google OAuth login successful, tokens saved")
                return True
            else:
                logger.warning("Google OAuth login failed or was cancelled")
                return False
        except Exception as e:
            logger.error(f"OAuth login flow error: {e}")
            return False

    async def login_provider(self, provider: str) -> tuple[bool, str]:
        """
        Provider별 로그인 플로우를 실행한다.

        Returns:
            (성공 여부, 사용자 안내 메시지)
        """
        if provider == "gemini":
            client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
            if not client_id:
                return False, (
                    "⚠ Google OAuth를 사용하려면 GCP에서 OAuth Client ID를 발급받아야 합니다.\n"
                    "  1. https://console.cloud.google.com/apis/credentials 에서 앱 등록\n"
                    "  2. 환경변수에 설정:\n"
                    "     GOOGLE_OAUTH_CLIENT_ID=<client_id>\n"
                    "     GOOGLE_OAUTH_CLIENT_SECRET=<client_secret>\n"
                    "\n"
                    "  또는 AI Studio에서 API 키 발급 후:\n"
                    "     /setting set gemini_key <키>"
                )
            success = await self.login_with_google_oauth()
            if success:
                return True, "✓ Google 계정 로그인 성공! 토큰이 저장되었습니다."
            return False, "⚠ Google 로그인이 취소되었거나 실패했습니다. 다시 시도해주세요."

        elif provider == "claude":
            return False, (
                "⚠ Anthropic(Claude)은 서드파티 앱의 OAuth 로그인을 지원하지 않습니다.\n"
                "  API 키를 직접 복사하여 설정해주세요:\n"
                "  1. https://console.anthropic.com/settings/keys 에서 키 생성\n"
                "  2. /setting set claude_key <키>"
            )

        elif provider == "openai":
            return False, (
                "⚠ OpenAI는 서드파티 앱의 개인 OAuth 로그인을 지원하지 않습니다.\n"
                "  API 키를 직접 복사하여 설정해주세요:\n"
                "  1. https://platform.openai.com/api-keys 에서 키 생성\n"
                "  2. /setting set openai_key <키>"
            )

        return False, f"⚠ 알 수 없는 프로바이더: {provider}"

    def ensure_valid_token(self, provider: str) -> Optional[str]:
        """
        토큰이 만료되었으면 갱신하고 유효한 access_token을 반환한다.
        API 키 방식이면 None을 반환한다 (호출자가 API 키를 사용해야 함).
        """
        data = self.get_provider_data(provider)
        token_data = data.get("token")

        if not token_data or not isinstance(token_data, dict):
            return None

        access_token = token_data.get("access_token")
        if not access_token:
            return None

        # 만료 확인
        from backend.orchestrator.managers.oauth_handler import is_token_expired, refresh_access_token

        if not is_token_expired(token_data):
            return access_token

        # Refresh 시도
        refresh_token = token_data.get("refresh_token")
        if not refresh_token:
            logger.warning(f"{provider} token expired and no refresh token available")
            return None

        logger.info(f"Refreshing expired {provider} token...")
        new_tokens = refresh_access_token(refresh_token)
        if new_tokens:
            self.set_provider_token(provider, new_tokens)
            return new_tokens["access_token"]

        logger.error(f"Failed to refresh {provider} token")
        return None

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
