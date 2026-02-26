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
        try:
            _unified_handler = RotatingFileHandler(
                debug_log_path, 
                maxBytes=50*1024*1024, 
                backupCount=5, 
                encoding='utf-8'
            )
            _unified_handler.setLevel(logging.DEBUG)
            _unified_handler.setFormatter(formatter)
        except PermissionError:
            # SIP-protected files, fall back to StreamHandler
            import sys
            _unified_handler = logging.StreamHandler(sys.stderr)
            _unified_handler.setLevel(logging.DEBUG)
            _unified_handler.setFormatter(formatter)
            print(f"Warning: Could not create debug log file (SIP), using stderr", file=sys.stderr)
        
        # 루트 로거에 통합 핸들러 추가 (한 번만)
        root_logger = logging.getLogger()
        if _unified_handler not in root_logger.handlers:
            # 기존 StreamHandler 제거 (콘솔 노출 방지)
            for h in root_logger.handlers[:]:
                if isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler):
                    root_logger.removeHandler(h)
            root_logger.addHandler(_unified_handler)
            root_logger.setLevel(logging.DEBUG)
            
            # 외부 라이브러리 로거 콘솔 노출 억제
            for noisy in ("httpcore", "httpx", "google_genai", "urllib3",
                          "google.auth", "google.auth.transport", "hpack"):
                logging.getLogger(noisy).setLevel(logging.WARNING)
    
    return _unified_handler

def setup_logger(name: str = "bi_agent", log_file: str = "bi_agent.log", level=logging.INFO):
    """
    Sets up a standardized logger with both console and rotating file handlers.
    모든 로거는 자동으로 통합 디버그 로그에도 기록됩니다.
    """
    # 통합 디버그 핸들러 사용
    get_unified_debug_handler()
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_path = log_dir / log_file
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Console Handler (WARNING 이상만 표시 — 사용자에게 불필요한 로그 숨김)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)

    # Module-specific File Handler (10MB per file, keep 3 backups)
    file_handler = None
    try:
        file_handler = RotatingFileHandler(
            log_path, maxBytes=10*1024*1024, backupCount=3, encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
    except PermissionError:
        # SIP-protected files, skip module-specific file logging
        import sys
        print(f"Warning: Could not create module-specific log file '{log_path}' (SIP), skipping file logging for '{name}'", file=sys.stderr)


    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Logger 자체는 DEBUG로 설정하여 모든 로그 캡처
    
    # Avoid duplicate handlers if setup is called multiple times
    if not logger.handlers:
        logger.addHandler(console_handler)
        if file_handler is not None:
            logger.addHandler(file_handler)
        logger.info(f"Logger '{name}' initialized with unified debug logging")
        
    return logger

# Default logger for general use
logger = setup_logger()
