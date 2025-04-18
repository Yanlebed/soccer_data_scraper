"""
Logging configuration for the Totalcorner scraper.
"""
import logging
import os
from pathlib import Path

def setup_logger(name: str = "totalcorner_scraper", level: int = logging.INFO) -> logging.Logger:
    """
    Set up and configure a logger instance.
    
    Args:
        name: Logger name
        level: Logging level
        
    Returns:
        Configured logger instance
    """
    # Check if running in Lambda (AWS_LAMBDA_FUNCTION_NAME environment variable exists)
    is_lambda = os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None

    # Configure the logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Clear any existing handlers
    if logger.handlers:
        logger.handlers = []

    # Create formatters
    log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    if is_lambda:
        # In Lambda, just use console output (no file handlers)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_format)
        logger.addHandler(console_handler)
    else:
        # For local development, use both file and console handlers
        # Create logs directory if it doesn't exist
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        # File handler
        file_handler = logging.FileHandler(logs_dir / f"{name}.log")
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_format)
        logger.addHandler(console_handler)

    return logger