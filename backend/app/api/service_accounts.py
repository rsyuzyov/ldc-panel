from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.api.users import get_ad_service

router = APIRouter(prefix="/api/ad", tags=["ad-service-accounts"])


class ServiceAccountResponse(BaseModel):
    dn: str
    sAMAccountName: str
    cn: str
    description: Optional[str] = None


@router.get("/service-accounts", response_model=List[ServiceAccountResponse])
async def get_service_accounts(
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Get list of Managed Service Accounts (MSA/gMSA)."""
    ad_service = get_ad_service(server_id)
    
    try:
        # MSA и gMSA
        cmd = 'ldbsearch -H /var/lib/samba/private/sam.ldb "(|(objectClass=msDS-ManagedServiceAccount)(objectClass=msDS-GroupManagedServiceAccount))" dn cn sAMAccountName description'
        exit_code, stdout, stderr = ad_service.ssh.execute(cmd)
        
        if exit_code != 0:
            raise HTTPException(status_code=500, detail=stderr)
        
        entries = ad_service._parse_ldbsearch_output(stdout)
        
        return [
            ServiceAccountResponse(
                dn=e.get('dn', ''),
                sAMAccountName=e.get('sAMAccountName', ''),
                cn=e.get('cn', ''),
                description=e.get('description'),
            )
            for e in entries
            if e.get('sAMAccountName')
        ]
    finally:
        ad_service.ssh.disconnect()
