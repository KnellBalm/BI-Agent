"""
HITL (Human-in-the-Loop) 인터럽트 시스템 (TASK-005)

주요 결정 지점에서 에이전트 실행을 일시 중단하고,
사용자의 승인/수정/반려를 받은 후 재개하는 시스템.

LangGraph의 Checkpointer + Interrupt 메커니즘을 활용합니다.

사용 예시:
    hitl = HITLManager()
    
    # 승인 요청 생성
    request = hitl.create_approval_request(
        step="SQL 실행",
        content="SELECT * FROM sales WHERE amount > 10000",
        risk_level="medium"
    )
    
    # 사용자 응답 처리 
    hitl.resolve(request.id, action="approve")
"""
import uuid
import json
import time
from enum import Enum
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path

from backend.utils.logger_setup import setup_logger

logger = setup_logger("hitl_manager", "hitl_manager.log")


class ApprovalAction(Enum):
    """사용자가 취할 수 있는 액션."""
    APPROVE = "approve"     # 승인
    MODIFY = "modify"       # 수정 후 진행
    REJECT = "reject"       # 반려 (중단)
    SKIP = "skip"           # 건너뛰기


class RiskLevel(Enum):
    """작업의 위험도 수준."""
    LOW = "low"             # 조회 등 비파괴적 작업
    MEDIUM = "medium"       # 데이터 변환, 차트 생성
    HIGH = "high"           # SQL 실행, 외부 API 호출
    CRITICAL = "critical"   # 데이터 삭제, 스키마 변경


@dataclass
class ApprovalRequest:
    """사용자 승인 요청 객체."""
    id: str
    step_name: str
    content: str
    risk_level: RiskLevel
    timestamp: float
    status: str = "pending"       # pending, approved, modified, rejected, skipped
    user_response: str = ""
    modified_content: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "step": self.step_name,
            "content": self.content,
            "risk_level": self.risk_level.value,
            "status": self.status,
            "user_response": self.user_response,
        }


class HITLManager:
    """
    Human-in-the-Loop 관리자.
    
    에이전트의 자율 실행 중 주요 결정 지점에서
    사용자에게 승인을 요청하고 결과를 기록합니다.
    
    ┌─────────────┐
    │ 에이전트 실행 │
    └──────┬──────┘
           │ HITL 체크포인트
    ┌──────▼──────┐
    │ 승인 요청    │ → 감사 로그 기록
    └──────┬──────┘
           │ 대기
    ┌──────▼──────────────────────────────┐
    │ 사용자 응답: 승인 / 수정 / 반려 / 건너뛰기 │
    └──────┬──────────────────────────────┘
           │
    ┌──────▼──────┐
    │ 실행 재개    │
    └─────────────┘
    """
    
    # 위험도에 따라 자동 승인 가능 여부 결정
    AUTO_APPROVE_LEVELS = {RiskLevel.LOW}
    
    def __init__(self, audit_log_dir: Optional[str] = None):
        self._pending: Dict[str, ApprovalRequest] = {}
        self._history: List[ApprovalRequest] = []
        self._callbacks: Dict[str, Callable] = {}
        
        # 감사 로그 경로
        log_dir = Path(audit_log_dir or str(Path.home() / ".bi-agent" / "logs"))
        log_dir.mkdir(parents=True, exist_ok=True)
        self._audit_log_path = log_dir / "hitl_approvals.jsonl"
    
    def create_approval_request(
        self,
        step: str,
        content: str,
        risk_level: str = "medium",
    ) -> ApprovalRequest:
        """승인 요청을 생성합니다.
        
        Args:
            step: 현재 단계 이름 (예: "SQL 실행", "차트 생성")
            content: 승인 대상 콘텐츠 (예: SQL 쿼리, 생성할 차트 설명)
            risk_level: 위험도 (low/medium/high/critical)
            
        Returns:
            ApprovalRequest 객체
        """
        request = ApprovalRequest(
            id=str(uuid.uuid4())[:8],
            step_name=step,
            content=content,
            risk_level=RiskLevel(risk_level),
            timestamp=time.time(),
        )
        
        # 낮은 위험도는 자동 승인
        if request.risk_level in self.AUTO_APPROVE_LEVELS:
            request.status = "approved"
            request.user_response = "자동 승인 (LOW 위험도)"
            self._history.append(request)
            self._write_audit_log(request)
            logger.info(f"[HITL] 자동 승인: {step} (risk={risk_level})")
            return request
        
        self._pending[request.id] = request
        logger.info(f"[HITL] 승인 대기: {request.id} — {step} (risk={risk_level})")
        self._write_audit_log(request)
        
        return request
    
    def resolve(
        self,
        request_id: str,
        action: str,
        modified_content: str = "",
        comment: str = "",
    ) -> ApprovalRequest:
        """사용자 응답으로 요청을 해결합니다.
        
        Args:
            request_id: 요청 ID
            action: approve/modify/reject/skip
            modified_content: modify 시 수정된 내용
            comment: 추가 코멘트
        """
        if request_id not in self._pending:
            raise ValueError(f"대기 중인 요청을 찾을 수 없습니다: {request_id}")
        
        request = self._pending.pop(request_id)
        approval_action = ApprovalAction(action)
        
        request.status = approval_action.value
        request.user_response = comment or f"사용자가 '{action}' 선택"
        
        if approval_action == ApprovalAction.MODIFY:
            request.modified_content = modified_content
        
        self._history.append(request)
        self._write_audit_log(request)
        
        logger.info(f"[HITL] 해결됨: {request_id} → {action}")
        
        # 콜백 실행
        if request_id in self._callbacks:
            self._callbacks[request_id](request)
            del self._callbacks[request_id]
        
        return request
    
    def should_interrupt(self, step: str, risk_level: str = "medium") -> bool:
        """이 단계에서 인터럽트가 필요한지 판단합니다."""
        level = RiskLevel(risk_level)
        return level not in self.AUTO_APPROVE_LEVELS
    
    def get_pending_requests(self) -> List[ApprovalRequest]:
        """대기 중인 모든 승인 요청을 반환합니다."""
        return list(self._pending.values())
    
    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """최근 승인 이력을 반환합니다."""
        return [r.to_dict() for r in self._history[-limit:]]
    
    def on_resolve(self, request_id: str, callback: Callable):
        """요청 해결 시 호출할 콜백을 등록합니다."""
        self._callbacks[request_id] = callback
    
    def _write_audit_log(self, request: ApprovalRequest):
        """감사 로그를 JSONL 파일에 기록합니다."""
        try:
            log_entry = request.to_dict()
            log_entry["timestamp"] = request.timestamp
            with open(self._audit_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"감사 로그 기록 실패: {e}")
