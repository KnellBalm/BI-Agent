import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logger(name: str = "bi_agent", log_file: str = "bi_agent.log", level=logging.INFO):
    """
    Sets up a standardized logger with both console and rotating file handlers.
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_path = log_dir / log_file
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Rotating File Handler (10MB per file, keep 3 backups)
    file_handler = RotatingFileHandler(
        log_path, maxBytes=10*1024*1024, backupCount=3, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers if setup is called multiple times
    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
    return logger

# Default logger for general use
logger = setup_logger()
