"""
University ERP — Logging Utility

Class-based logger (no global state).  Configuration is read
from settings.yaml at construction time.
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Any, Optional


class ERPLogger:
    """
    Factory / wrapper that provides pre-configured loggers.

    Usage:
        logger = ERPLogger.get_logger("student_service")
        logger.info("Student registered", extra={...})
    """

    _initialised: bool = False
    _default_level: int = logging.DEBUG
    _default_format: str = (
        "%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s"
    )
    _log_file: Optional[str] = None
    _max_bytes: int = 10_485_760  # 10 MB
    _backup_count: int = 5

    @classmethod
    def configure(
        cls,
        *,
        level: str = "DEBUG",
        fmt: Optional[str] = None,
        log_file: Optional[str] = None,
        max_bytes: int = 10_485_760,
        backup_count: int = 5,
    ) -> None:
        """
        One-time global configuration — called once from main.py
        after reading settings.yaml.
        """
        cls._default_level = getattr(logging, level.upper(), logging.DEBUG)
        if fmt:
            cls._default_format = fmt
        cls._log_file = log_file
        cls._max_bytes = max_bytes
        cls._backup_count = backup_count
        cls._initialised = True

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Return a named logger with consistent formatting.
        Idempotent — handlers are only added on the first call
        for a given name.
        """
        logger = logging.getLogger(name)

        if logger.handlers:
            return logger  # already configured

        logger.setLevel(cls._default_level)
        formatter = logging.Formatter(cls._default_format)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler (if a path was provided)
        if cls._log_file:
            log_dir = os.path.dirname(cls._log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            file_handler = RotatingFileHandler(
                cls._log_file,
                maxBytes=cls._max_bytes,
                backupCount=cls._backup_count,
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger
