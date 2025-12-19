"""DHCP API endpoints"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List

from app.api.auth import get_current_user
from app.models.dhcp import DHCPSubnet, DHCPSubnetCreate, DHCPReservation, DHCPReservationCreate, DHCPLease
from app.services.server_store import server_store
from app.services.ssh import SSHService
from app.services.dhcp_parser import parse_dhcpd_conf, serialize_dhcpd_conf, parse_dhcpd_leases

router = APIRouter(prefix="/api/dhcp", tags=["dhcp"])

DHCPD_CONF_PATH = "/etc/dhcp/dhcpd.conf"
DHCPD_LEASES_PATH = "/var/lib/dhcp/dhcpd.leases"


def get_dhcp_ssh(server_id: str) -> SSHService:
    """Get SSH service for DHCP operations."""
    server = server_store.get_by_id(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Сервер не найден")
    
    if not server.services.dhcp:
        raise HTTPException(status_code=400, detail="DHCP сервис недоступен на этом сервере")
    
    ssh = SSHService(server)
    success, error = ssh.connect()
    if not success:
        raise HTTPException(status_code=500, detail=f"Ошибка подключения: {error}")
    
    return ssh


def load_dhcp_config(ssh: SSHService) -> tuple:
    """Load and parse DHCP config from server."""
    exit_code, stdout, stderr = ssh.execute(f"cat {DHCPD_CONF_PATH}")
    if exit_code != 0:
        raise HTTPException(status_code=500, detail=f"Ошибка чтения конфигурации: {stderr}")
    
    return parse_dhcpd_conf(stdout)


def save_dhcp_config(ssh: SSHService, subnets: List[DHCPSubnet], reservations: List[DHCPReservation]):
    """Save DHCP config to server and reload service."""
    config = serialize_dhcpd_conf(subnets, reservations)
    
    # Check syntax first
    exit_code, stdout, stderr = ssh.execute(f'echo "{config}" | dhcpd -t -cf /dev/stdin')
    if exit_code != 0:
        raise HTTPException(status_code=400, detail=f"Ошибка синтаксиса: {stderr}")
    
    # Write config
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
        f.write(config)
        temp_path = f.name
    
    try:
        sftp = ssh.client.open_sftp()
        sftp.put(temp_path, DHCPD_CONF_PATH)
        sftp.close()
    finally:
        os.unlink(temp_path)
    
    # Reload service
    exit_code, stdout, stderr = ssh.execute("systemctl reload isc-dhcp-server")
    if exit_code != 0:
        raise HTTPException(status_code=500, detail=f"Ошибка перезагрузки сервиса: {stderr}")


@router.get("/subnets", response_model=List[DHCPSubnet])
async def get_subnets(
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Get list of DHCP subnets."""
    ssh = get_dhcp_ssh(server_id)
    
    try:
        subnets, _ = load_dhcp_config(ssh)
        return subnets
    finally:
        ssh.disconnect()


@router.post("/subnets", response_model=DHCPSubnet)
async def create_subnet(
    subnet: DHCPSubnetCreate,
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Create a new DHCP subnet."""
    ssh = get_dhcp_ssh(server_id)
    
    try:
        subnets, reservations = load_dhcp_config(ssh)
        
        new_subnet = DHCPSubnet(**subnet.model_dump())
        subnets.append(new_subnet)
        
        save_dhcp_config(ssh, subnets, reservations)
        
        return new_subnet
    finally:
        ssh.disconnect()


@router.patch("/subnets/{subnet_id}", response_model=DHCPSubnet)
async def update_subnet(
    subnet_id: str,
    subnet: DHCPSubnetCreate,
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Update a DHCP subnet."""
    ssh = get_dhcp_ssh(server_id)
    
    try:
        subnets, reservations = load_dhcp_config(ssh)
        
        for i, s in enumerate(subnets):
            if s.id == subnet_id:
                updated = DHCPSubnet(id=subnet_id, **subnet.model_dump())
                subnets[i] = updated
                save_dhcp_config(ssh, subnets, reservations)
                return updated
        
        raise HTTPException(status_code=404, detail="Подсеть не найдена")
    finally:
        ssh.disconnect()


@router.delete("/subnets/{subnet_id}")
async def delete_subnet(
    subnet_id: str,
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Delete a DHCP subnet."""
    ssh = get_dhcp_ssh(server_id)
    
    try:
        subnets, reservations = load_dhcp_config(ssh)
        
        original_len = len(subnets)
        subnets = [s for s in subnets if s.id != subnet_id]
        
        if len(subnets) == original_len:
            raise HTTPException(status_code=404, detail="Подсеть не найдена")
        
        save_dhcp_config(ssh, subnets, reservations)
        
        return {"message": "Подсеть удалена"}
    finally:
        ssh.disconnect()


@router.get("/reservations", response_model=List[DHCPReservation])
async def get_reservations(
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Get list of DHCP reservations."""
    ssh = get_dhcp_ssh(server_id)
    
    try:
        _, reservations = load_dhcp_config(ssh)
        return reservations
    finally:
        ssh.disconnect()


@router.post("/reservations", response_model=DHCPReservation)
async def create_reservation(
    reservation: DHCPReservationCreate,
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Create a new DHCP reservation."""
    ssh = get_dhcp_ssh(server_id)
    
    try:
        subnets, reservations = load_dhcp_config(ssh)
        
        new_reservation = DHCPReservation(**reservation.model_dump())
        reservations.append(new_reservation)
        
        save_dhcp_config(ssh, subnets, reservations)
        
        return new_reservation
    finally:
        ssh.disconnect()


@router.delete("/reservations/{reservation_id}")
async def delete_reservation(
    reservation_id: str,
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Delete a DHCP reservation."""
    ssh = get_dhcp_ssh(server_id)
    
    try:
        subnets, reservations = load_dhcp_config(ssh)
        
        original_len = len(reservations)
        reservations = [r for r in reservations if r.id != reservation_id]
        
        if len(reservations) == original_len:
            raise HTTPException(status_code=404, detail="Резервирование не найдено")
        
        save_dhcp_config(ssh, subnets, reservations)
        
        return {"message": "Резервирование удалено"}
    finally:
        ssh.disconnect()


@router.get("/leases", response_model=List[DHCPLease])
async def get_leases(
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Get list of active DHCP leases."""
    ssh = get_dhcp_ssh(server_id)
    
    try:
        exit_code, stdout, stderr = ssh.execute(f"cat {DHCPD_LEASES_PATH}")
        if exit_code != 0:
            raise HTTPException(status_code=500, detail=f"Ошибка чтения аренд: {stderr}")
        
        leases = parse_dhcpd_leases(stdout)
        return leases
    finally:
        ssh.disconnect()
