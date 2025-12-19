"""AD Computers API endpoints"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List

from app.api.auth import get_current_user
from app.api.users import get_ad_service
from app.models.ad import ADComputerCreate

router = APIRouter(prefix="/api/ad/computers", tags=["ad-computers"])


class ComputerResponse(BaseModel):
    dn: str
    cn: str
    sAMAccountName: str
    operatingSystem: Optional[str] = None
    operatingSystemVersion: Optional[str] = None
    dNSHostName: Optional[str] = None
    lastLogonTimestamp: Optional[str] = None
    enabled: bool


@router.get("", response_model=List[ComputerResponse])
async def get_computers(
    server_id: str = Query(..., description="ID сервера"),
    search: Optional[str] = Query(None, description="Поисковый запрос"),
    username: str = Depends(get_current_user),
):
    """Get list of AD computers."""
    ad_service = get_ad_service(server_id)
    
    try:
        computers, error = ad_service.search_computers(search)
        if error:
            raise HTTPException(status_code=500, detail=error)
        
        return [
            ComputerResponse(
                dn=c.dn,
                cn=c.cn,
                sAMAccountName=c.sAMAccountName,
                operatingSystem=c.operatingSystem,
                operatingSystemVersion=c.operatingSystemVersion,
                dNSHostName=c.dNSHostName,
                lastLogonTimestamp=c.lastLogonTimestamp,
                enabled=c.enabled,
            )
            for c in computers
        ]
    finally:
        ad_service.ssh.disconnect()


@router.post("", response_model=dict)
async def create_computer(
    server_id: str = Query(..., description="ID сервера"),
    computer: ADComputerCreate = ...,
    username: str = Depends(get_current_user),
):
    """Create a new AD computer."""
    ad_service = get_ad_service(server_id)
    
    try:
        # Generate LDIF for computer
        from app.services.ldap_cmd import generate_ldif_add
        
        dn = f"CN={computer.cn},{computer.ou},{ad_service.base_dn}"
        attributes = {
            "objectClass": ["top", "person", "organizationalPerson", "user", "computer"],
            "cn": computer.cn,
            "sAMAccountName": f"{computer.cn}$",
            "userAccountControl": "4096",  # Workstation trust account
        }
        
        ldif = generate_ldif_add(dn, attributes)
        
        # Execute via SSH
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ldif', delete=False) as f:
            f.write(ldif)
            temp_path = f.name
        
        try:
            sftp = ad_service.ssh.client.open_sftp()
            remote_path = f"/tmp/add_computer_{computer.cn}.ldif"
            sftp.put(temp_path, remote_path)
            sftp.close()
            
            cmd = f'ldapmodify -H ldapi:/// -f {remote_path}'
            exit_code, stdout, stderr = ad_service.ssh.execute(cmd)
            
            ad_service.ssh.execute(f'rm -f {remote_path}')
            
            if exit_code != 0:
                raise HTTPException(status_code=500, detail=stderr)
            
            return {"message": "Компьютер создан", "cn": computer.cn}
        finally:
            os.unlink(temp_path)
    finally:
        ad_service.ssh.disconnect()


@router.delete("/{dn:path}")
async def delete_computer(
    dn: str,
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Delete an AD computer."""
    ad_service = get_ad_service(server_id)
    
    try:
        cmd = f'ldapdelete -H ldapi:/// "{dn}"'
        exit_code, stdout, stderr = ad_service.ssh.execute(cmd)
        
        if exit_code != 0:
            raise HTTPException(status_code=500, detail=stderr)
        
        return {"message": "Компьютер удалён"}
    finally:
        ad_service.ssh.disconnect()
