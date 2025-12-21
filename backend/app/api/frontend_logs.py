"""Frontend logs API endpoint"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
import logging
from pathlib import Path

from app.config import settings
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/logs", tags=["logs"])

# Create frontend logger
frontend_log_file = settings.logs_dir / "frontend.log"
frontend_logger = logging.getLogger("ldc-panel.frontend")
frontend_logger.setLevel(logging.DEBUG)

# Ensure no duplicate handlers
if not frontend_logger.handlers:
    handler = logging.FileHandler(frontend_log_file, encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    frontend_logger.addHandler(handler)


class FrontendLogEntry(BaseModel):
    level: str  # error, warn, info, debug
    message: str
    context: Optional[dict[str, Any]] = None
    timestamp: Optional[str] = None
    url: Optional[str] = None


@router.post("/frontend")
async def receive_frontend_log(
    log_entry: FrontendLogEntry,
    request: Request,
    username: Optional[str] = Depends(get_current_user)
):
    """Receive log from frontend and write to frontend.log"""
    
    # Build log message
    log_msg = f"{log_entry.message}"
    if log_entry.context:
        log_msg += f" | context={log_entry.context}"
    if log_entry.url:
        log_msg += f" | url={log_entry.url}"
    
    # Add request metadata
    user_agent = request.headers.get("User-Agent", "unknown")
    ip_address = request.client.host if request.client else "unknown"
    log_msg += f" | user={username or 'anonymous'} | ip={ip_address} | ua={user_agent}"
    
    # Log according to level
    level_map = {
        "error": logging.ERROR,
        "warn": logging.WARNING,
        "info": logging.INFO,
        "debug": logging.DEBUG
    }
    log_level = level_map.get(log_entry.level.lower(), logging.INFO)
    
    frontend_logger.log(log_level, log_msg)
    
    return {"status": "logged"}


@router.post("/frontend/batch")
async def receive_frontend_logs_batch(
    log_entries: list[FrontendLogEntry],
    request: Request,
    username: Optional[str] = Depends(get_current_user)
):
    """Receive multiple logs from frontend in batch"""
    
    for log_entry in log_entries:
        # Build log message
        log_msg = f"{log_entry.message}"
        if log_entry.context:
            log_msg += f" | context={log_entry.context}"
        if log_entry.url:
            log_msg += f" | url={log_entry.url}"
        
        # Add request metadata
        user_agent = request.headers.get("User-Agent", "unknown")
        ip_address = request.client.host if request.client else "unknown"
        log_msg += f" | user={username or 'anonymous'} | ip={ip_address}"
        
        # Log according to level
        level_map = {
            "error": logging.ERROR,
            "warn": logging.WARNING,
            "info": logging.INFO,
            "debug": logging.DEBUG
        }
        log_level = level_map.get(log_entry.level.lower(), logging.INFO)
        
        frontend_logger.log(log_level, log_msg)
    
    return {"status": "logged", "count": len(log_entries)}
