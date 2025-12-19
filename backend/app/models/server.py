"""Server models"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum


class AuthType(str, Enum):
    KEY = "key"
    PASSWORD = "password"


class ServerServices(BaseModel):
    ad: bool = False
    dns: bool = False
    dhcp: bool = False


class ServerConfig(BaseModel):
    """Server configuration model."""
    id: str
    name: str
    host: str
    port: int = 22
    user: str = "root"
    auth_type: AuthType = AuthType.KEY
    key_path: Optional[str] = None
    password: Optional[str] = None
    services: ServerServices = Field(default_factory=ServerServices)
    domain: Optional[str] = None
    base_dn: Optional[str] = None


class ServerCreate(BaseModel):
    """Model for creating a new server."""
    id: str
    name: str
    host: str
    port: int = 22
    user: str = "root"
    auth_type: AuthType = AuthType.KEY
    key_path: Optional[str] = None
    password: Optional[str] = None
    domain: Optional[str] = None
    base_dn: Optional[str] = None


class ServerStatus(BaseModel):
    """Server status model."""
    id: str
    name: str
    host: str
    connected: bool = False
    services: ServerServices = Field(default_factory=ServerServices)
    error: Optional[str] = None


class ServerResponse(BaseModel):
    """Server response model (without sensitive data)."""
    id: str
    name: str
    host: str
    port: int
    user: str
    auth_type: AuthType
    services: ServerServices
    domain: Optional[str] = None
    base_dn: Optional[str] = None
