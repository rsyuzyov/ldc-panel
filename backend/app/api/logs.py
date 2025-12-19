"""Logs API endpoints"""
from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.logger import operation_logger

router = APIRouter(prefix="/api/logs", tags=["logs"])


class LogEntry(BaseModel):
    timestamp: str
    level: str
    operator: str
    action: str
    object: str
    details: str


@router.get("", response_model=List[LogEntry])
async def get_logs(
    limit: int = Query(100, ge=1, le=1000, description="Максимальное количество записей"),
    operator: Optional[str] = Query(None, description="Фильтр по оператору"),
    username: str = Depends(get_current_user),
):
    """Get operation logs."""
    logs = operation_logger.get_logs(limit=limit, filter_operator=operator)
    
    return [
        LogEntry(
            timestamp=log["timestamp"],
            level=log["level"],
            operator=log["operator"],
            action=log["action"],
            object=log["object"],
            details=log["details"],
        )
        for log in logs
    ]
