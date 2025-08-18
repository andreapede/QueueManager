"""
Logger setup for Queue Management System
"""

import logging
import logging.handlers
import os
from datetime import datetime

from config.config import Config

def setup_logger(name: str = 'QueueManager') -> logging.Logger:
    """Setup logger with file and console handlers"""
    
    # Create logger
    logger = logging.getLogger(name)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Set level from config
    level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    try:
        # Ensure log directory exists
        log_dir = os.path.dirname(Config.LOG_FILE)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        # Rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            Config.LOG_FILE,
            maxBytes=Config.LOG_MAX_BYTES,
            backupCount=Config.LOG_BACKUP_COUNT
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
    except Exception as e:
        logger.warning(f"Failed to setup file logging: {e}")
    
    logger.info(f"Logger '{name}' initialized with level {Config.LOG_LEVEL}")
    return logger
