import asyncio
import os
import google.generativeai as genai
from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

class LLMProvider(ABC):
    """
    LLM 서비스를 위한 추상 기본 클래스
    """
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        pass

    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]]) -> str:
        pass

class GeminiProvider(LLMProvider):
    """
    Google Gemini API를 사용한 LLM 구현 (멀티 키 및 과금 제어 지원)
    """
    def __init__(self, model_name: Optional[str] = None, quota_manager=None):
        # .env에서 가져오거나 기본값 사용
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        
        # 'models/' 프리픽스가 없으면 추가 (genai 라이브러리 요구사항)
        if not self.model_name.startswith("models/"):
            self.model_name = f"models/{self.model_name}"
            
        self.quota_manager = quota_manager
        self._setup_default_key()

    def _setup_default_key(self):
        # 기본 키 설정 (기존 .env 호환용)
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(self.model_name)
        else:
            self.model = None

    async def _ensure_active_key(self) -> str:
        """할당량이 남아있는 유효한 키 또는 토큰을 확보합니다."""
        from backend.orchestrator.auth_manager import auth_manager
        
        provider_data = auth_manager.get_provider_data("gemini")
        api_key = provider_data.get("key") or os.getenv("GEMINI_API_KEY")
        token = provider_data.get("token")

        if not api_key and not token:
             raise ValueError("계정 인증이 필요합니다. TUI 메인 화면에서 로그인을 진행해주거나 API Key를 설정해 주세요.")

        # API Key 우선 사용 (현재 라이브러리 지원 한계상)
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(self.model_name)
            return api_key
        
        # TODO: OAuth Token 사용 로직 (google-auth Credentials 객체 생성 필요)
        # 현재는 안내 메시지로 대체
        raise NotImplementedError("OAuth 토큰 기반 인증은 개발 중입니다. 현재는 API Key를 사용해 주세요.")

    async def generate(self, prompt: str) -> str:
        current_key = await self._ensure_active_key()
        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            if self.quota_manager and current_key:
                self.quota_manager.increment_usage(current_key)
            return response.text
        except Exception as e:
            if "429" in str(e) and self.quota_manager:
                # 할당량 초과 시 키 무효화 후 재시도
                await self.quota_manager.report_exhausted()
                return await self.generate(prompt)
            raise e

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        current_key = await self._ensure_active_key()
        try:
            history = []
            for msg in messages[:-1]:
                history.append({"role": msg["role"], "parts": [msg["content"]]})
            
            chat = self.model.start_chat(history=history)
            response = await asyncio.to_thread(chat.send_message, messages[-1]["content"])
            if self.quota_manager and current_key:
                self.quota_manager.increment_usage(current_key)
            return response.text
        except Exception as e:
            if "429" in str(e) and self.quota_manager:
                await self.quota_manager.report_exhausted()
                return await self.chat(messages)
            raise e

class OllamaProvider(LLMProvider):
    """
    Ollama (로컬 LLM)를 사용한 구현
    """
    def __init__(self, model_name: Optional[str] = None, base_url: str = 'http://localhost:11434'):
        self.model_name = model_name or os.getenv("OLLAMA_MODEL", "llama3")
        self.base_url = base_url

    async def generate(self, prompt: str) -> str:
        import httpx
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={"model": self.model_name, "prompt": prompt, "stream": False}
                )
                response.raise_for_status()
                return response.json().get("response", "")
            except Exception as e:
                return f"Ollama generation failed: {str(e)}"

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        import httpx
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={"model": self.model_name, "messages": messages, "stream": False}
                )
                response.raise_for_status()
                return response.json().get("message", {}).get("content", "")
            except Exception as e:
                return f"Ollama chat failed: {str(e)}"

class FailoverLLMProvider(LLMProvider):
    """
    여러 LLM 공급자를 순차적으로 시도하는 공급자 (Gemini -> Ollama)
    """
    def __init__(self, primary: LLMProvider, secondary: LLMProvider):
        self.primary = primary
        self.secondary = secondary
        self.use_secondary = False

    async def generate(self, prompt: str) -> str:
        if not self.use_secondary:
            try:
                return await self.primary.generate(prompt)
            except Exception as e:
                print(f"Primary LLM failed, switching to secondary: {e}")
                self.use_secondary = True
        
        return await self.secondary.generate(prompt)

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        if not self.use_secondary:
            try:
                return await self.primary.chat(messages)
            except Exception as e:
                print(f"Primary LLM failed, switching to secondary: {e}")
                self.use_secondary = True
        
        return await self.secondary.chat(messages)
