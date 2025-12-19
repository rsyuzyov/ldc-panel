"""DHCP models"""
from pydantic import BaseModel
from typing import Optional, List
import uuid


class DHCPSubnet(BaseModel):
    """DHCP Subnet model."""
    id: str = ""
    network: str  # "192.168.1.0"
    netmask: str  # "255.255.255.0"
    range_start: Optional[str] = None
    range_end: Optional[str] = None
    routers: Optional[str] = None
    domain_name_servers: Optional[str] = None
    domain_name: Optional[str] = None
    default_lease_time: int = 86400
    max_lease_time: int = 172800
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.id:
            self.id = str(uuid.uuid4())[:8]


class DHCPSubnetCreate(BaseModel):
    """Model for creating DHCP subnet."""
    network: str
    netmask: str
    range_start: Optional[str] = None
    range_end: Optional[str] = None
    routers: Optional[str] = None
    domain_name_servers: Optional[str] = None
    domain_name: Optional[str] = None
    default_lease_time: int = 86400
    max_lease_time: int = 172800


class DHCPReservation(BaseModel):
    """DHCP Reservation model."""
    id: str = ""
    hostname: str
    mac: str  # "00:11:22:33:44:55"
    ip: str
    description: Optional[str] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.id:
            # Используем MAC как ID для стабильности
            self.id = self.mac.lower().replace(":", "-")


class DHCPReservationCreate(BaseModel):
    """Model for creating DHCP reservation."""
    hostname: str
    mac: str
    ip: str
    description: Optional[str] = None


class DHCPLease(BaseModel):
    """DHCP Lease model."""
    ip: str
    mac: str
    hostname: Optional[str] = None
    starts: Optional[str] = None
    ends: Optional[str] = None
    state: str = "active"
