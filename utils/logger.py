"""
Logging and console utilities.
"""

import logging
import sys
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional, Callable
import threading


def get_log_file_path() -> Path:
    """Return the user-writable application log path."""
    if os.name == 'nt':
        base = os.getenv('LOCALAPPDATA') or os.getenv('APPDATA')
        log_dir = Path(base) / "yuoop-downloader" / "logs" if base else Path.home() / "yuoop-downloader" / "logs"
    else:
        state_home = os.getenv('XDG_STATE_HOME')
        log_dir = (Path(state_home) if state_home else Path.home() / ".local" / "state") / "yuoop-downloader"

    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "yuoop.log"


class LogHandler:
    """
    Custom logging handler that can forward logs to UI callbacks.
    """
    
    def __init__(self):
        """Initialize log handler."""
        self.log_callbacks: list[Callable[[str], None]] = []
        self._callback_lock = threading.Lock()
        self.logger = logging.getLogger('yuoop')
        self._setup_logger()
    
    def _setup_logger(self) -> None:
        """Configure the logger with file and stream handlers."""
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Set level
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False
        
        # File handler
        try:
            file_handler = RotatingFileHandler(
                get_log_file_path(),
                maxBytes=1_000_000,
                backupCount=3,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not setup file handler: {e}")
        
        # Stream handler (console)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(logging.INFO)
        stream_formatter = logging.Formatter(
            '[%(levelname)s] %(message)s'
        )
        stream_handler.setFormatter(stream_formatter)
        self.logger.addHandler(stream_handler)
    
    def add_ui_callback(self, callback: Callable[[str], None]) -> None:
        """
        Register a callback to receive log messages (for UI display).
        
        Args:
            callback: Function that receives log message string
        """
        with self._callback_lock:
            if callback not in self.log_callbacks:
                self.log_callbacks.append(callback)
    
    def remove_ui_callback(self, callback: Callable[[str], None]) -> None:
        """Remove a UI callback."""
        with self._callback_lock:
            if callback in self.log_callbacks:
                self.log_callbacks.remove(callback)
    
    def _broadcast_to_ui(self, level: str, message: str) -> None:
        """Broadcast log message to all registered UI callbacks."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted_msg = f"[{timestamp}] {level}: {message}"
        with self._callback_lock:
            callbacks = list(self.log_callbacks)

        for callback in callbacks:
            try:
                callback(formatted_msg)
            except Exception as e:
                self.logger.error(f"Error in UI callback: {e}")
    
    def info(self, message: str) -> None:
        """Log info message."""
        self.logger.info(message)
        self._broadcast_to_ui("INFO", message)
    
    def warning(self, message: str) -> None:
        """Log warning message."""
        self.logger.warning(message)
        self._broadcast_to_ui("WARNING", message)
    
    def error(self, message: str) -> None:
        """Log error message."""
        self.logger.error(message)
        self._broadcast_to_ui("ERROR", message)
    
    def debug(self, message: str) -> None:
        """Log debug message."""
        self.logger.debug(message)
    
    def success(self, message: str) -> None:
        """Log success message (custom level for UI)."""
        self.logger.info(message)
        self._broadcast_to_ui("SUCCESS", message)


# Global logger instance
_logger: Optional[LogHandler] = None


def get_logger() -> LogHandler:
    """Get or create global logger instance."""
    global _logger
    if _logger is None:
        _logger = LogHandler()
    return _logger
