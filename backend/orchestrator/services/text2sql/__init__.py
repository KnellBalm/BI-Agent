"""
Text2SQL 서비스 모듈

자연어를 SQL로 변환하는 서비스를 제공합니다.
듀얼 모드 지원: Local (Ollama) + API (Gemini/Claude/OpenAI)
"""
from backend.orchestrator.services.text2sql.base import (
    BaseText2SQLService,
    Text2SQLResult
)
from backend.orchestrator.services.text2sql.local_service import LocalText2SQLService
from backend.orchestrator.services.text2sql.api_service import APIText2SQLService
from backend.orchestrator.services.text2sql.factory import Text2SQLServiceFactory

__all__ = [
    "BaseText2SQLService",
    "Text2SQLResult",
    "LocalText2SQLService",
    "APIText2SQLService",
    "Text2SQLServiceFactory",
]
