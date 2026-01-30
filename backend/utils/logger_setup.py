import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Global unified debug log setup
_unified_handler = None

def get_unified_debug_handler():
    """
    모든 모듈이 공유하는 통합 디버그 로그 핸들러를 반환합니다.
    프로젝트 루트 디렉토리에 bi-agent-debug.log를 생성합니다.
    """
    global _unified_handler
    if _unified_handler is None:
        # 프로젝트 루트 디렉토리 찾기 (backend의 상위 디렉토리)
        current_dir = Path(__file__).resolve().parent  # backend/utils
        project_root = current_dir.parent.parent  # BI-Agent root
        
        debug_log_path = project_root / "bi-agent-debug.log"
        
        formatter = logging.Formatter(
            '%(asctime)s - [%(name)s] - %(levelname)s - %(message)s - (%(filename)s:%(lineno)d)'
        )
        
        # 50MB 파일 크기, 5개 백업 유지
        _unified_handler = RotatingFileHandler(
            debug_log_path, 
            maxBytes=50*1024*1024, 
            backupCount=5, 
            encoding='utf-8'
        )
        _unified_handler.setLevel(logging.DEBUG)
        _unified_handler.setFormatter(formatter)
        
        # 루트 로거에 통합 핸들러 추가 (한 번만)
        root_logger = logging.getLogger()
        if _unified_handler not in root_logger.handlers:
            root_logger.addHandler(_unified_handler)
            root_logger.setLevel(logging.DEBUG)
    
    return _unified_handler

def setup_logger(name: str = "bi_agent", log_file: str = "bi_agent.log", level=logging.INFO):
    """
    Sets up a standardized logger with both console and rotating file handlers.
    모든 로거는 자동으로 통합 디버그 로그에도 기록됩니다.
    """
    # 통합 디버그 핸들러 초기화 (최초 1회만 실행됨)
    get_unified_debug_handler()
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_path = log_dir / log_file
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Console Handler (INFO 이상만 표시)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Module-specific File Handler (10MB per file, keep 3 backups)
    file_handler = RotatingFileHandler(
        log_path, maxBytes=10*1024*1024, backupCount=3, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Logger 자체는 DEBUG로 설정하여 모든 로그 캡처
    
    # Avoid duplicate handlers if setup is called multiple times
    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        logger.info(f"Logger '{name}' initialized with unified debug logging")
        
    return logger

# Default logger for general use
logger = setup_logger()

