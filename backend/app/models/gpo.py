"""GPO models"""
from pydantic import BaseModel
from typing import Optional, List


class GPO(BaseModel):
    """Group Policy Object model."""
    name: str
    guid: str
    path: Optional[str] = None
    display_name: Optional[str] = None
    version: Optional[str] = None


class GPOCreate(BaseModel):
    """Model for creating GPO."""
    name: str


class GPOLink(BaseModel):
    """GPO Link model."""
    container_dn: str
    gpo_guid: str


class GPOResponse(BaseModel):
    """GPO response model."""
    name: str
    guid: str
    display_name: Optional[str] = None
    links: List[str] = []
