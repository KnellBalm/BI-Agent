import os
import json
import traceback
import datetime
from typing import Any, Dict, Optional
from backend.utils.path_config import path_manager

class DiagnosticLogger:
    """
    Records structured error logs in JSONL format for AI-based diagnostics.
    Saves to ~/.bi-agent/logs/diagnostic_errors.jsonl
    """
    
    def __init__(self, project_id: str = "default"):
        self.project_id = project_id
        # 프로젝트 루트의 logs 디렉토리 사용 (작업 디렉토리 기준)
        import pathlib
        project_root = pathlib.Path(__file__).parent.parent.parent  # backend/utils/../.. -> 프로젝트 루트
        self.log_dir = project_root / "logs"
        self.log_file = self.log_dir / "diagnostic_errors.jsonl"
        self._ensure_log_dir()

    def _ensure_log_dir(self):
        os.makedirs(self.log_dir, exist_ok=True)

    def log_error(self, error_type: str, message: str, context: Optional[Dict[str, Any]] = None):
        """Logs an error with full traceback and context."""
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "project_id": self.project_id,
            "error_type": error_type,
            "message": message,
            "traceback": traceback.format_exc(),
            "context": context or {}
        }
        
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            # Fallback to standard print if file logging fails
            print(f"FAILED TO WRITE DIAGNOSTIC LOG: {e}")

    def log_success(self, event_type: str, message: str, context: Optional[Dict[str, Any]] = None):
        """Logs a successful event for diagnostic purposes."""
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "project_id": self.project_id,
            "event_type": event_type,
            "status": "SUCCESS",
            "message": message,
            "context": context or {}
        }
        
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"FAILED TO WRITE SUCCESS LOG: {e}")

    def get_last_error(self) -> Optional[Dict[str, Any]]:
        """Retrieves the most recent error entry."""
        if not os.path.exists(self.log_file):
            return None
        
        try:
            with open(self.log_file, "rb") as f:
                f.seek(0, os.SEEK_END)
                # Simple tail logic for smallish log files
                # For robust implementation, we'd read chunks backwards
                lines = f.readlines()
                if lines:
                    return json.loads(lines[-1].decode("utf-8"))
        except:
            return None
        return None

# Global instance for easy access
diagnostic_logger = DiagnosticLogger()
