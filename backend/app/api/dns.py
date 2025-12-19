"""DNS API endpoints"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List

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


@router.get("/zones", response_model=List[DNSZone])
async def get_zones(
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Get list of DNS zones."""
    ssh, from_pool = get_dns_ssh(server_id)
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
        cmd = f'ldbsearch -H ldap://{server.host} -k yes -b "{base_dn}" "(objectClass=dnsNode)" name dnsRecord --show-binary'
        print(f"[DEBUG] DNS ldbsearch command: {cmd}")
        exit_code, stdout, stderr = ssh.execute(cmd)
        print(f"[DEBUG] DNS ldbsearch result: exit={exit_code}")
        if exit_code == 0:
            # Ищем запись ldc-test-record для отладки
            if 'ldc-test-record' in stdout:
                idx = stdout.find('ldc-test-record')
                print(f"[DEBUG] ldc-test-record context: {stdout[idx:idx+800]}")
        
        if exit_code != 0:
            base_dn = f"DC={zone},CN=MicrosoftDNS,DC=ForestDnsZones,{domain_dn}"
            cmd = f'ldbsearch -H ldap://{server.host} -k yes -b "{base_dn}" "(objectClass=dnsNode)" name dnsRecord --show-binary'
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
        
        print(f"[DEBUG] Found {len(result)} DNS records")
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
    print(f"[DEBUG] create_record: zone={zone}, record={record}")
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
                print(f"[DEBUG] Deleting existing record: {delete_cmd}")
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
        print(f"[DEBUG] DNS add command: {cmd}")
        
        exit_code, stdout, stderr = ssh.execute(cmd)
        print(f"[DEBUG] DNS add result: exit={exit_code}, stdout={stdout}, stderr={stderr}")
        
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
    print(f"[DEBUG] update_record: zone={zone}, name={name}, type={record_type}, data={update_data}")
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
        print(f"[DEBUG] update ldbsearch: exit={exit_code}")
        
        old_value = None
        if exit_code == 0:
            ip_match = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', stdout)
            if ip_match:
                old_value = ip_match.group(1)
        
        print(f"[DEBUG] old_value={old_value}, new_value={new_value}")
        
        # Удаляем старую запись если нашли значение
        if old_value:
            delete_cmd = generate_dns_delete_command(
                server=server.host,
                zone=zone,
                name=name,
                record_type=DNSRecordType(record_type),
                data=old_value,
            )
            print(f"[DEBUG] delete cmd: {delete_cmd}")
            del_exit, del_out, del_err = ssh.execute(delete_cmd)
            print(f"[DEBUG] delete result: exit={del_exit}, err={del_err}")
        
        # Создаём новую запись
        add_cmd = generate_dns_add_command(
            server=server.host,
            zone=zone,
            name=name,
            record_type=DNSRecordType(record_type),
            data=new_value,
        )
        print(f"[DEBUG] add cmd: {add_cmd}")
        
        exit_code, stdout, stderr = ssh.execute(add_cmd)
        print(f"[DEBUG] add result: exit={exit_code}, out={stdout}, err={stderr}")
        
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
        # Получаем зоны
        cmd = generate_dns_zonelist_command(server.host)
        exit_code, stdout, stderr = ssh.execute(cmd)
        
        if exit_code != 0:
            raise HTTPException(status_code=500, detail=stderr)
        
        zones = []
        for line in stdout.split('\n'):
            line = line.strip()
            if line.startswith('pszZoneName') and ':' in line:
                zone_name = line.split(':', 1)[1].strip()
                if zone_name:
                    zone_type = "reverse" if ".in-addr.arpa" in zone_name else "forward"
                    zones.append(DNSZone(name=zone_name, type=zone_type))
        
        # Находим первую forward-зону
        first_zone = next((z for z in zones if z.type == "forward"), None)
        records = []
        current_zone = None
        
        if first_zone:
            current_zone = first_zone.name
            
            # Формируем base_dn
            if server.base_dn:
                domain_dn = server.base_dn
            else:
                domain_parts = first_zone.name.split(".")
                domain_dn = ",".join([f"DC={p}" for p in domain_parts])
            
            base_dn = f"DC={first_zone.name},CN=MicrosoftDNS,DC=DomainDnsZones,{domain_dn}"
            cmd = f'ldbsearch -H ldap://{server.host} -k yes -b "{base_dn}" "(objectClass=dnsNode)" name dnsRecord --show-binary'
            exit_code, stdout, stderr = ssh.execute(cmd)
            
            if exit_code != 0:
                base_dn = f"DC={first_zone.name},CN=MicrosoftDNS,DC=ForestDnsZones,{domain_dn}"
                cmd = f'ldbsearch -H ldap://{server.host} -k yes -b "{base_dn}" "(objectClass=dnsNode)" name dnsRecord --show-binary'
                exit_code, stdout, stderr = ssh.execute(cmd)
            
            if exit_code == 0:
                # Парсим записи
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
                
                # Фильтруем
                seen = set()
                filtered = []
                for rec in records:
                    name = rec.get('name', '')
                    if not name or name == '@' or name.startswith('_') or name.startswith('..'):
                        continue
                    key = f"{name}:{rec.get('data', '')}"
                    if key in seen:
                        continue
                    seen.add(key)
                    filtered.append(DNSRecordResponse(
                        name=name,
                        type=rec.get('type', 'A'),
                        data=rec.get('data', ''),
                        ttl=rec.get('ttl', 3600),
                    ))
                records = filtered
        
        return {
            "zones": zones,
            "records": records,
            "currentZone": current_zone
        }
    finally:
        release_ssh(ssh, from_pool)
