"""Utilities module for trading module."""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


class Logger:
    """Centralized logging configuration."""
    
    _logger: Optional[logging.Logger] = None
    
    @classmethod
    def setup(cls, 
              log_file: Optional[Path] = None,
              level: str = "INFO") -> logging.Logger:
        """Set up and configure logger.
        
        Args:
            log_file: Path to log file. If None, logs to console only.
            level: Logging level (INFO, DEBUG, WARNING, ERROR).
        
        Returns:
            Configured logger instance.
        """
        if cls._logger:
            return cls._logger
        
        cls._logger = logging.getLogger("Trading")
        cls._logger.setLevel(getattr(logging, level.upper()))
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        
        # Format
        formatter = logging.Formatter(
            '[%(asctime)s - %(name)s - %(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        cls._logger.addHandler(console_handler)
        
        # File handler
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(getattr(logging, level.upper()))
            file_handler.setFormatter(formatter)
            cls._logger.addHandler(file_handler)
        
        return cls._logger
    
    @classmethod
    def get(cls) -> logging.Logger:
        """Get configured logger instance."""
        if cls._logger is None:
            cls.setup()
        return cls._logger
