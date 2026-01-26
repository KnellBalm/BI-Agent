import os
import json
import webbrowser
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path

class AuthManager:
    """
    Manages user-specific credentials and OAuth flows.
    Stores data in ~/.bi-agent/ to prevent Git leaks.
    """
    def __init__(self):
        self.home_dir = Path.home() / ".bi-agent"
        self.creds_path = self.home_dir / "credentials.json"
        self.home_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_gitignore()
        self.credentials = self._load_credentials()

    def _ensure_gitignore(self):
        """Ensure the home directory has its own protection if needed."""
        # Mostly handled by global .gitignore, but safe to keep home dir isolated
        pass

    def _load_credentials(self) -> Dict[str, Any]:
        if self.creds_path.exists():
            try:
                with open(self.creds_path, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {"gemini_key": None, "openai_key": None, "claude_key": None, "tokens": {}}

    def save_credentials(self):
        with open(self.creds_path, 'w') as f:
            json.dump(self.credentials, f, indent=2)

    def get_gemini_key(self) -> Optional[str]:
        return self.credentials.get("gemini_key") or os.getenv("GEMINI_API_KEY")

    def set_gemini_key(self, key: str):
        self.credentials["gemini_key"] = key
        self.save_credentials()

    async def login_with_google(self) -> bool:
        """
        Simulates an OAuth flow by opening the key generation page 
        and prompting the user in a professional way.
        (Real OAuth 2.0 Loop can be added here if Client ID is provided)
        """
        # For this MVP, we guide them to the API key page which acts as a 'login'
        # in the context of Google AI Studio.
        url = "https://aistudio.google.com/app/apikey"
        webbrowser.open(url)
        return True

    def is_authenticated(self) -> bool:
        return self.get_gemini_key() is not None

# Global instance for shared access
auth_manager = AuthManager()
