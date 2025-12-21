"""DNS API endpoints"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
import traceback
import re

from app.api.auth import get_current_user
from app.models.dns import DNSZone, DNSRecordCreate, DNSRecordResponse, DNSRecordType
from app.services.server_store import server_store
from app.services.ssh import SSHService
from app.services.ssh_pool import ssh_pool
from app.services.kerberos import ensure_kerberos_ticket
from app.services.samba_tool import (
    generate_dns_zonelist_command,
    generate_dns_add_command,
    generate_dns_delete_command,
    KERBEROS_FLAG,
)
from app.logger import get_logger

logger = get_logger("api.dns")

router = APIRouter(prefix="/api/dns", tags=["dns"])


def get_dns_ssh(server_id: str, use_pool: bool = True) -> tuple[SSHService, bool]:
    """Get SSH service for DNS operations.
    
    Returns:
        Tuple of (ssh, from_pool) - from_pool=True означает не закрывать соединение
    """
    server = server_store.get_by_id(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Сервер не найден")
    
    if not server.services.dns:
        raise HTTPException(status_code=400, detail="DNS сервис недоступен на этом сервере")
    
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
    
    # Ensure Kerberos ticket for samba-tool
    success, error = ensure_kerberos_ticket(ssh, server.user)
    if not success:
        if not from_pool:
            ssh.disconnect()
        raise HTTPException(status_code=500, detail=f"Ошибка Kerberos: {error}")
    
    return ssh, from_pool



def release_ssh(ssh: SSHService, from_pool: bool) -> None:
    """Освободить SSH соединение."""
    if not from_pool:
        ssh.disconnect()


def sort_dns_zones(zones: list, domain_dn: str) -> list:
    """Sort DNS zones: domain zone first, RootDNSServers last.
    
    Args:
        zones: List of DNSZone objects
        domain_dn: Domain DN like DC=ag,DC=local
    
    Returns:
        Sorted list of zones
    """
    # Extract domain name from domain_dn: DC=ag,DC=local -> ag.local
    parts = [p.split('=')[1] for p in domain_dn.split(',') if p.startswith('DC=')]
    domain_name = '.'.join(parts).lower() if parts else None
    
    def zone_sort_key(zone):
        name = zone.name.lower()
        # RootDNSServers always last
        if name == 'rootdnsservers':
            return (2, name)
        # Domain zone first
        if domain_name and name == domain_name:
            return (0, name)
        # Others in between
        return (1, name)
    
    return sorted(zones, key=zone_sort_key)


def get_domain_dn(ssh: SSHService, server) -> str:
    """Get domain DN from server config or RootDSE."""
    if server.base_dn:
        logger.info(f"Using configured Base DN: {server.base_dn}")
        return server.base_dn
        
    # Query RootDSE
    cmd = f"ldbsearch -H /var/lib/samba/private/sam.ldb -b '' -s base defaultNamingContext"
    logger.debug(f"RootDSE search cmd: {cmd}")
    exit_code, stdout, stderr = ssh.execute(cmd)
    
    if exit_code == 0:
        for line in stdout.split('\n'):
            line = line.strip()
            if line.startswith('defaultNamingContext:'):
                return line.split(':', 1)[1].strip()
    else:
        logger.warning(f"RootDSE search failed: {stderr}")

    # Fallback
                
    # Fallback to trying to construct from domain name if available, or error?
    # For now let's hope we have it or can construct it from server host (subdomain assumption might be wrong)
    # But usually RootDSE works. If not, let's try to infer from hostname if it looks like a domain
    parts = server.host.split('.')
    if len(parts) > 1:
        # Assuming host is like dc1.domain.local
        return ",".join([f"DC={p}" for p in parts[1:]])
    
    raise HTTPException(status_code=500, detail="Не удалось определить Base DN домена")


@router.get("/zones", response_model=List[DNSZone])
async def get_zones(
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Get list of DNS zones using ldbsearch."""
    ssh, from_pool = get_dns_ssh(server_id)
    server = server_store.get_by_id(server_id)
    
    try:
        domain_dn = get_domain_dn(ssh, server)
        zones = []
        
        # Helper to search in a partition
        def search_partition(partition_dn):
            cmd = f'ldbsearch -H /var/lib/samba/private/sam.ldb -b "{partition_dn},{domain_dn}" "(objectClass=dnsZone)" name'
            logger.debug(f"Zone search cmd: {cmd}")
            exit_code, stdout, stderr = ssh.execute(cmd)
            
            if exit_code != 0:
                logger.warning(f"Zone search failed for {partition_dn}: {stderr}")
                return
                
            for line in stdout.split('\n'):
                line = line.strip()
                if line.startswith('name:'):
                    name = line.split(':', 1)[1].strip()
                    if name and name != '@' and not name.startswith('..'):
                        zone_type = "reverse" if ".in-addr.arpa" in name else "forward"
                        # Avoid duplicates
                        if not any(z.name == name for z in zones):
                            zones.append(DNSZone(name=name, type=zone_type))

        # Search in DomainDnsZones and ForestDnsZones
        search_partition("CN=MicrosoftDNS,DC=DomainDnsZones")
        search_partition("CN=MicrosoftDNS,DC=ForestDnsZones")
        
        # Sort zones: domain zone first, RootDNSServers last
        zones = sort_dns_zones(zones, domain_dn)
        
        logger.debug(f"Parsed zones: {[z.name for z in zones]}")
        return zones
    except Exception as e:
        logger.error(f"Error in get_zones: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        release_ssh(ssh, from_pool)


@router.get("/zones/{zone}/records", response_model=List[DNSRecordResponse])
async def get_zone_records(
    zone: str,
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Get DNS records for a zone using ldbsearch."""
    ssh, from_pool = get_dns_ssh(server_id)
    server = server_store.get_by_id(server_id)
    
    try:
        import re
        
        # Формируем base_dn
        if server.base_dn:
            domain_dn = server.base_dn
        else:
            domain_parts = zone.split(".")
            domain_dn = ",".join([f"DC={p}" for p in domain_parts])
        
        # DNS записи хранятся в DomainDnsZones
        base_dn = f"DC={zone},CN=MicrosoftDNS,DC=DomainDnsZones,{domain_dn}"
        
        # Получаем записи через ldbsearch с dnsRecord
        cmd = f'ldbsearch -H /var/lib/samba/private/sam.ldb -b "{base_dn}" "(objectClass=dnsNode)" name dnsRecord --show-binary'
        logger.debug(f"DNS ldbsearch command: {cmd}")
        exit_code, stdout, stderr = ssh.execute(cmd)
        logger.debug(f"DNS ldbsearch result: exit={exit_code}")
        if exit_code == 0:
            # Ищем запись ldc-test-record для отладки
            if 'ldc-test-record' in stdout:
                idx = stdout.find('ldc-test-record')
                logger.debug(f"ldc-test-record context: {stdout[idx:idx+800]}")
        
        if exit_code != 0:
            base_dn = f"DC={zone},CN=MicrosoftDNS,DC=ForestDnsZones,{domain_dn}"
            cmd = f'ldbsearch -H /var/lib/samba/private/sam.ldb -b "{base_dn}" "(objectClass=dnsNode)" name dnsRecord --show-binary'
            exit_code, stdout, stderr = ssh.execute(cmd)
            
            if exit_code != 0:
                raise HTTPException(status_code=500, detail=f"Ошибка ldbsearch: {stderr}")
        
        # Парсим записи - ищем пары name + IP в ipv4 строке
        records = []
        current_name = None
        current_ips = []
        
        for line in stdout.split('\n'):
            line_stripped = line.strip()
            
            if line_stripped.startswith('name:'):
                # Сохраняем предыдущую запись
                if current_name and current_ips:
                    for ip in current_ips:
                        records.append({
                            'name': current_name,
                            'type': 'A',
                            'data': ip,
                            'ttl': 3600,
                        })
                elif current_name:
                    records.append({
                        'name': current_name,
                        'type': 'A',
                        'data': '',
                        'ttl': 3600,
                    })
                
                current_name = line_stripped.split(':', 1)[1].strip()
                current_ips = []
            elif line_stripped.startswith('ipv4'):
                # Формат: "ipv4                     : 192.168.1.251"
                if ':' in line_stripped:
                    ip = line_stripped.split(':', 1)[1].strip()
                    if ip and re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
                        current_ips.append(ip)
        
        # Последняя запись
        if current_name and current_ips:
            for ip in current_ips:
                records.append({
                    'name': current_name,
                    'type': 'A',
                    'data': ip,
                    'ttl': 3600,
                })
        elif current_name:
            records.append({
                'name': current_name,
                'type': 'A',
                'data': '',
                'ttl': 3600,
            })
        
        # Фильтруем и формируем ответ
        result = []
        seen = set()
        for rec in records:
            name = rec.get('name', '')
            if not name or name == '@' or name.startswith('_') or name.startswith('..'):
                continue
            
            key = f"{name}:{rec.get('data', '')}"
            if key in seen:
                continue
            seen.add(key)
            
            result.append(DNSRecordResponse(
                name=name,
                type=rec.get('type', 'A'),
                data=rec.get('data', ''),
                ttl=rec.get('ttl', 3600),
            ))
        
        logger.debug(f"Found {len(result)} DNS records")
        return result
    finally:
        release_ssh(ssh, from_pool)


@router.post("/zones/{zone}/records")
async def create_record(
    zone: str,
    record: DNSRecordCreate,
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Create a DNS record."""
    import re
    logger.debug(f"create_record: zone={zone}, record={record}")
    ssh, from_pool = get_dns_ssh(server_id)
    server = server_store.get_by_id(server_id)
    
    try:
        # Проверяем, существует ли запись, и удаляем если да
        if server.base_dn:
            domain_dn = server.base_dn
        else:
            domain_parts = zone.split(".")
            domain_dn = ",".join([f"DC={p}" for p in domain_parts])
        
        base_dn = f"DC={zone},CN=MicrosoftDNS,DC=DomainDnsZones,{domain_dn}"
        record_dn = f"DC={record.name},{base_dn}"
        
        check_cmd = f'ldbsearch -H ldap://{server.host} -k yes -b "{record_dn}" -s base dnsRecord --show-binary'
        exit_code, stdout, stderr = ssh.execute(check_cmd)
        
        if exit_code == 0 and 'dnsRecord' in stdout:
            # Запись существует — ищем старое значение и удаляем
            ip_match = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', stdout)
            if ip_match:
                old_value = ip_match.group(1)
                delete_cmd = generate_dns_delete_command(
                    server=server.host,
                    zone=zone,
                    name=record.name,
                    record_type=record.type,
                    data=old_value,
                )
                logger.debug(f"Deleting existing record: {delete_cmd}")
                ssh.execute(delete_cmd)
        
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
        logger.debug(f"DNS add command: {cmd}")
        
        exit_code, stdout, stderr = ssh.execute(cmd)
        logger.debug(f"DNS add result: exit={exit_code}, stdout={stdout}, stderr={stderr}")
        
        if exit_code != 0:
            raise HTTPException(status_code=500, detail=stderr)
        
        return {"message": "DNS запись создана"}
    finally:
        release_ssh(ssh, from_pool)


@router.delete("/zones/{zone}/records/{name}/{record_type}")
async def delete_record(
    zone: str,
    name: str,
    record_type: str,
    data: Optional[str] = Query(None, description="Данные записи (опционально)"),
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Delete a DNS record."""
    import re
    ssh, from_pool = get_dns_ssh(server_id)
    server = server_store.get_by_id(server_id)
    
    try:
        # Если data не передан, ищем значение через ldbsearch
        if not data:
            if server.base_dn:
                domain_dn = server.base_dn
            else:
                domain_parts = zone.split(".")
                domain_dn = ",".join([f"DC={p}" for p in domain_parts])
            
            base_dn = f"DC={zone},CN=MicrosoftDNS,DC=DomainDnsZones,{domain_dn}"
            record_dn = f"DC={name},{base_dn}"
            
            cmd = f'ldbsearch -H ldap://{server.host} -k yes -b "{record_dn}" -s base dnsRecord --show-binary'
            exit_code, stdout, stderr = ssh.execute(cmd)
            
            if exit_code == 0:
                # Ищем ipv4 строку
                for line in stdout.split('\n'):
                    if line.strip().startswith('ipv4'):
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            data = parts[1].strip()
                            break
            
            if not data:
                raise HTTPException(status_code=404, detail="Запись не найдена")
        
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
        release_ssh(ssh, from_pool)


@router.put("/zones/{zone}/records/{name}/{record_type}")
async def update_record(
    zone: str,
    name: str,
    record_type: str,
    update_data: dict,
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Update a DNS record (delete old + create new per Requirement 6.5)."""
    import re
    logger.debug(f"update_record: zone={zone}, name={name}, type={record_type}, data={update_data}")
    ssh, from_pool = get_dns_ssh(server_id)
    server = server_store.get_by_id(server_id)
    
    try:
        new_value = update_data.get("value") or update_data.get("data")
        if not new_value:
            raise HTTPException(status_code=400, detail="Не указано новое значение")
        
        # Сначала получаем текущее значение записи для удаления
        if server.base_dn:
            domain_dn = server.base_dn
        else:
            domain_parts = zone.split(".")
            domain_dn = ",".join([f"DC={p}" for p in domain_parts])
        
        base_dn = f"DC={zone},CN=MicrosoftDNS,DC=DomainDnsZones,{domain_dn}"
        record_dn = f"DC={name},{base_dn}"
        
        cmd = f'ldbsearch -H ldap://{server.host} -k yes -b "{record_dn}" -s base dnsRecord --show-binary'
        exit_code, stdout, stderr = ssh.execute(cmd)
        logger.debug(f"update ldbsearch: exit={exit_code}")
        
        old_value = None
        if exit_code == 0:
            ip_match = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', stdout)
            if ip_match:
                old_value = ip_match.group(1)
        
        logger.debug(f"old_value={old_value}, new_value={new_value}")
        
        # Удаляем старую запись если нашли значение
        if old_value:
            delete_cmd = generate_dns_delete_command(
                server=server.host,
                zone=zone,
                name=name,
                record_type=DNSRecordType(record_type),
                data=old_value,
            )
            logger.debug(f"delete cmd: {delete_cmd}")
            del_exit, del_out, del_err = ssh.execute(delete_cmd)
            logger.debug(f"delete result: exit={del_exit}, err={del_err}")
        
        # Создаём новую запись
        add_cmd = generate_dns_add_command(
            server=server.host,
            zone=zone,
            name=name,
            record_type=DNSRecordType(record_type),
            data=new_value,
        )
        logger.debug(f"add cmd: {add_cmd}")
        
        exit_code, stdout, stderr = ssh.execute(add_cmd)
        logger.debug(f"add result: exit={exit_code}, out={stdout}, err={stderr}")
        
        if exit_code != 0:
            raise HTTPException(status_code=500, detail=stderr)
        
        return {"message": "DNS запись обновлена"}
    finally:
        release_ssh(ssh, from_pool)



@router.get("/all")
async def get_all_dns_data(
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Получить зоны и записи первой forward-зоны одним запросом."""
    import re
    ssh, from_pool = get_dns_ssh(server_id)
    server = server_store.get_by_id(server_id)
    
    try:
        domain_dn = get_domain_dn(ssh, server)
        zones = []
        
        # Helper to search zones
        def search_partition(partition_dn):
            cmd = f'ldbsearch -H /var/lib/samba/private/sam.ldb -b "{partition_dn},{domain_dn}" "(objectClass=dnsZone)" name'
            logger.debug(f"Zone search cmd (all): {cmd}")
            exit_code, stdout, stderr = ssh.execute(cmd)
            
            if exit_code != 0:
                return
                
            for line in stdout.split('\n'):
                line = line.strip()
                if line.startswith('name:'):
                    name = line.split(':', 1)[1].strip()
                    if name and name != '@' and not name.startswith('..'):
                        zone_type = "reverse" if ".in-addr.arpa" in name else "forward"
                        if not any(z.name == name for z in zones):
                            zones.append(DNSZone(name=name, type=zone_type))

        # Get zones
        search_partition("CN=MicrosoftDNS,DC=DomainDnsZones")
        search_partition("CN=MicrosoftDNS,DC=ForestDnsZones")
        
        # Sort zones: domain zone first, RootDNSServers last
        zones = sort_dns_zones(zones, domain_dn)
        
        # Find first forward zone (now domain zone due to sorting)
        first_zone = next((z for z in zones if z.type == "forward"), None)
        records = []
        current_zone = None
        
        if first_zone:
            current_zone = first_zone.name
            
            # Search records in both partitions because the zone could be in either
            # We check where the zone object was found or just search both for records
            # Searching both is safer as we don't track which partition the zone came from above
            
            partitions = [
                f"DC={first_zone.name},CN=MicrosoftDNS,DC=DomainDnsZones,{domain_dn}",
                f"DC={first_zone.name},CN=MicrosoftDNS,DC=ForestDnsZones,{domain_dn}"
            ]
            
            for base_dn in partitions:
                cmd = f'ldbsearch -H /var/lib/samba/private/sam.ldb -b "{base_dn}" "(objectClass=dnsNode)" name dnsRecord --show-binary'
                exit_code, stdout, stderr = ssh.execute(cmd)
                
                if exit_code == 0:
                    # Parse records
                    current_name = None
                    current_ips = []
                    
                    for line in stdout.split('\n'):
                        line_stripped = line.strip()
                        
                        if line_stripped.startswith('name:'):
                            if current_name and current_ips:
                                for ip in current_ips:
                                    records.append({
                                        'name': current_name,
                                        'type': 'A',
                                        'data': ip,
                                        'ttl': 3600,
                                    })
                            elif current_name:
                                records.append({
                                    'name': current_name,
                                    'type': 'A',
                                    'data': '',
                                    'ttl': 3600,
                                })
                            
                            current_name = line_stripped.split(':', 1)[1].strip()
                            current_ips = []
                        elif line_stripped.startswith('ipv4'):
                            if ':' in line_stripped:
                                ip = line_stripped.split(':', 1)[1].strip()
                                if ip and re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
                                    current_ips.append(ip)
                    
                    # Flush last
                    if current_name and current_ips:
                        for ip in current_ips:
                            records.append({
                                'name': current_name,
                                'type': 'A',
                                'data': ip,
                                'ttl': 3600,
                            })
                    elif current_name:
                        records.append({
                            'name': current_name,
                            'type': 'A',
                            'data': '',
                            'ttl': 3600,
                        })

        # Process and filter records
        seen = set()
        filtered_records = []
        for rec in records:
            name = rec.get('name', '')
            if not name or name == '@' or name.startswith('_') or name.startswith('..'):
                continue
            
            key = f"{name}:{rec.get('data', '')}"
            if key in seen:
                continue
            seen.add(key)
            
            filtered_records.append(DNSRecordResponse(
                name=name,
                type=rec.get('type', 'A'),
                data=rec.get('data', ''),
                ttl=rec.get('ttl', 3600),
            ))
        
        return {
            "zones": zones,
            "records": filtered_records,
            "currentZone": current_zone
        }
    except Exception as e:
        logger.error(f"Error in get_all_dns_data: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        release_ssh(ssh, from_pool)
