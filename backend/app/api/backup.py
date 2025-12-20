"""Backup and Restore API endpoints"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List
from datetime import datetime

from app.api.auth import get_current_user
from app.services.server_store import server_store
from app.services.ssh import SSHService

router = APIRouter(prefix="/api/backup", tags=["backup"])

BACKUP_LDIF_DIR = "/backups/ldif"
BACKUP_DHCP_DIR = "/backups/dhcp"


class BackupFile(BaseModel):
    filename: str
    type: str
    size: int
    created: str


def get_backup_ssh(server_id: str) -> SSHService:
    """Get SSH service for backup operations."""
    server = server_store.get_by_id(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Сервер не найден")
    
    ssh = SSHService(server)
    success, error = ssh.connect()
    if not success:
        raise HTTPException(status_code=500, detail=f"Ошибка подключения: {error}")
    
    return ssh


@router.post("/ldif")
async def backup_ldif(
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Create LDIF backup."""
    ssh = get_backup_ssh(server_id)
    server = server_store.get_by_id(server_id)
    
    try:
        # Ensure backup directory exists
        ssh.execute(f"mkdir -p {BACKUP_LDIF_DIR}")
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ldif_backup_{timestamp}.ldif"
        filepath = f"{BACKUP_LDIF_DIR}/{filename}"
        
        # Execute ldapsearch to create backup
        base_dn = server.base_dn or "DC=domain,DC=local"
        cmd = f'ldapsearch -x -H ldap://localhost -b "{base_dn}" "(objectClass=*)" > {filepath}'
        
        exit_code, stdout, stderr = ssh.execute(cmd)
        
        if exit_code != 0:
            raise HTTPException(status_code=500, detail=f"Ошибка создания бэкапа: {stderr}")
        
        return {"message": "LDIF бэкап создан", "filename": filename}
    finally:
        ssh.disconnect()


@router.post("/dhcp")
async def backup_dhcp(
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Create DHCP config backup."""
    ssh = get_backup_ssh(server_id)
    
    try:
        # Ensure backup directory exists
        ssh.execute(f"mkdir -p {BACKUP_DHCP_DIR}")
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"dhcpd_backup_{timestamp}.conf"
        filepath = f"{BACKUP_DHCP_DIR}/{filename}"
        
        # Copy dhcpd.conf
        cmd = f"cp /etc/dhcp/dhcpd.conf {filepath}"
        
        exit_code, stdout, stderr = ssh.execute(cmd)
        
        if exit_code != 0:
            raise HTTPException(status_code=500, detail=f"Ошибка создания бэкапа: {stderr}")
        
        return {"message": "DHCP бэкап создан", "filename": filename}
    finally:
        ssh.disconnect()


@router.get("/list", response_model=List[BackupFile])
async def list_backups(
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """List available backups."""
    ssh = get_backup_ssh(server_id)
    
    try:
        backups = []
        
        # List LDIF backups
        exit_code, stdout, stderr = ssh.execute(f"ls -la {BACKUP_LDIF_DIR}/*.ldif 2>/dev/null || true")
        if exit_code == 0 and stdout.strip():
            for line in stdout.strip().split('\n'):
                parts = line.split()
                if len(parts) >= 9:
                    filename = parts[-1].split('/')[-1]
                    size = int(parts[4]) if parts[4].isdigit() else 0
                    date_str = f"{parts[5]} {parts[6]} {parts[7]}"
                    backups.append(BackupFile(
                        filename=filename,
                        type="ldif",
                        size=size,
                        created=date_str,
                    ))
        
        # List DHCP backups
        exit_code, stdout, stderr = ssh.execute(f"ls -la {BACKUP_DHCP_DIR}/*.conf 2>/dev/null || true")
        if exit_code == 0 and stdout.strip():
            for line in stdout.strip().split('\n'):
                parts = line.split()
                if len(parts) >= 9:
                    filename = parts[-1].split('/')[-1]
                    size = int(parts[4]) if parts[4].isdigit() else 0
                    date_str = f"{parts[5]} {parts[6]} {parts[7]}"
                    backups.append(BackupFile(
                        filename=filename,
                        type="dhcp",
                        size=size,
                        created=date_str,
                    ))
        
        return backups
    finally:
        ssh.disconnect()


@router.post("/restore/{backup_type}/{filename}")
async def restore_backup(
    backup_type: str,
    filename: str,
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Restore from backup."""
    if backup_type not in ("ldif", "dhcp"):
        raise HTTPException(status_code=400, detail="Неверный тип бэкапа")
    
    ssh = get_backup_ssh(server_id)
    
    try:
        if backup_type == "ldif":
            filepath = f"{BACKUP_LDIF_DIR}/{filename}"
            
            # Check file exists
            exit_code, _, _ = ssh.execute(f"test -f {filepath}")
            if exit_code != 0:
                raise HTTPException(status_code=404, detail="Файл бэкапа не найден")
            
            # Restore using ldapadd
            cmd = f"ldapadd -H ldapi:/// -f {filepath}"
            exit_code, stdout, stderr = ssh.execute(cmd)
            
            if exit_code != 0:
                raise HTTPException(status_code=500, detail=f"Ошибка восстановления: {stderr}")
            
            return {"message": "LDIF бэкап восстановлен"}
        
        else:  # dhcp
            filepath = f"{BACKUP_DHCP_DIR}/{filename}"
            
            # Check file exists
            exit_code, _, _ = ssh.execute(f"test -f {filepath}")
            if exit_code != 0:
                raise HTTPException(status_code=404, detail="Файл бэкапа не найден")
            
            # Restore dhcpd.conf
            cmd = f"cp {filepath} /etc/dhcp/dhcpd.conf && systemctl reload isc-dhcp-server"
            exit_code, stdout, stderr = ssh.execute(cmd)
            
            if exit_code != 0:
                raise HTTPException(status_code=500, detail=f"Ошибка восстановления: {stderr}")
            
            return {"message": "DHCP бэкап восстановлен"}
    finally:
        ssh.disconnect()
