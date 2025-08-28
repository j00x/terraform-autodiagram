"""
Logging configuration for TerraVision.

This module provides centralized logging configuration for the entire application.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> None:
    """
    Configure logging for TerraVision application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file. If None, logs only to console.
    """
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    simple_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler with simple format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with detailed format (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)  # Always debug level for files
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)
    
    # Configure specific loggers
    _configure_module_loggers(log_level)


def _configure_module_loggers(log_level: str) -> None:
    """Configure logging for specific modules."""
    # Reduce verbosity of third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    # Set TerraVision module loggers to specified level
    terravision_modules = [
        'modules.graphmaker',
        'modules.fileparser', 
        'modules.interpreter',
        'modules.drawing',
        'modules.tfwrapper',
        'modules.annotations',
        'modules.helpers',
        'modules.resource_handlers'
    ]
    
    for module_name in terravision_modules:
        logger = logging.getLogger(module_name)
        logger.setLevel(getattr(logging, log_level.upper()))


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the specified module.
    
    Args:
        name: Module name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


class PerformanceTimer:
    """Context manager for timing operations and logging performance metrics."""
    
    def __init__(self, logger: logging.Logger, operation_name: str):
        self.logger = logger
        self.operation_name = operation_name
        self.start_time = None
    
    def __enter__(self):
        import time
        self.start_time = time.time()
        self.logger.debug(f"Starting {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        elapsed = time.time() - self.start_time
        if exc_type is None:
            self.logger.info(f"Completed {self.operation_name} in {elapsed:.3f}s")
        else:
            self.logger.error(f"Failed {self.operation_name} after {elapsed:.3f}s: {exc_val}")


def log_function_call(logger: logging.Logger):
    """Decorator to log function entry and exit with parameters."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger.debug(f"Entering {func.__name__} with args={len(args)}, kwargs={list(kwargs.keys())}")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"Exiting {func.__name__} successfully")
                return result
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {type(e).__name__}: {e}")
                raise
        return wrapper
    return decorator
