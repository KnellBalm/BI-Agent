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
    Manages user-specific credentials and OAuth flows.
    Stores data in ~/.bi-agent/ to prevent Git leaks.
    """
    def __init__(self):
        try:
            self.home_dir = Path.home() / ".bi-agent"
            self.creds_path = self.home_dir / "credentials.json"
            self.home_dir.mkdir(parents=True, exist_ok=True)
            self.credentials = self._load_credentials()
            logger.info(f"AuthManager initialized. Data path: {self.creds_path}")
        except Exception as e:
            logger.error(f"Failed to initialize AuthManager: {e}")
            self.credentials = {"gemini_key": None, "tokens": {}}

    def _load_credentials(self) -> Dict[str, Any]:
        if self.creds_path.exists():
            try:
                with open(self.creds_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading credentials: {e}")
        return {"gemini_key": None, "openai_key": None, "claude_key": None, "tokens": {}}

    def save_credentials(self):
        try:
            with open(self.creds_path, 'w', encoding='utf-8') as f:
                json.dump(self.credentials, f, indent=2)
            logger.info("Credentials saved successfully.")
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")

    def get_gemini_key(self) -> Optional[str]:
        key = self.credentials.get("gemini_key") or os.getenv("GEMINI_API_KEY")
        if not key:
            logger.warning("Gemini API Key requested but not found.")
        return key

    def set_gemini_key(self, key: str):
        if not key or len(key) < 10:
            logger.error("Attempted to set an invalid or too short Gemini API Key.")
            return
        self.credentials["gemini_key"] = key
        self.save_credentials()

    async def login_with_google(self) -> bool:
        """
        Guides the user to the API key generation page.
        """
        try:
            url = "https://aistudio.google.com/app/apikey"
            webbrowser.open(url)
            logger.info("Opened Google AI Studio for API Key generation.")
            return True
        except Exception as e:
            logger.error(f"Failed to open browser for login: {e}")
            return False

    def is_authenticated(self) -> bool:
        return self.get_gemini_key() is not None

# Global instance
auth_manager = AuthManager()
