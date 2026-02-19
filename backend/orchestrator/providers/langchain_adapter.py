"""
LangChain ChatModel Adapter (TASK-001)

기존의 커스텀 LLMProvider를 LangChain의 BaseChatModel 인터페이스로 래핑합니다.
이를 통해 기존의 Quota 관리, Failover 로직을 유지하면서도
LangChain의 Tool Calling, Output Parser 등 생태계를 활용할 수 있습니다.
"""
import asyncio
from typing import Any, List, Optional, Iterator, AsyncIterator

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.callbacks.manager import CallbackManagerForLLMRun, AsyncCallbackManagerForLLMRun

from backend.orchestrator.providers.llm_provider import (
    LLMProvider, FailoverLLMProvider, GeminiProvider, OllamaProvider,
    ClaudeProvider, OpenAIProvider
)
from backend.utils.logger_setup import setup_logger

logger = setup_logger("langchain_adapter", "langchain_adapter.log")


class BIAgentChatModel(BaseChatModel):
    """
    BI-Agent의 커스텀 LLMProvider를 LangChain ChatModel로 래핑하는 어댑터.
    
    기존의 FailoverLLMProvider(Gemini→Claude→GPT→Ollama) 전략과
    QuotaManager를 그대로 유지하면서, LangChain의 chain/tool 생태계에 연결합니다.
    
    사용 예시:
        from backend.orchestrator.providers.langchain_adapter import BIAgentChatModel
        
        model = BIAgentChatModel()
        result = model.invoke("매출 데이터를 분석해줘")
    """
    
    # Pydantic v2 필드 선언
    provider: Any = None  # LLMProvider 인스턴스
    model_name: str = "bi-agent-failover"
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(self, provider: Optional[LLMProvider] = None, **kwargs):
        """
        Args:
            provider: 기존 LLMProvider 인스턴스. None이면 FailoverLLMProvider 자동 생성.
        """
        super().__init__(**kwargs)
        if provider is None:
            # 기본값: 기존 Failover 체인 (Gemini → Claude → OpenAI → Ollama)
            self.provider = FailoverLLMProvider([
                GeminiProvider(),
                ClaudeProvider(),
                OpenAIProvider(),
                OllamaProvider(),
            ])
            self.model_name = "bi-agent-failover"
        else:
            self.provider = provider
            self.model_name = provider.__class__.__name__

    @property
    def _llm_type(self) -> str:
        """LangChain이 요구하는 모델 타입 식별자."""
        return f"bi-agent-{self.model_name}"
    
    def _convert_messages_to_prompt(self, messages: List[BaseMessage]) -> str:
        """LangChain BaseMessage 리스트를 단일 프롬프트 문자열로 변환."""
        parts = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                parts.append(f"[System] {msg.content}")
            elif isinstance(msg, HumanMessage):
                parts.append(f"[User] {msg.content}")
            elif isinstance(msg, AIMessage):
                parts.append(f"[Assistant] {msg.content}")
            else:
                parts.append(msg.content)
        return "\n".join(parts)
    
    def _convert_messages_to_chat_format(self, messages: List[BaseMessage]) -> List[dict]:
        """LangChain BaseMessage 리스트를 기존 Provider의 chat() 형식으로 변환."""
        chat_messages = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                chat_messages.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                chat_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                chat_messages.append({"role": "assistant", "content": msg.content})
            else:
                chat_messages.append({"role": "user", "content": msg.content})
        return chat_messages

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """동기 호출 (내부적으로 asyncio 사용)."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        
        if loop and loop.is_running():
            # 이미 이벤트 루프가 돌고 있는 경우 (예: Textual TUI 내부)
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(
                    asyncio.run, self._agenerate(messages, stop, run_manager=None, **kwargs)
                ).result()
                return result
        else:
            return asyncio.run(self._agenerate(messages, stop, run_manager=None, **kwargs))
    
    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """비동기 호출 - 기존 Provider의 generate/chat를 활용."""
        try:
            # chat() 메서드가 있는 Provider는 메시지 형식으로 호출
            chat_messages = self._convert_messages_to_chat_format(messages)
            response_text = await self.provider.chat(chat_messages)
        except Exception as e:
            logger.warning(f"chat() 호출 실패, generate()로 폴백: {e}")
            # chat() 실패 시 단일 프롬프트로 폴백
            prompt = self._convert_messages_to_prompt(messages)
            response_text = await self.provider.generate(prompt)
        
        # stop 시퀀스 처리
        if stop:
            for s in stop:
                if s in response_text:
                    response_text = response_text[:response_text.index(s)]
        
        message = AIMessage(content=response_text)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])
