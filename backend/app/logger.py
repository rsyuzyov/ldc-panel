"""Operation logging"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
import json

from app.config import settings


class OperationLogger:
    """Logger for tracking operations."""
    
    def __init__(self, log_file: Optional[Path] = None):
        self.log_file = log_file or settings.log_file
        self._setup_logger()
    
    def _setup_logger(self):
        """Setup the logger."""
        self.logger = logging.getLogger("ldc-panel")
        self.logger.setLevel(logging.INFO)
        
        # Ensure log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # File handler
        handler = logging.FileHandler(self.log_file, encoding="utf-8")
        handler.setLevel(logging.INFO)
        
        # Format: timestamp | level | operator | action | object | details
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(operator)s | %(action)s | %(object)s | %(details)s"
        )
        handler.setFormatter(formatter)
        
        self.logger.addHandler(handler)
    
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
        extra = {
            "operator": operator,
            "action": action,
            "object": obj,
            "details": details or "",
        }
        
        message = f"{action} {obj}"
        
        if level == "ERROR":
            self.logger.error(message, extra=extra)
        elif level == "WARNING":
            self.logger.warning(message, extra=extra)
        else:
            self.logger.info(message, extra=extra)
    
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
            
            parts = line.split(" | ")
            if len(parts) >= 5:
                entry = {
                    "timestamp": parts[0],
                    "level": parts[1],
                    "operator": parts[2],
                    "action": parts[3],
                    "object": parts[4],
                    "details": parts[5] if len(parts) > 5 else "",
                }
                
                if filter_operator and entry["operator"] != filter_operator:
                    continue
                
                entries.append(entry)
                
                if len(entries) >= limit:
                    break
        
        return entries


# Global logger instance
operation_logger = OperationLogger()


def log_operation(operator: str, action: str, obj: str, details: Optional[str] = None):
    """Convenience function to log an operation."""
    operation_logger.log_operation(operator, action, obj, details)
