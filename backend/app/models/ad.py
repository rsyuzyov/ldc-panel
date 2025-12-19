"""Active Directory models"""
from pydantic import BaseModel, Field
from typing import Optional, List


class ADUser(BaseModel):
    """AD User model."""
    dn: str
    sAMAccountName: str
    cn: str
    sn: Optional[str] = None
    givenName: Optional[str] = None
    mail: Optional[str] = None
    userPrincipalName: Optional[str] = None
    memberOf: List[str] = Field(default_factory=list)
    userAccountControl: int = 512  # Normal account
    
    @property
    def enabled(self) -> bool:
        """Check if user account is enabled."""
        return not (self.userAccountControl & 2)  # ACCOUNTDISABLE flag
    
    @property
    def full_name(self) -> str:
        """Get full name."""
        parts = []
        if self.givenName:
            parts.append(self.givenName)
        if self.sn:
            parts.append(self.sn)
        return " ".join(parts) if parts else self.cn


class ADUserCreate(BaseModel):
    """Model for creating AD user."""
    sAMAccountName: str
    cn: str
    sn: Optional[str] = None
    givenName: Optional[str] = None
    mail: Optional[str] = None
    password: str
    ou: str = "CN=Users"  # Default OU


class ADUserUpdate(BaseModel):
    """Model for updating AD user."""
    cn: Optional[str] = None
    sn: Optional[str] = None
    givenName: Optional[str] = None
    mail: Optional[str] = None
    userAccountControl: Optional[int] = None


class ADComputer(BaseModel):
    """AD Computer model."""
    dn: str
    cn: str
    sAMAccountName: str
    operatingSystem: Optional[str] = None
    operatingSystemVersion: Optional[str] = None
    dNSHostName: Optional[str] = None
    lastLogonTimestamp: Optional[str] = None
    userAccountControl: int = 4096  # Workstation trust account
    
    @property
    def enabled(self) -> bool:
        """Check if computer account is enabled."""
        return not (self.userAccountControl & 2)


class ADComputerCreate(BaseModel):
    """Model for creating AD computer."""
    cn: str
    ou: str = "CN=Computers"


class ADGroup(BaseModel):
    """AD Group model."""
    dn: str
    cn: str
    sAMAccountName: str
    description: Optional[str] = None
    member: List[str] = Field(default_factory=list)
    groupType: int = -2147483646  # Global security group
    
    @property
    def member_count(self) -> int:
        """Get number of members."""
        return len(self.member)


class ADGroupCreate(BaseModel):
    """Model for creating AD group."""
    cn: str
    description: Optional[str] = None
    ou: str = "CN=Users"


class ADGroupMember(BaseModel):
    """Model for group member operation."""
    member_dn: str
