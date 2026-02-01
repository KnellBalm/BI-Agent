"""
Approval Logger
Audit logging for user approvals and rejections in the BI-Agent system.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import json
from backend.utils.logger_setup import setup_logger

logger = setup_logger("approval_logger", "approval_logger.log")


@dataclass
class ApprovalEvent:
    """
    Represents a single approval or rejection event.
    
    Attributes:
        timestamp: When the event occurred
        action: Type of action (approve, reject, edit, batch_approve)
        target_type: What was approved (hypothesis, constraint, table, pipeline)
        target_id: Identifier for the target
        user_action: Keyboard shortcut used (Y, Shift+Y, N, E, etc.)
        context: Additional context data
    """
    timestamp: datetime
    action: str
    target_type: str
    target_id: str
    user_action: str
    context: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        return d


class ApprovalLogger:
    """
    Logger for user approval events with JSONL persistence.
    
    Logs all user approval/rejection actions to logs/approvals.jsonl
    for audit trail and analytics.
    """
    
    def __init__(self, log_path: Optional[Path] = None):
        """
        Initialize approval logger.
        
        Args:
            log_path: Path to log file (default: logs/approvals.jsonl)
        """
        if log_path is None:
            log_path = Path("logs/approvals.jsonl")
        
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"ApprovalLogger initialized with log path: {self.log_path}")
    
    def log_approval(self, event: ApprovalEvent) -> None:
        """
        Log an approval event to file.
        
        Args:
            event: ApprovalEvent to log
        """
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
            
            logger.info(
                f"Logged {event.action} for {event.target_type}:{event.target_id} "
                f"via {event.user_action}"
            )
        except Exception as e:
            logger.error(f"Failed to log approval event: {e}")
    
    def get_recent_events(self, limit: int = 100) -> list[ApprovalEvent]:
        """
        Get recent approval events.
        
        Args:
            limit: Maximum number of events to return
        
        Returns:
            List of recent ApprovalEvent objects
        """
        events = []
        
        if not self.log_path.exists():
            return events
        
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
            # Get last N lines
            for line in lines[-limit:]:
                data = json.loads(line)
                data['timestamp'] = datetime.fromisoformat(data['timestamp'])
                events.append(ApprovalEvent(**data))
        
        except Exception as e:
            logger.error(f"Failed to read approval events: {e}")
        
        return events
    
    def clear_log(self) -> None:
        """Clear the approval log file"""
        if self.log_path.exists():
            self.log_path.unlink()
            logger.info("Approval log cleared")
