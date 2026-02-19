"""
SQLite Checkpointer 통합 (TASK-002)

LangGraph의 상태(State)를 SQLite에 영구 저장하여,
프로세스 재시작 후에도 분석 세션을 이어갈 수 있게 합니다.
HITL(Human-in-the-Loop) 패턴의 핵심 기반 기술입니다.
"""
import sqlite3
from pathlib import Path
from typing import Optional

from langgraph.checkpoint.sqlite import SqliteSaver

from backend.utils.logger_setup import setup_logger

logger = setup_logger("checkpointer", "checkpointer.log")

# 기본 체크포인트 저장 경로
DEFAULT_CHECKPOINT_DIR = Path.home() / ".bi-agent" / "checkpoints"


def get_checkpointer(db_path: Optional[str] = None) -> SqliteSaver:
    """
    SQLite 기반 LangGraph Checkpointer를 생성합니다 (동기 버전).
    
    Args:
        db_path: SQLite DB 파일 경로. None이면 기본 경로 사용.
        
    Returns:
        SqliteSaver 인스턴스 (graph.compile(checkpointer=...) 에 전달)
        
    사용 예시:
        checkpointer = get_checkpointer()
        workflow = graph.compile(checkpointer=checkpointer)
    """
    if db_path is None:
        DEFAULT_CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        db_path = str(DEFAULT_CHECKPOINT_DIR / "langgraph_state.db")
    
    logger.info(f"체크포인터 초기화: {db_path}")
    conn = sqlite3.connect(db_path, check_same_thread=False)
    return SqliteSaver(conn)
