"""DHCP API endpoints"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List

from app.api.auth import get_current_user
from app.models.dhcp import DHCPSubnet, DHCPSubnetCreate, DHCPReservation, DHCPReservationCreate, DHCPLease
from app.services.server_store import server_store
from app.services.ssh import SSHService
from app.services.ssh_pool import ssh_pool
from app.services.dhcp_parser import parse_dhcpd_conf, serialize_dhcpd_conf, parse_dhcpd_leases

router = APIRouter(prefix="/api/dhcp", tags=["dhcp"])

DHCPD_CONF_PATH = "/etc/dhcp/dhcpd.conf"
DHCPD_LEASES_PATH = "/var/lib/dhcp/dhcpd.leases"


def get_dhcp_ssh(server_id: str, use_pool: bool = True) -> tuple[SSHService, bool]:
    """Get SSH service for DHCP operations.
    
    Returns:
        Tuple of (ssh, from_pool) - from_pool=True означает не закрывать соединение
    """
    server = server_store.get_by_id(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Сервер не найден")
    
    if not server.services.dhcp:
        raise HTTPException(status_code=400, detail="DHCP сервис недоступен на этом сервере")
    
    from_pool = False
    if use_pool:
        try:
            ssh = ssh_pool.get(server)
            from_pool = True
        except ConnectionError as e:
            raise HTTPException(status_code=500, detail=f"Ошибка подключения: {e}")
    else:
        ssh = SSHService(server)
        success, error = ssh.connect()
        if not success:
            raise HTTPException(status_code=500, detail=f"Ошибка подключения: {error}")
    
    return ssh, from_pool


def release_ssh(ssh: SSHService, from_pool: bool) -> None:
    """Освободить SSH соединение."""
    if not from_pool:
        ssh.disconnect()


def load_dhcp_config(ssh: SSHService) -> tuple:
    """Load and parse DHCP config from server."""
    exit_code, stdout, stderr = ssh.execute(f"cat {DHCPD_CONF_PATH}")
    if exit_code != 0:
        raise HTTPException(status_code=500, detail=f"Ошибка чтения конфигурации: {stderr}")
    
    return parse_dhcpd_conf(stdout)


def save_dhcp_config(ssh: SSHService, subnets: List[DHCPSubnet], reservations: List[DHCPReservation]):
    """Save DHCP config to server and reload service."""
    from datetime import datetime
    
    config = serialize_dhcpd_conf(subnets, reservations)
    print(f"[DEBUG] Generated config:\n{config[:500]}")
    
    # Write config to temp file and check syntax
    import base64
    config_b64 = base64.b64encode(config.encode()).decode()
    
    # Записываем во временный файл и проверяем синтаксис
    check_cmd = f'echo "{config_b64}" | base64 -d > /tmp/dhcpd_test.conf && dhcpd -t -cf /tmp/dhcpd_test.conf 2>&1'
    exit_code, stdout, stderr = ssh.execute(check_cmd)
    print(f"[DEBUG] Syntax check: exit={exit_code}, output={stdout}")
    
    if exit_code != 0:
        raise HTTPException(status_code=400, detail=f"Ошибка синтаксиса: {stdout or stderr}")
    
    # Создаём бэкап перед изменением
    backup_name = f"/etc/dhcp/dhcpd.conf.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    ssh.execute(f"cp {DHCPD_CONF_PATH} {backup_name}")
    print(f"[DEBUG] Backup created: {backup_name}")
    
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
    
    # Restart service (reload not supported by isc-dhcp-server)
    exit_code, stdout, stderr = ssh.execute("systemctl restart isc-dhcp-server")
    if exit_code != 0:
        raise HTTPException(status_code=500, detail=f"Ошибка перезапуска сервиса: {stderr}")


@router.get("/subnets", response_model=List[DHCPSubnet])
async def get_subnets(
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Get list of DHCP subnets."""
    ssh, from_pool = get_dhcp_ssh(server_id)
    
    try:
        subnets, _ = load_dhcp_config(ssh)
        return subnets
    finally:
        release_ssh(ssh, from_pool)


@router.post("/subnets", response_model=DHCPSubnet)
async def create_subnet(
    subnet: DHCPSubnetCreate,
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Create a new DHCP subnet."""
    ssh, from_pool = get_dhcp_ssh(server_id)
    
    try:
        subnets, reservations = load_dhcp_config(ssh)
        
        new_subnet = DHCPSubnet(**subnet.model_dump())
        subnets.append(new_subnet)
        
        save_dhcp_config(ssh, subnets, reservations)
        
        return new_subnet
    finally:
        release_ssh(ssh, from_pool)


@router.patch("/subnets/{subnet_id}", response_model=DHCPSubnet)
async def update_subnet(
    subnet_id: str,
    subnet: DHCPSubnetCreate,
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Update a DHCP subnet."""
    ssh, from_pool = get_dhcp_ssh(server_id)
    
    try:
        subnets, reservations = load_dhcp_config(ssh)
        
        for i, s in enumerate(subnets):
            if s.id == subnet_id:
                # Новый id формируется из network_netmask
                new_id = f"{subnet.network}_{subnet.netmask}"
                updated = DHCPSubnet(id=new_id, **subnet.model_dump())
                subnets[i] = updated
                save_dhcp_config(ssh, subnets, reservations)
                return updated
        
        raise HTTPException(status_code=404, detail="Подсеть не найдена")
    finally:
        release_ssh(ssh, from_pool)


@router.delete("/subnets/{subnet_id}")
async def delete_subnet(
    subnet_id: str,
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Delete a DHCP subnet."""
    ssh, from_pool = get_dhcp_ssh(server_id)
    
    try:
        subnets, reservations = load_dhcp_config(ssh)
        
        original_len = len(subnets)
        subnets = [s for s in subnets if s.id != subnet_id]
        
        if len(subnets) == original_len:
            raise HTTPException(status_code=404, detail="Подсеть не найдена")
        
        save_dhcp_config(ssh, subnets, reservations)
        
        return {"message": "Подсеть удалена"}
    finally:
        release_ssh(ssh, from_pool)


@router.get("/reservations", response_model=List[DHCPReservation])
async def get_reservations(
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Get list of DHCP reservations."""
    ssh, from_pool = get_dhcp_ssh(server_id)
    
    try:
        _, reservations = load_dhcp_config(ssh)
        return reservations
    finally:
        release_ssh(ssh, from_pool)


@router.post("/reservations", response_model=DHCPReservation)
async def create_reservation(
    reservation: DHCPReservationCreate,
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Create a new DHCP reservation."""
    print(f"[DEBUG] create_reservation: {reservation}")
    ssh, from_pool = get_dhcp_ssh(server_id)
    
    try:
        subnets, reservations = load_dhcp_config(ssh)
        print(f"[DEBUG] Loaded {len(subnets)} subnets, {len(reservations)} reservations")
        
        new_reservation = DHCPReservation(**reservation.model_dump())
        reservations.append(new_reservation)
        
        save_dhcp_config(ssh, subnets, reservations)
        
        return new_reservation
    except Exception as e:
        print(f"[DEBUG] Error creating reservation: {e}")
        raise
    finally:
        release_ssh(ssh, from_pool)


@router.delete("/reservations/{reservation_id}")
async def delete_reservation(
    reservation_id: str,
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Delete a DHCP reservation."""
    ssh, from_pool = get_dhcp_ssh(server_id)
    
    try:
        subnets, reservations = load_dhcp_config(ssh)
        
        original_len = len(reservations)
        reservations = [r for r in reservations if r.id != reservation_id]
        
        if len(reservations) == original_len:
            raise HTTPException(status_code=404, detail="Резервирование не найдено")
        
        save_dhcp_config(ssh, subnets, reservations)
        
        return {"message": "Резервирование удалено"}
    finally:
        release_ssh(ssh, from_pool)


@router.get("/leases", response_model=List[DHCPLease])
async def get_leases(
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Get list of active DHCP leases."""
    ssh, from_pool = get_dhcp_ssh(server_id)
    
    try:
        exit_code, stdout, stderr = ssh.execute(f"cat {DHCPD_LEASES_PATH}")
        if exit_code != 0:
            raise HTTPException(status_code=500, detail=f"Ошибка чтения аренд: {stderr}")
        
        leases = parse_dhcpd_leases(stdout)
        return leases
    finally:
        release_ssh(ssh, from_pool)


@router.get("/all")
async def get_all_dhcp_data(
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Получить все DHCP данные одним запросом."""
    ssh, from_pool = get_dhcp_ssh(server_id)
    
    try:
        subnets, reservations = load_dhcp_config(ssh)
        
        exit_code, stdout, _ = ssh.execute(f"cat {DHCPD_LEASES_PATH}")
        leases = parse_dhcpd_leases(stdout) if exit_code == 0 else []
        
        return {
            "subnets": subnets,
            "reservations": reservations,
            "leases": leases
        }
    finally:
        release_ssh(ssh, from_pool)
