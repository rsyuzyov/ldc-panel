"""DNS models"""
from pydantic import BaseModel
from typing import Optional, List, Literal
from enum import Enum


class DNSRecordType(str, Enum):
    A = "A"
    AAAA = "AAAA"
    CNAME = "CNAME"
    MX = "MX"
    TXT = "TXT"
    SRV = "SRV"
    PTR = "PTR"
    NS = "NS"


class DNSZone(BaseModel):
    """DNS Zone model."""
    name: str
    type: str = "forward"  # forward or reverse


class DNSRecord(BaseModel):
    """DNS Record model."""
    name: str
    type: DNSRecordType
    data: str
    ttl: int = 3600
    
    # MX specific
    priority: Optional[int] = None
    
    # SRV specific
    srv_priority: Optional[int] = None
    srv_weight: Optional[int] = None
    srv_port: Optional[int] = None


class DNSRecordCreate(BaseModel):
    """Model for creating DNS record."""
    name: str
    type: DNSRecordType
    data: str
    ttl: int = 3600
    priority: Optional[int] = None  # For MX
    srv_priority: Optional[int] = None
    srv_weight: Optional[int] = None
    srv_port: Optional[int] = None


class DNSRecordResponse(BaseModel):
    """DNS Record response model."""
    name: str
    type: str
    data: str
    ttl: int
