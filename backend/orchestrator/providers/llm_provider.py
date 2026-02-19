import asyncio
import os
from google import genai
from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional, Union
import anthropic
from openai import AsyncOpenAI
from dotenv import load_dotenv
from backend.orchestrator.managers.quota_manager import quota_manager
from backend.utils.logger_setup import setup_logger

load_dotenv()

logger = setup_logger("llm_provider", "llm_provider.log")

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
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = None

    async def _ensure_active_key(self) -> str:
        """할당량이 남아있는 유효한 키 또는 토큰을 확보합니다."""
        from backend.orchestrator import auth_manager
        
        provider_data = auth_manager.get_provider_data("gemini")
        api_key = provider_data.get("key") or os.getenv("GEMINI_API_KEY")
        token = provider_data.get("token")

        if not api_key and not token:
             raise ValueError("계정 인증이 필요합니다. TUI 메인 화면에서 로그인을 진행해주거나 API Key를 설정해 주세요.")

        # API Key 우선 사용
        if api_key:
            self.client = genai.Client(api_key=api_key)
            return api_key
        
        # TODO: OAuth Token 사용 로직 (google-auth Credentials 객체 생성 필요)
        # 현재는 안내 메시지로 대체
        raise NotImplementedError("OAuth 토큰 기반 인증은 개발 중입니다. 현재는 API Key를 사용해 주세요.")

    async def generate(self, prompt: str) -> str:
        if not quota_manager.can_use_provider("gemini"):
            # Fallback will be handled by FailoverLLMProvider if used
            raise RuntimeError("Gemini 할당량이 가득 찼거나 이미 소진되었습니다.")

        current_key = await self._ensure_active_key()
        try:
            # google-genai (new SDK)는 동기/비동기 모두 지원하지만 여기선 thread 유지
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt
            )
            quota_manager.increment_usage("gemini")
            return response.text
        except Exception as e:
            if "429" in str(e):
                quota_manager.report_limit_reached("gemini")
            raise e

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        if not quota_manager.can_use_provider("gemini"):
            raise RuntimeError("Gemini 할당량이 가득 찼거나 이미 소진되었습니다.")

        current_key = await self._ensure_active_key()
        try:
            # 전체 메시지를 contents 리스트로 변환
            # Gemini contents는 'user'와 'model' role만 지원
            contents = []
            for msg in messages:
                role = msg["role"]
                if role == "system":
                    role = "user"  # system → user로 매핑
                elif role == "assistant":
                    role = "model"  # assistant → model로 매핑
                contents.append({
                    "role": role,
                    "parts": [{"text": msg["content"]}]
                })
            
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=contents,
            )
            quota_manager.increment_usage("gemini")
            return response.text
        except Exception as e:
            if "429" in str(e):
                quota_manager.report_limit_reached("gemini")
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

class ClaudeProvider(LLMProvider):
    """
    Anthropic Claude API를 사용한 구현
    """
    def __init__(self, model_name: str = "claude-3-5-sonnet-20241022"):
        self.model_name = model_name
        self._setup_client()

    def _setup_client(self):
        from backend.orchestrator import auth_manager
        api_key = auth_manager.get_provider_data("claude").get("key") or os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            self.client = anthropic.AsyncAnthropic(api_key=api_key)
        else:
            self.client = None

    async def generate(self, prompt: str) -> str:
        if not self.client: return "Claude API Key가 설정되지 않았습니다."
        if not quota_manager.can_use_provider("claude"):
            raise RuntimeError("Claude 할당량이 가득 찼습니다.")

        try:
            response = await self.client.messages.create(
                model=self.model_name,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            quota_manager.increment_usage("claude")
            return response.content[0].text
        except Exception as e:
            if "429" in str(e):
                quota_manager.report_limit_reached("claude")
            raise e

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        if not self.client: return "Claude API Key가 설정되지 않았습니다."
        if not quota_manager.can_use_provider("claude"):
            raise RuntimeError("Claude 할당량이 가득 찼습니다.")

        # Claude format conversion (system prompt adjustment might be needed elsewhere)
        claude_messages = []
        for msg in messages:
            claude_messages.append({"role": msg["role"], "content": msg["content"]})
        
        try:
            response = await self.client.messages.create(
                model=self.model_name,
                max_tokens=4096,
                messages=claude_messages
            )
            quota_manager.increment_usage("claude")
            return response.content[0].text
        except Exception as e:
            if "429" in str(e):
                quota_manager.report_limit_reached("claude")
            raise e

class OpenAIProvider(LLMProvider):
    """
    OpenAI ChatGPT API를 사용한 구현
    """
    def __init__(self, model_name: str = "gpt-4o"):
        self.model_name = model_name
        self._setup_client()

    def _setup_client(self):
        from backend.orchestrator import auth_manager
        api_key = auth_manager.get_provider_data("openai").get("key") or os.getenv("OPENAI_API_KEY")
        if api_key:
            self.client = AsyncOpenAI(api_key=api_key)
        else:
            self.client = None

    async def generate(self, prompt: str) -> str:
        if not self.client: return "OpenAI API Key가 설정되지 않았습니다."
        if not quota_manager.can_use_provider("openai"):
            raise RuntimeError("OpenAI 할당량이 가득 찼습니다.")

        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}]
            )
            quota_manager.increment_usage("openai")
            return response.choices[0].message.content
        except Exception as e:
            if "429" in str(e):
                quota_manager.report_limit_reached("openai")
            raise e

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        if not self.client: return "OpenAI API Key가 설정되지 않았습니다."
        if not quota_manager.can_use_provider("openai"):
            raise RuntimeError("OpenAI 할당량이 가득 찼습니다.")

        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages
            )
            quota_manager.increment_usage("openai")
            return response.choices[0].message.content
        except Exception as e:
            if "429" in str(e):
                quota_manager.report_limit_reached("openai")
            raise e

class FailoverLLMProvider(LLMProvider):
    """
    여러 LLM 공급자를 순차적으로 시도하는 공급자 (Gemini -> Claude -> GPT -> Ollama)
    """
    def __init__(self, providers: List[LLMProvider]):
        self.providers = providers
        self.current_index = 0

    async def generate(self, prompt: str) -> str:
        # 가용한 공급자를 찾을 때까지 순회
        for provider in self.providers:
            provider_name = provider.__class__.__name__.lower().replace("provider", "")
            if quota_manager.can_use_provider(provider_name):
                try:
                    return await provider.generate(prompt)
                except Exception as e:
                    logger.error(f"Provider {provider_name} failed: {e}")
                    continue
        return "모든 유료 구독 및 무료 Fallback LLM 공급자가 응답에 실패했거나 할당량이 소진되었습니다."

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        for i in range(self.current_index, len(self.providers)):
            try:
                result = await self.providers[i].chat(messages)
                self.current_index = i
                return result
            except Exception as e:
                print(f"Provider {i} failed: {e}")
                continue
        return "모든 LLM 공급자가 응답에 실패했습니다."
