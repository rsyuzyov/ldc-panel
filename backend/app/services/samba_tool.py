"""Samba-tool command generation"""
from typing import Optional
from app.models.dns import DNSRecordType


def generate_dns_add_command(
    server: str,
    zone: str,
    name: str,
    record_type: DNSRecordType,
    data: str,
    priority: Optional[int] = None,
    srv_priority: Optional[int] = None,
    srv_weight: Optional[int] = None,
    srv_port: Optional[int] = None,
) -> str:
    """Generate samba-tool dns add command.
    
    Args:
        server: DNS server hostname
        zone: DNS zone name
        name: Record name
        record_type: Record type (A, AAAA, CNAME, MX, TXT, SRV)
        data: Record data
        priority: MX priority
        srv_priority: SRV priority
        srv_weight: SRV weight
        srv_port: SRV port
        
    Returns:
        samba-tool dns add command string
    """
    base_cmd = f"samba-tool dns add {server} {zone} {name} {record_type.value}"
    
    if record_type == DNSRecordType.MX:
        # MX format: samba-tool dns add server zone name MX "target priority"
        mx_priority = priority if priority is not None else 10
        return f'{base_cmd} "{data} {mx_priority}"'
    
    elif record_type == DNSRecordType.SRV:
        # SRV format: samba-tool dns add server zone name SRV "target port priority weight"
        p = srv_priority if srv_priority is not None else 0
        w = srv_weight if srv_weight is not None else 100
        port = srv_port if srv_port is not None else 0
        return f'{base_cmd} "{data} {port} {p} {w}"'
    
    elif record_type == DNSRecordType.TXT:
        # TXT records need quotes
        return f'{base_cmd} "{data}"'
    
    else:
        # A, AAAA, CNAME, PTR, NS
        return f"{base_cmd} {data}"


def generate_dns_delete_command(
    server: str,
    zone: str,
    name: str,
    record_type: DNSRecordType,
    data: str,
) -> str:
    """Generate samba-tool dns delete command.
    
    Args:
        server: DNS server hostname
        zone: DNS zone name
        name: Record name
        record_type: Record type
        data: Record data
        
    Returns:
        samba-tool dns delete command string
    """
    base_cmd = f"samba-tool dns delete {server} {zone} {name} {record_type.value}"
    
    if record_type in (DNSRecordType.TXT, DNSRecordType.MX, DNSRecordType.SRV):
        return f'{base_cmd} "{data}"'
    
    return f"{base_cmd} {data}"


def generate_dns_query_command(
    server: str,
    zone: str,
    name: str = "@",
    record_type: Optional[str] = None,
) -> str:
    """Generate samba-tool dns query command.
    
    Args:
        server: DNS server hostname
        zone: DNS zone name
        name: Record name (@ for zone root)
        record_type: Optional record type filter
        
    Returns:
        samba-tool dns query command string
    """
    cmd = f"samba-tool dns query {server} {zone} {name}"
    
    if record_type:
        cmd += f" {record_type}"
    else:
        cmd += " ALL"
    
    return cmd


def generate_dns_zonelist_command(server: str) -> str:
    """Generate samba-tool dns zonelist command.
    
    Args:
        server: DNS server hostname
        
    Returns:
        samba-tool dns zonelist command string
    """
    return f"samba-tool dns zonelist {server}"


# GPO commands

def generate_gpo_listall_command() -> str:
    """Generate samba-tool gpo listall command.
    
    Returns:
        samba-tool gpo listall command string
    """
    return "samba-tool gpo listall"


def generate_gpo_create_command(name: str) -> str:
    """Generate samba-tool gpo create command.
    
    Args:
        name: GPO name
        
    Returns:
        samba-tool gpo create command string
    """
    return f'samba-tool gpo create "{name}"'


def generate_gpo_delete_command(gpo_guid: str) -> str:
    """Generate samba-tool gpo del command.
    
    Args:
        gpo_guid: GPO GUID
        
    Returns:
        samba-tool gpo del command string
    """
    return f"samba-tool gpo del {gpo_guid}"


def generate_gpo_setlink_command(container_dn: str, gpo_guid: str) -> str:
    """Generate samba-tool gpo setlink command.
    
    Args:
        container_dn: Container DN (OU or domain)
        gpo_guid: GPO GUID
        
    Returns:
        samba-tool gpo setlink command string
    """
    return f'samba-tool gpo setlink "{container_dn}" {gpo_guid}'


def generate_gpo_dellink_command(container_dn: str, gpo_guid: str) -> str:
    """Generate samba-tool gpo dellink command.
    
    Args:
        container_dn: Container DN
        gpo_guid: GPO GUID
        
    Returns:
        samba-tool gpo dellink command string
    """
    return f'samba-tool gpo dellink "{container_dn}" {gpo_guid}'
