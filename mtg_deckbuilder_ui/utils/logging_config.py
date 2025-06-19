# mtg_deckbuilder_ui/utils/logging_config.py

"""
logging_config.py

Provides centralized logging configuration for the MTG Deckbuilder application.
This module allows customization of log levels via app_config and sets up consistent
logging across all modules in the application.
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Default configuration
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DIRECTORY = "logs"

# Dictionary mapping string log level names to their numeric values
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def get_log_level(level_name):
    """Convert string log level to numeric log level"""
    return LOG_LEVELS.get(level_name.upper(), DEFAULT_LOG_LEVEL)


def setup_logging(app_config=None, log_to_file=True, log_to_console=True):
    """
    Configure the root logger for the application

    Args:
        app_config: Application configuration object with log settings
        log_to_file: Whether to log to a file
        log_to_console: Whether to log to console

    Returns:
        logging.Logger: Configured root logger
    """
    # Create logs directory if logging to file
    if log_to_file:
        log_dir = Path(LOG_DIRECTORY)
        log_dir.mkdir(exist_ok=True)

    # Get log level from config, with fallback to default
    log_level = DEFAULT_LOG_LEVEL
    if app_config:
        try:
            log_level_name = app_config.get("Logging", "log_level", "INFO")
            log_level = get_log_level(log_level_name)
        except Exception as e:
            print(f"Error getting log level from config: {e}")

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create formatters
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT)

    # Add console handler if requested
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # Add file handler if requested
    if log_to_file:
        log_file = os.path.join(LOG_DIRECTORY, "mtg_deckbuilder.log")
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10_485_760, backupCount=5  # 10 MB
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    return root_logger


def get_logger(name):
    """
    Get a logger for a specific module with the configured settings

    Args:
        name: Name of the module requesting the logger

    Returns:
        logging.Logger: Logger for the specified module
    """
    return logging.getLogger(name)
