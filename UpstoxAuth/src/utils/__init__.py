"""Utilities module for HFT application."""

import logging
import sys
from pathlib import Path
from datetime import datetime, time, timedelta
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
        
        cls._logger = logging.getLogger("HFT")
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


class TimeUtils:
    """Utility functions for time calculations."""
    
    @staticmethod
    def get_token_expiry_time(current_time: Optional[datetime] = None) -> datetime:
        """Calculate token expiry time (3:30 AM IST next day).
        
        Args:
            current_time: Current datetime. If None, uses current system time.
        
        Returns:
            Datetime object for token expiry.
        """
        if current_time is None:
            current_time = datetime.now()
        
        expiry = current_time.replace(hour=3, minute=30, second=0, microsecond=0)
        
        # If current time is before 3:30 AM, expiry is today's 3:30 AM
        # If current time is at or after 3:30 AM, expiry is tomorrow's 3:30 AM
        if current_time.time() >= time(3, 30):
            expiry += timedelta(days=1)
        
        return expiry
    
    @staticmethod
    def is_token_expired(issued_time: datetime, 
                        current_time: Optional[datetime] = None) -> bool:
        """Check if token has expired based on expiry rules.
        
        Args:
            issued_time: When the token was issued.
            current_time: Current time for checking. If None, uses system time.
        
        Returns:
            True if token has expired, False otherwise.
        """
        if current_time is None:
            current_time = datetime.now()
        
        expiry_time = TimeUtils.get_token_expiry_time(issued_time)
        return current_time >= expiry_time
    
    @staticmethod
    def get_time_until_expiry(issued_time: datetime,
                             current_time: Optional[datetime] = None) -> timedelta:
        """Get remaining time until token expiry.
        
        Args:
            issued_time: When the token was issued.
            current_time: Current time for calculation. If None, uses system time.
        
        Returns:
            Timedelta representing time until expiry.
        """
        if current_time is None:
            current_time = datetime.now()
        
        expiry_time = TimeUtils.get_token_expiry_time(issued_time)
        remaining = expiry_time - current_time
        
        return remaining if remaining.total_seconds() > 0 else timedelta(0)
    
    @staticmethod
    def datetime_to_timestamp_ms(dt: datetime) -> int:
        """Convert datetime to milliseconds since epoch."""
        return int(dt.timestamp() * 1000)
    
    @staticmethod
    def timestamp_ms_to_datetime(ts_ms: int) -> datetime:
        """Convert milliseconds since epoch to datetime."""
        return datetime.fromtimestamp(ts_ms / 1000)


class ErrorHandler:
    """Centralized error handling."""
    
    logger = Logger.get()
    
    @staticmethod
    def handle_exception(exc: Exception, context: str = "") -> None:
        """Log and handle exceptions.
        
        Args:
            exc: Exception to handle.
            context: Additional context for the error.
        """
        logger = Logger.get()
        if context:
            logger.error(f"{context}: {str(exc)}", exc_info=True)
        else:
            logger.error(f"Exception: {str(exc)}", exc_info=True)
    
    @staticmethod
    def validate_response(response: dict, 
                         required_fields: list,
                         context: str = "") -> bool:
        """Validate API response structure.
        
        Args:
            response: Response dictionary.
            required_fields: List of required field names.
            context: Context for error messages.
        
        Returns:
            True if valid, False otherwise.
        """
        logger = Logger.get()
        missing = [f for f in required_fields if f not in response]
        
        if missing:
            msg = f"Missing fields in response: {missing}"
            if context:
                msg = f"{context}: {msg}"
            logger.error(msg)
            return False
        
        return True
