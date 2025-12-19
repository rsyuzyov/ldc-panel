"""DNS API endpoints"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List

from app.api.auth import get_current_user
from app.models.dns import DNSZone, DNSRecordCreate, DNSRecordResponse, DNSRecordType
from app.services.server_store import server_store
from app.services.ssh import SSHService
from app.services.kerberos import ensure_kerberos_ticket
from app.services.samba_tool import (
    generate_dns_zonelist_command,
    generate_dns_add_command,
    generate_dns_delete_command,
)

router = APIRouter(prefix="/api/dns", tags=["dns"])


def get_dns_ssh(server_id: str) -> SSHService:
    """Get SSH service for DNS operations."""
    server = server_store.get_by_id(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Сервер не найден")
    
    if not server.services.dns:
        raise HTTPException(status_code=400, detail="DNS сервис недоступен на этом сервере")
    
    ssh = SSHService(server)
    success, error = ssh.connect()
    if not success:
        raise HTTPException(status_code=500, detail=f"Ошибка подключения: {error}")
    
    # Ensure Kerberos ticket for samba-tool
    success, error = ensure_kerberos_ticket(ssh, server.user)
    if not success:
        ssh.disconnect()
        raise HTTPException(status_code=500, detail=f"Ошибка Kerberos: {error}")
    
    return ssh


@router.get("/zones", response_model=List[DNSZone])
async def get_zones(
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Get list of DNS zones."""
    ssh = get_dns_ssh(server_id)
    server = server_store.get_by_id(server_id)
    
    try:
        cmd = generate_dns_zonelist_command(server.host)
        exit_code, stdout, stderr = ssh.execute(cmd)
        
        print(f"[DEBUG] DNS zonelist: exit_code={exit_code}, stdout={stdout[:200] if stdout else ''}")
        
        if exit_code != 0:
            raise HTTPException(status_code=500, detail=stderr)
        
        zones = []
        for line in stdout.split('\n'):
            line = line.strip()
            # Parse only pszZoneName lines
            if line.startswith('pszZoneName') and ':' in line:
                zone_name = line.split(':', 1)[1].strip()
                if zone_name:
                    zone_type = "reverse" if ".in-addr.arpa" in zone_name else "forward"
                    zones.append(DNSZone(name=zone_name, type=zone_type))
        
        print(f"[DEBUG] Parsed zones: {[z.name for z in zones]}")
        return zones
    finally:
        ssh.disconnect()


@router.get("/zones/{zone}/records", response_model=List[DNSRecordResponse])
async def get_zone_records(
    zone: str,
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Get DNS records for a zone using ldbsearch."""
    ssh = get_dns_ssh(server_id)
    server = server_store.get_by_id(server_id)
    
    try:
        # Получаем записи через ldbsearch (по требованиям спеки)
        # Формируем base DN для зоны
        domain_parts = zone.split(".")
        domain_dn = ",".join([f"DC={p}" for p in domain_parts])
        base_dn = f"DC={zone},CN=MicrosoftDNS,DC=DomainDnsZones,{domain_dn}"
        
        cmd = f'ldbsearch -H ldap://{server.host} -k yes -b "{base_dn}" "(objectClass=dnsNode)" dn name'
        print(f"[DEBUG] DNS ldbsearch command: {cmd}")
        exit_code, stdout, stderr = ssh.execute(cmd)
        print(f"[DEBUG] DNS ldbsearch result: exit={exit_code}, stdout={stdout[:500] if stdout else ''}")
        
        if exit_code != 0:
            # Попробуем ForestDnsZones для корневых зон
            base_dn = f"DC={zone},CN=MicrosoftDNS,DC=ForestDnsZones,{domain_dn}"
            cmd = f'ldbsearch -H ldap://{server.host} -k yes -b "{base_dn}" "(objectClass=dnsNode)" dn name'
            exit_code, stdout, stderr = ssh.execute(cmd)
            
            if exit_code != 0:
                raise HTTPException(status_code=500, detail=f"Ошибка ldbsearch: {stderr}")
        
        # Парсим имена записей из ldbsearch
        record_names = []
        current_name = None
        for line in stdout.split('\n'):
            line = line.strip()
            if line.startswith('name:'):
                name = line.split(':', 1)[1].strip()
                if name and name != '@':
                    record_names.append(name)
        
        print(f"[DEBUG] Found {len(record_names)} record names")
        
        # Для каждой записи получаем детали через отдельный ldbsearch с dnsRecord
        records = []
        for name in record_names:
            # Пропускаем служебные записи
            if name.startswith('_') or name.startswith('..'):
                continue
            
            record_dn = f"DC={name},{base_dn}"
            cmd = f'ldbsearch -H ldap://{server.host} -k yes -b "{record_dn}" -s base dnsRecord --show-binary'
            exit_code, stdout, stderr = ssh.execute(cmd)
            
            if exit_code != 0:
                continue
            
            # Парсим dnsRecord (бинарные данные, но можно извлечь тип и значение)
            # Простой парсинг: ищем IP адреса в выводе
            for line in stdout.split('\n'):
                # A записи обычно содержат IP в формате x.x.x.x
                import re
                ip_match = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', line)
                if ip_match and 'dnsRecord' in line:
                    records.append(DNSRecordResponse(
                        name=name,
                        type='A',
                        data=ip_match.group(1),
                        ttl=3600,
                    ))
                    break
        
        # Если не нашли записи через детальный парсинг, вернём хотя бы имена
        if not records and record_names:
            for name in record_names[:50]:  # Лимит
                if not name.startswith('_') and not name.startswith('..'):
                    records.append(DNSRecordResponse(
                        name=name,
                        type='A',
                        data='(см. детали)',
                        ttl=3600,
                    ))
        
        return records
    finally:
        ssh.disconnect()


@router.post("/zones/{zone}/records")
async def create_record(
    zone: str,
    record: DNSRecordCreate,
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Create a DNS record."""
    ssh = get_dns_ssh(server_id)
    server = server_store.get_by_id(server_id)
    
    try:
        cmd = generate_dns_add_command(
            server=server.host,
            zone=zone,
            name=record.name,
            record_type=record.type,
            data=record.data,
            priority=record.priority,
            srv_priority=record.srv_priority,
            srv_weight=record.srv_weight,
            srv_port=record.srv_port,
        )
        
        exit_code, stdout, stderr = ssh.execute(cmd)
        
        if exit_code != 0:
            raise HTTPException(status_code=500, detail=stderr)
        
        return {"message": "DNS запись создана"}
    finally:
        ssh.disconnect()


@router.delete("/zones/{zone}/records/{name}/{record_type}")
async def delete_record(
    zone: str,
    name: str,
    record_type: str,
    data: str = Query(..., description="Данные записи"),
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Delete a DNS record."""
    ssh = get_dns_ssh(server_id)
    server = server_store.get_by_id(server_id)
    
    try:
        cmd = generate_dns_delete_command(
            server=server.host,
            zone=zone,
            name=name,
            record_type=DNSRecordType(record_type),
            data=data,
        )
        
        exit_code, stdout, stderr = ssh.execute(cmd)
        
        if exit_code != 0:
            raise HTTPException(status_code=500, detail=stderr)
        
        return {"message": "DNS запись удалена"}
    finally:
        ssh.disconnect()
