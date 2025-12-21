"""Application logging with rotation and archiving"""
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime
from pathlib import Path
from typing import Optional
import json
import shutil

from app.config import settings


def archive_old_log(log_file: Path) -> Optional[Path]:
    """Archive existing log file with timestamp before starting new one.
    
    Args:
        log_file: Path to the log file to archive
        
    Returns:
        Path to archived file if archiving was done, None otherwise
    """
    if not log_file.exists():
        return None
    
    # Create archive filename with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    archive_name = f"{log_file.stem}.{timestamp}{log_file.suffix}"
    archive_path = log_file.parent / archive_name
    
    # Move current log to archive
    shutil.move(str(log_file), str(archive_path))
    
    return archive_path


def cleanup_old_logs(logs_dir: Path, max_age_days: int = 30):
    """Remove log files older than max_age_days.
    
    Args:
        logs_dir: Directory containing log files
        max_age_days: Maximum age in days
    """
    if not logs_dir.exists():
        return
    
    now = datetime.now()
    
    for log_file in logs_dir.glob("*.log*"):
        # Skip current log files
        if log_file.name in ["backend.log", "frontend.log", "uvicorn.log"]:
            continue
        
        # Check file age
        file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
        age_days = (now - file_time).days
        
        if age_days > max_age_days:
            log_file.unlink()


class OperationLogger:
    """Logger for tracking operations with rotation and archiving."""
    
    def __init__(self, log_file: Optional[Path] = None, console_output: bool = False):
        self.log_file = log_file or settings.log_file
        self.console_output = console_output
        self._setup_logger()
    
    def _setup_logger(self):
        """Setup the logger with rotation."""
        self.logger = logging.getLogger("ldc-panel")
        self.logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Ensure log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Archive old log before opening new one
        if self.log_file.exists():
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            archive_name = f"{self.log_file.stem}.{timestamp}{self.log_file.suffix}"
            archive_path = self.log_file.parent / archive_name
            try:
                shutil.copy2(str(self.log_file), str(archive_path))
                # Clear the file content instead of moving
                with open(self.log_file, 'w', encoding='utf-8') as f:
                    f.write('')
            except Exception:
                # If archiving fails, just continue with existing file
                pass
        
        # Rotating file handler (100 MB max)
        file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=100 * 1024 * 1024,  # 100 MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Format: timestamp | level | logger | message | extra fields
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        
        # Console handler for development
        if self.console_output:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # Configure root logger to capture all logs (uvicorn, fastapi, etc.)
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # Clear existing handlers to avoid duplicates
        root_logger.handlers.clear()
        
        # Add our file handler to root logger
        root_logger.addHandler(file_handler)
        
        # Add console handler to root if needed
        if self.console_output:
            root_logger.addHandler(console_handler)
        
        # Configure uvicorn loggers specifically
        for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
            logger_obj = logging.getLogger(logger_name)
            logger_obj.handlers.clear()
            logger_obj.propagate = True  # Propagate to root logger

    
    def log_operation(
        self,
        operator: str,
        action: str,
        obj: str,
        details: Optional[str] = None,
        level: str = "INFO",
    ):
        """Log an operation.
        
        Args:
            operator: Username performing the operation
            action: Action type (CREATE, UPDATE, DELETE, etc.)
            obj: Object being operated on
            details: Additional details
            level: Log level (INFO, WARNING, ERROR)
        """
        message = f"{operator} | {action} | {obj}"
        if details:
            message += f" | {details}"
        
        if level == "ERROR":
            self.logger.error(message)
        elif level == "WARNING":
            self.logger.warning(message)
        else:
            self.logger.info(message)
    
    def get_logs(self, limit: int = 100, filter_operator: Optional[str] = None) -> list:
        """Get recent log entries.
        
        Args:
            limit: Maximum number of entries to return
            filter_operator: Optional operator filter
            
        Returns:
            List of log entries
        """
        entries = []
        
        if not self.log_file.exists():
            return entries
        
        with open(self.log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        for line in reversed(lines[-limit * 2:]):  # Read more to account for filtering
            line = line.strip()
            if not line:
                continue
            
            try:
                parts = line.split(" | ")
                if len(parts) >= 4:
                    entry = {
                        "timestamp": parts[0],
                        "level": parts[1].strip(),
                        "logger": parts[2],
                        "message": " | ".join(parts[3:]),
                    }
                    
                    # Try to parse operation log format
                    msg_parts = entry["message"].split(" | ")
                    if len(msg_parts) >= 3:
                        entry["operator"] = msg_parts[0]
                        entry["action"] = msg_parts[1]
                        entry["object"] = msg_parts[2]
                        if len(msg_parts) > 3:
                            entry["details"] = " | ".join(msg_parts[3:])
                    
                    if filter_operator and entry.get("operator") != filter_operator:
                        continue
                    
                    entries.append(entry)
                    
                    if len(entries) >= limit:
                        break
            except Exception:
                # Skip malformed lines
                continue
        
        return entries


# Global logger instance
operation_logger = OperationLogger(console_output=settings.debug)


def log_operation(operator: str, action: str, obj: str, details: Optional[str] = None):
    """Convenience function to log an operation."""
    operation_logger.log_operation(operator, action, obj, details)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module.
    
    Args:
        name: Module name (e.g., 'ldc-panel.api.dns')
        
    Returns:
        Logger instance
    """
    return logging.getLogger(f"ldc-panel.{name}")
