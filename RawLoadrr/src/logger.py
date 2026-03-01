# -*- coding: utf-8 -*-
"""
Dual-level Logging System

Provides two logging levels:
- ERROR: Console + File (errors that are important)
- DEBUG: Silent file only (everything for debugging)

Never stops the process - logs everything and continues.
"""
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

_debug_mode: bool = False
_all_instances: list = []

_RAWLOADRR_ROOT = Path(__file__).parent.parent
_DEFAULT_LOGS_DIR = str(_RAWLOADRR_ROOT / "logs")


def set_debug_mode(debug: bool = False) -> None:
    """Module-level function: set debug mode for all existing and future UploadLogger instances."""
    global _debug_mode
    _debug_mode = debug
    for instance in _all_instances:
        instance.set_debug_mode(debug)


class UploadLogger:
    """
    Dual-level logger for upload tracking.
    
    Creates two log files:
    - logs/{tracker}_errors.log: Only errors (human-readable)
    - logs/{tracker}_debug.log: Everything with timestamps
    
    Logging levels:
    - ERROR: Critical failures (API errors, network issues)
    - WARNING: Rate limits, retries, potential issues
    - INFO: Successful operations, state changes
    - DEBUG: Detailed information for troubleshooting
    """
    
    def __init__(self, tracker: str = 'uploadrr', logs_dir: str = None):
        """
        Initialize logger for a specific tracker.
        
        Args:
            tracker: Tracker name (e.g., 'MILNU', 'EMU')
            logs_dir: Directory to store log files
        """
        self.tracker = tracker
        self.logs_dir = Path(logs_dir if logs_dir is not None else _DEFAULT_LOGS_DIR)
        self.logs_dir.mkdir(exist_ok=True, parents=True)
        
        # File paths
        self.error_log = self.logs_dir / f"{tracker}_errors.log"
        self.debug_log = self.logs_dir / f"{tracker}_debug.log"
        
        # Setup loggers
        self.logger_error = self._setup_error_logger()
        self.logger_debug = self._setup_debug_logger()
        self._console_handler: Optional[logging.StreamHandler] = None
        self.set_debug_mode(_debug_mode)
        _all_instances.append(self)

    def set_debug_mode(self, debug: bool = False) -> None:
        """Configure console output: WARNING+ in normal mode, DEBUG+ in debug mode."""
        if self._console_handler is not None:
            self.logger_debug.removeHandler(self._console_handler)
            self._console_handler = None
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG if debug else logging.WARNING)
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        )
        handler.setFormatter(formatter)
        self._console_handler = handler
        self.logger_debug.addHandler(handler)

    def _setup_error_logger(self) -> logging.Logger:
        """Setup error logger (human-readable errors only)"""
        logger = logging.getLogger(f"{self.tracker}_error")
        logger.setLevel(logging.ERROR)
        
        # Clear existing handlers
        logger.handlers = []
        
        # File handler - errors only
        fh = logging.FileHandler(self.error_log, encoding='utf-8')
        fh.setLevel(logging.ERROR)
        
        # Format: TIMESTAMP | LEVEL | MESSAGE
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
        return logger
    
    def _setup_debug_logger(self) -> logging.Logger:
        """Setup debug logger (everything to file, silent)"""
        logger = logging.getLogger(f"{self.tracker}_debug")
        logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        logger.handlers = []
        
        # File handler - everything
        fh = logging.FileHandler(self.debug_log, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        
        # Detailed format for debugging
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)-8s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
        return logger
    
    def error(self, message: str, exc_info: bool = False):
        """
        Log error message. Appears in both ERROR and DEBUG logs.
        
        Args:
            message: Error message
            exc_info: Include exception traceback
        """
        self.logger_error.error(message, exc_info=exc_info)
        self.logger_debug.error(message, exc_info=exc_info)
    
    def warning(self, message: str):
        """Log warning (DEBUG only - not shown in error log)"""
        self.logger_debug.warning(message)
    
    def info(self, message: str):
        """Log info (DEBUG only)"""
        self.logger_debug.info(message)
    
    def debug(self, message: str):
        """Log debug details (DEBUG only)"""
        self.logger_debug.debug(message)
    
    def api_call(self, method: str, url: str, status: Optional[int] = None, response_time: float = 0):
        """
        Log API call details.
        
        Args:
            method: HTTP method (GET, POST, etc)
            url: API endpoint
            status: HTTP status code (if response received)
            response_time: Time taken in seconds
        """
        if status:
            msg = f"API {method} {url} → {status} ({response_time:.2f}s)"
            if status >= 400:
                self.error(msg)
            else:
                self.debug(msg)
        else:
            self.debug(f"API {method} {url} (request sent)")
    
    def upload_result(self, torrent_name: str, success: bool, reason: str = ""):
        """
        Log upload result (appears in appropriate log).
        
        Args:
            torrent_name: Name of torrent being uploaded
            success: Upload successful?
            reason: Optional reason for failure
        """
        if success:
            self.info(f"✓ Upload successful: {torrent_name}")
        else:
            msg = f"✗ Upload failed: {torrent_name}"
            if reason:
                msg += f" ({reason})"
            self.error(msg)
    
    def tor_fallback(self, url: str, reason: str):
        """Log Tor fallback activation"""
        self.warning(f"Tor fallback activated for {url}: {reason}")
        self.debug(f"Attempting connection via Tor SOCKS5")
    
    def rate_limit_hit(self, calls_current: int, calls_max: int, wait_time: float):
        """Log rate limit event"""
        self.warning(
            f"Rate limit approaching: {calls_current}/{calls_max} "
            f"- waiting {wait_time:.2f}s"
        )
    
    def get_error_log_path(self) -> str:
        """Get path to error log file"""
        return str(self.error_log)
    
    def get_debug_log_path(self) -> str:
        """Get path to debug log file"""
        return str(self.debug_log)
    
    def print_stats(self):
        """Print log file statistics"""
        try:
            error_size = self.error_log.stat().st_size if self.error_log.exists() else 0
            debug_size = self.debug_log.stat().st_size if self.debug_log.exists() else 0
            
            error_lines = sum(1 for _ in open(self.error_log)) if self.error_log.exists() else 0
            debug_lines = sum(1 for _ in open(self.debug_log)) if self.debug_log.exists() else 0
            
            from src.console import console
            console.print(f"\n[blue]Log Statistics for {self.tracker}:[/blue]")
            console.print(f"  Error Log: {error_size:,} bytes ({error_lines} lines)")
            console.print(f"  Debug Log: {debug_size:,} bytes ({debug_lines} lines)")
            console.print(f"  Location: {self.logs_dir}/\n")
        except Exception as e:
            print(f"Could not read log stats: {e}")


# Convenience function to create loggers
def get_logger(tracker: str) -> UploadLogger:
    """Get or create a logger for a tracker"""
    return UploadLogger(tracker)
