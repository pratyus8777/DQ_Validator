"""
Logging configuration for the DQ_PE platform.
Provides centralized logging with file and console output.
"""

import logging
import logging.handlers
import os
from datetime import datetime


def setup_logging(log_dir: str = "output", log_level: str = "INFO") -> logging.Logger:
    """
    Initialize and configure logging for the application.
    
    Args:
        log_dir: Directory to store log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    os.makedirs(log_dir, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger("dq_pe")
    logger.setLevel(getattr(logging, log_level))
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    log_filename = os.path.join(
        log_dir,
        f"dq_pe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )
    file_handler = logging.handlers.RotatingFileHandler(
        log_filename,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5
    )
    file_handler.setLevel(getattr(logging, log_level))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Module name
    
    Returns:
        Logger instance
    """
    return logging.getLogger(f"dq_pe.{name}")
