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
    """Parse samba-tool gpo listall output."""
    gpos = []
    current_gpo = {}
    
    for line in output.split('\n'):
        line = line.strip()
        if not line:
            if current_gpo:
                gpos.append(GPO(
                    name=current_gpo.get('displayname', current_gpo.get('name', '')),
                    guid=current_gpo.get('gpo', ''),
                    display_name=current_gpo.get('displayname'),
                    path=current_gpo.get('path'),
                ))
                current_gpo = {}
            continue
        
        if ':' in line:
            key, value = line.split(':', 1)
            current_gpo[key.strip().lower()] = value.strip()
    
    if current_gpo:
        gpos.append(GPO(
            name=current_gpo.get('displayname', current_gpo.get('name', '')),
            guid=current_gpo.get('gpo', ''),
            display_name=current_gpo.get('displayname'),
            path=current_gpo.get('path'),
        ))
    
    return gpos


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
        
        return [
            GPOResponse(
                name=g.name,
                guid=g.guid,
                display_name=g.display_name,
                links=[],
            )
            for g in gpos
        ]
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
