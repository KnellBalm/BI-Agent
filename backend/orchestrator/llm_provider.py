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

    async def _ensure_active_key(self) -> Optional[str]:
        """할당량이 남아있는 유효한 키를 확보합니다."""
        if not self.quota_manager:
            return os.getenv("GEMINI_API_KEY")
        
        active_config = await self.quota_manager.get_active_key_config()
        if active_config:
            genai.configure(api_key=active_config['key'])
            self.model = genai.GenerativeModel(self.model_name)
            return active_config['key']
        elif not self.model:
             raise ValueError("No active GEMINI_API_KEY found and QuotaManager is missing or has no keys.")
        return os.getenv("GEMINI_API_KEY")

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
    Ollama (로컬 LLM)를 사용한 구현 (향후 활용)
    """
    def __init__(self, base_url: str = 'http://localhost:11434', model: str = 'llama3'):
        self.base_url = base_url
        self.model = model

    def generate(self, prompt: str) -> str:
        # requests를 사용한 Ollama API 호출 구현
        return "Ollama provider is not fully implemented yet."

    def chat(self, messages: List[Dict[str, str]]) -> str:
        return "Ollama provider chat is not fully implemented yet."
