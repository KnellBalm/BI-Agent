import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class ContextManager:
    """
    사용자의 분석 세션 내에서 '활성 컨텍스트(Active Context)'를 관리합니다.
    탐색(Explore)된 테이블 정보와 현재 여정의 단계(Journey Step)를 유지하여
    분석(Analyze) 시 연속성 있는 경험을 제공합니다.
    """
    def __init__(self):
        self.active_conn_id: Optional[str] = None
        self.active_table: Optional[str] = None
        self.active_schema: Optional[Dict[str, Any]] = None
        self.journey_step: int = 0  # 0: Launch, 1: Auth, 2: Connect, 3: Explore, 4: Pin, 5: Analyze, 6: Result
        self.last_sync: datetime = datetime.now()
        
    def set_active_table(self, conn_id: str, table_name: str, schema: Optional[Dict[str, Any]] = None):
        """활성 테이블을 설정하고 여정 단계를 'Explore'로 업데이트합니다."""
        self.active_conn_id = conn_id
        self.active_table = table_name
        self.active_schema = schema
        self.journey_step = max(self.journey_step, 4)  # Table Pinned
        self.last_sync = datetime.now()
        logger.info(f"Context updated: {conn_id}.{table_name} (Step: {self.journey_step})")

    def update_journey_step(self, step: int):
        """여정의 현재 단계를 업데이트합니다."""
        if step > self.journey_step:
            self.journey_step = step
            self.last_sync = datetime.now()
            logger.info(f"Journey step progressed to: {step}")

    def get_context_summary(self) -> str:
        """현재 컨텍스트의 요약 정보를 반환합니다 (사이드바 노출용)."""
        if not self.active_table:
            return "No active table selected"
        return f"{self.active_conn_id}.{self.active_table}"

    def reset_context(self):
        """컨텍스트를 초기화합니다."""
        self.active_conn_id = None
        self.active_table = None
        self.active_schema = None
        # journey_step은 유지하거나 상황에 따라 초기화
        logger.info("Context reset")

# Global instance for the session
context_manager = ContextManager()
