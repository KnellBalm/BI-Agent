from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from backend.orchestrator.providers.llm_provider import LLMProvider
from backend.orchestrator.managers.connection_manager import ConnectionManager

class AbstractOrchestrator(ABC):
    """
    BI-Agent Orchestrator 추상 베이스 클래스.
    모든 오케스트레이션 엔진(LangGraph, Collaborative 등)은 이 클래스를 상속받아야 합니다.
    """
    
    def __init__(self, 
                 llm: Optional[LLMProvider] = None, 
                 connection_manager: Optional[ConnectionManager] = None):
        self.llm = llm
        self.connection_manager = connection_manager

    @abstractmethod
    async def run(self, user_query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        사용자 쿼리를 처리하고 결과를 반환합니다.
        
        Args:
            user_query: 사용자 입력 문자열
            context: 실행 컨텍스트 (연결 정보 등)
            
        Returns:
            Dict[str, Any]: 실행 결과 (final_response, data_result 등)
        """
        pass
