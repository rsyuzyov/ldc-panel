"""GPO API endpoints"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List
import re

from app.api.auth import get_current_user
from app.models.gpo import GPO, GPOCreate, GPOLink, GPOResponse
from app.services.server_store import server_store
from app.services.ssh import SSHService
from app.services.samba_tool import (
    generate_gpo_listall_command,
    generate_gpo_create_command,
    generate_gpo_delete_command,
    generate_gpo_setlink_command,
)

router = APIRouter(prefix="/api/gpo", tags=["gpo"])


def get_gpo_ssh(server_id: str) -> SSHService:
    """Get SSH service for GPO operations."""
    server = server_store.get_by_id(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Сервер не найден")
    
    if not server.services.ad:
        raise HTTPException(status_code=400, detail="AD сервис недоступен на этом сервере")
    
    ssh = SSHService(server)
    success, error = ssh.connect()
    if not success:
        raise HTTPException(status_code=500, detail=f"Ошибка подключения: {error}")
    
    return ssh


def parse_gpo_list(output: str) -> List[GPO]:
    """Parse samba-tool gpo listall output.
    
    Output format:
    GPO          : {GUID}
    display name : Policy Name
    path         : \\domain\sysvol\...
    dn           : CN={GUID},CN=Policies,...
    """
    gpos = []
    current_gpo = {}
    
    for line in output.split('\n'):
        line = line.strip()
        if not line:
            if current_gpo:
                display_name = current_gpo.get('display name', current_gpo.get('displayname', ''))
                gpos.append(GPO(
                    name=display_name or current_gpo.get('gpo', ''),
                    guid=current_gpo.get('gpo', ''),
                    display_name=display_name,
                    path=current_gpo.get('path'),
                ))
                current_gpo = {}
            continue
        
        if ':' in line:
            key, value = line.split(':', 1)
            current_gpo[key.strip().lower()] = value.strip()
    
    if current_gpo:
        display_name = current_gpo.get('display name', current_gpo.get('displayname', ''))
        gpos.append(GPO(
            name=display_name or current_gpo.get('gpo', ''),
            guid=current_gpo.get('gpo', ''),
            display_name=display_name,
            path=current_gpo.get('path'),
        ))
    
    return gpos


def get_gpo_details(ssh: SSHService, guid: str) -> dict:
    """Get GPO details from LDAP (links, whenChanged)."""
    # Убираем фигурные скобки для поиска
    clean_guid = guid.strip('{}')
    
    # Ищем GPO в LDAP
    cmd = f'ldbsearch -H /var/lib/samba/private/sam.ldb "(objectClass=groupPolicyContainer)" dn displayName whenChanged gPCFileSysPath'
    exit_code, stdout, stderr = ssh.execute(cmd)
    
    details = {}
    if exit_code == 0:
        current = {}
        for line in stdout.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                if current and clean_guid.lower() in current.get('dn', '').lower():
                    details = current
                    break
                current = {}
                continue
            if ': ' in line:
                key, value = line.split(': ', 1)
                current[key] = value
        if current and clean_guid.lower() in current.get('dn', '').lower():
            details = current
    
    # Ищем линки GPO (где gPLink содержит этот GUID)
    links = []
    cmd2 = f'ldbsearch -H /var/lib/samba/private/sam.ldb "(gPLink=*{clean_guid}*)" dn'
    exit_code2, stdout2, stderr2 = ssh.execute(cmd2)
    
    if exit_code2 == 0:
        for line in stdout2.split('\n'):
            if line.startswith('dn: '):
                dn = line[4:].strip()
                # Упрощаем DN для отображения
                if 'DC=' in dn:
                    parts = dn.split(',')
                    simple = parts[0].replace('OU=', '').replace('CN=', '').replace('DC=', '')
                    links.append(simple)
    
    return {
        'whenChanged': details.get('whenChanged', ''),
        'links': links,
    }


@router.get("", response_model=List[GPOResponse])
async def get_gpos(
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Get list of GPOs."""
    ssh = get_gpo_ssh(server_id)
    
    try:
        cmd = generate_gpo_listall_command()
        exit_code, stdout, stderr = ssh.execute(cmd)
        
        if exit_code != 0:
            raise HTTPException(status_code=500, detail=stderr)
        
        gpos = parse_gpo_list(stdout)
        
        result = []
        for g in gpos:
            details = get_gpo_details(ssh, g.guid)
            result.append(GPOResponse(
                name=g.name,
                guid=g.guid,
                display_name=g.display_name,
                links=details['links'],
                when_changed=details['whenChanged'],
            ))
        
        return result
    finally:
        ssh.disconnect()


@router.post("", response_model=dict)
async def create_gpo(
    gpo: GPOCreate,
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Create a new GPO."""
    ssh = get_gpo_ssh(server_id)
    
    try:
        cmd = generate_gpo_create_command(gpo.name)
        exit_code, stdout, stderr = ssh.execute(cmd)
        
        if exit_code != 0:
            raise HTTPException(status_code=500, detail=stderr)
        
        # Extract GUID from output
        guid_match = re.search(r'\{[0-9A-Fa-f-]+\}', stdout)
        guid = guid_match.group(0) if guid_match else ""
        
        return {"message": "GPO создана", "name": gpo.name, "guid": guid}
    finally:
        ssh.disconnect()


@router.delete("/{gpo_guid}")
async def delete_gpo(
    gpo_guid: str,
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Delete a GPO."""
    ssh = get_gpo_ssh(server_id)
    
    try:
        cmd = generate_gpo_delete_command(gpo_guid)
        exit_code, stdout, stderr = ssh.execute(cmd)
        
        if exit_code != 0:
            raise HTTPException(status_code=500, detail=stderr)
        
        return {"message": "GPO удалена"}
    finally:
        ssh.disconnect()


@router.post("/{gpo_guid}/link")
async def link_gpo(
    gpo_guid: str,
    link: GPOLink,
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Link a GPO to a container."""
    ssh = get_gpo_ssh(server_id)
    
    try:
        cmd = generate_gpo_setlink_command(link.container_dn, gpo_guid)
        exit_code, stdout, stderr = ssh.execute(cmd)
        
        if exit_code != 0:
            raise HTTPException(status_code=500, detail=stderr)
        
        return {"message": "GPO связана"}
    finally:
        ssh.disconnect()
