"""AD Groups API endpoints"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List

from app.api.auth import get_current_user
from app.api.users import get_ad_service
from app.models.ad import ADGroupCreate, ADGroupMember

router = APIRouter(prefix="/api/ad/groups", tags=["ad-groups"])


class GroupResponse(BaseModel):
    dn: str
    cn: str
    sAMAccountName: str
    description: Optional[str] = None
    member: List[str] = []
    member_count: int


@router.get("", response_model=List[GroupResponse])
async def get_groups(
    server_id: str = Query(..., description="ID сервера"),
    search: Optional[str] = Query(None, description="Поисковый запрос"),
    username: str = Depends(get_current_user),
):
    """Get list of AD groups."""
    ad_service = get_ad_service(server_id)
    
    try:
        groups, error = ad_service.search_groups(search)
        if error:
            raise HTTPException(status_code=500, detail=error)
        
        return [
            GroupResponse(
                dn=g.dn,
                cn=g.cn,
                sAMAccountName=g.sAMAccountName,
                description=g.description,
                member=g.member,
                member_count=g.member_count,
            )
            for g in groups
        ]
    finally:
        ad_service.ssh.disconnect()


@router.post("", response_model=dict)
async def create_group(
    server_id: str = Query(..., description="ID сервера"),
    group: ADGroupCreate = ...,
    username: str = Depends(get_current_user),
):
    """Create a new AD group."""
    ad_service = get_ad_service(server_id)
    
    try:
        from app.services.ldap_cmd import generate_ldif_add
        
        dn = f"CN={group.cn},{group.ou},{ad_service.base_dn}"
        attributes = {
            "objectClass": ["top", "group"],
            "cn": group.cn,
            "sAMAccountName": group.cn,
            "groupType": "-2147483646",  # Global security group
        }
        
        if group.description:
            attributes["description"] = group.description
        
        ldif = generate_ldif_add(dn, attributes)
        
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ldif', delete=False) as f:
            f.write(ldif)
            temp_path = f.name
        
        try:
            sftp = ad_service.ssh.client.open_sftp()
            remote_path = f"/tmp/add_group_{group.cn}.ldif"
            sftp.put(temp_path, remote_path)
            sftp.close()
            
            cmd = f'ldapmodify -H ldapi:/// -f {remote_path}'
            exit_code, stdout, stderr = ad_service.ssh.execute(cmd)
            
            ad_service.ssh.execute(f'rm -f {remote_path}')
            
            if exit_code != 0:
                raise HTTPException(status_code=500, detail=stderr)
            
            return {"message": "Группа создана", "cn": group.cn}
        finally:
            os.unlink(temp_path)
    finally:
        ad_service.ssh.disconnect()


@router.delete("/{dn:path}")
async def delete_group(
    dn: str,
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Delete an AD group."""
    ad_service = get_ad_service(server_id)
    
    try:
        cmd = f'ldapdelete -H ldapi:/// "{dn}"'
        exit_code, stdout, stderr = ad_service.ssh.execute(cmd)
        
        if exit_code != 0:
            raise HTTPException(status_code=500, detail=stderr)
        
        return {"message": "Группа удалена"}
    finally:
        ad_service.ssh.disconnect()


@router.post("/{dn:path}/members")
async def add_group_member(
    dn: str,
    server_id: str = Query(..., description="ID сервера"),
    member: ADGroupMember = ...,
    username: str = Depends(get_current_user),
):
    """Add a member to an AD group."""
    ad_service = get_ad_service(server_id)
    
    try:
        success, error = ad_service.add_group_member(dn, member.member_dn)
        
        if not success:
            raise HTTPException(status_code=500, detail=error)
        
        return {"message": "Член группы добавлен"}
    finally:
        ad_service.ssh.disconnect()


@router.delete("/{dn:path}/members/{member_dn:path}")
async def remove_group_member(
    dn: str,
    member_dn: str,
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Remove a member from an AD group."""
    ad_service = get_ad_service(server_id)
    
    try:
        success, error = ad_service.remove_group_member(dn, member_dn)
        
        if not success:
            raise HTTPException(status_code=500, detail=error)
        
        return {"message": "Член группы удалён"}
    finally:
        ad_service.ssh.disconnect()
