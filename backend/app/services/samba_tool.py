"""Samba-tool command generation"""
from typing import Optional
from app.models.dns import DNSRecordType

# Kerberos flag for all DNS commands
KERBEROS_FLAG = "--use-kerberos=required"


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
    """Generate samba-tool dns add command."""
    base_cmd = f"samba-tool dns add {server} {zone} {name} {record_type.value}"
    
    if record_type == DNSRecordType.MX:
        mx_priority = priority if priority is not None else 10
        return f'{base_cmd} "{data} {mx_priority}" {KERBEROS_FLAG}'
    
    elif record_type == DNSRecordType.SRV:
        p = srv_priority if srv_priority is not None else 0
        w = srv_weight if srv_weight is not None else 100
        port = srv_port if srv_port is not None else 0
        return f'{base_cmd} "{data} {port} {p} {w}" {KERBEROS_FLAG}'
    
    elif record_type == DNSRecordType.TXT:
        return f'{base_cmd} "{data}" {KERBEROS_FLAG}'
    
    else:
        return f"{base_cmd} {data} {KERBEROS_FLAG}"


def generate_dns_delete_command(
    server: str,
    zone: str,
    name: str,
    record_type: DNSRecordType,
    data: str,
) -> str:
    """Generate samba-tool dns delete command."""
    base_cmd = f"samba-tool dns delete {server} {zone} {name} {record_type.value}"
    
    if record_type in (DNSRecordType.TXT, DNSRecordType.MX, DNSRecordType.SRV):
        return f'{base_cmd} "{data}" {KERBEROS_FLAG}'
    
    return f"{base_cmd} {data} {KERBEROS_FLAG}"


def generate_dns_query_command(
    server: str,
    zone: str,
    name: str = "@",
    record_type: Optional[str] = None,
) -> str:
    """Generate samba-tool dns query command."""
    cmd = f"samba-tool dns query {server} {zone} {name}"
    
    if record_type:
        cmd += f" {record_type}"
    else:
        cmd += " ALL"
    
    return f"{cmd} {KERBEROS_FLAG}"


def generate_dns_zonelist_command(server: str) -> str:
    """Generate samba-tool dns zonelist command."""
    return f"samba-tool dns zonelist {server} {KERBEROS_FLAG}"


# GPO commands

def generate_gpo_listall_command() -> str:
    """Generate samba-tool gpo listall command."""
    return "samba-tool gpo listall"


def generate_gpo_create_command(name: str) -> str:
    """Generate samba-tool gpo create command."""
    return f'samba-tool gpo create "{name}"'


def generate_gpo_delete_command(gpo_guid: str) -> str:
    """Generate samba-tool gpo del command."""
    return f"samba-tool gpo del {gpo_guid}"


def generate_gpo_setlink_command(container_dn: str, gpo_guid: str) -> str:
    """Generate samba-tool gpo setlink command."""
    return f'samba-tool gpo setlink "{container_dn}" {gpo_guid}'


def generate_gpo_dellink_command(container_dn: str, gpo_guid: str) -> str:
    """Generate samba-tool gpo dellink command."""
    return f'samba-tool gpo dellink "{container_dn}" {gpo_guid}'
