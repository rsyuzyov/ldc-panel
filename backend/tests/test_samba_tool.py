"""Property-based tests for samba-tool command generation"""
import pytest
from hypothesis import given, strategies as st, settings

from app.models.dns import DNSRecordType
from app.services.samba_tool import (
    generate_dns_add_command,
    generate_dns_delete_command,
    generate_dns_query_command,
    generate_gpo_create_command,
    generate_gpo_delete_command,
    generate_gpo_setlink_command,
)


# Strategies
dns_names = st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-_.'))
zone_names = st.text(min_size=3, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-.'))
ipv4_addresses = st.from_regex(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', fullmatch=True)
hostnames = st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-.'))


# **Feature: ldc-panel, Property 13: DNS command generation**
# **Validates: Requirements 6.3**
@given(
    server=hostnames,
    zone=zone_names,
    name=dns_names,
    ip=ipv4_addresses,
)
@settings(max_examples=100)
def test_dns_a_record_command_generation(server: str, zone: str, name: str, ip: str):
    """For any A record, generated samba-tool dns add command should contain correct parameters."""
    cmd = generate_dns_add_command(
        server=server,
        zone=zone,
        name=name,
        record_type=DNSRecordType.A,
        data=ip,
    )
    
    # Should contain samba-tool dns add
    assert "samba-tool dns add" in cmd
    
    # Should contain server, zone, name
    assert server in cmd
    assert zone in cmd
    assert name in cmd
    
    # Should contain record type
    assert " A " in cmd
    
    # Should contain IP address
    assert ip in cmd


@given(
    server=hostnames,
    zone=zone_names,
    name=dns_names,
    target=hostnames,
)
@settings(max_examples=100)
def test_dns_cname_record_command_generation(server: str, zone: str, name: str, target: str):
    """For any CNAME record, generated command should contain correct parameters."""
    cmd = generate_dns_add_command(
        server=server,
        zone=zone,
        name=name,
        record_type=DNSRecordType.CNAME,
        data=target,
    )
    
    assert "samba-tool dns add" in cmd
    assert " CNAME " in cmd
    assert target in cmd


@given(
    server=hostnames,
    zone=zone_names,
    name=dns_names,
    target=hostnames,
    priority=st.integers(min_value=0, max_value=100),
)
@settings(max_examples=100)
def test_dns_mx_record_command_generation(server: str, zone: str, name: str, target: str, priority: int):
    """For any MX record, generated command should contain target and priority."""
    cmd = generate_dns_add_command(
        server=server,
        zone=zone,
        name=name,
        record_type=DNSRecordType.MX,
        data=target,
        priority=priority,
    )
    
    assert "samba-tool dns add" in cmd
    assert " MX " in cmd
    assert target in cmd
    assert str(priority) in cmd


# **Feature: ldc-panel, Property 14: GPO command generation**
# **Validates: Requirements 8.2, 8.3, 8.5**
@given(name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() and '"' not in x))
@settings(max_examples=100)
def test_gpo_create_command_generation(name: str):
    """For any GPO name, generated samba-tool gpo create command should have correct syntax."""
    cmd = generate_gpo_create_command(name)
    
    assert "samba-tool gpo create" in cmd
    assert f'"{name}"' in cmd


@given(gpo_guid=st.uuids().map(lambda x: f"{{{str(x).upper()}}}"))
@settings(max_examples=100)
def test_gpo_delete_command_generation(gpo_guid: str):
    """For any GPO GUID, generated samba-tool gpo del command should have correct syntax."""
    cmd = generate_gpo_delete_command(gpo_guid)
    
    assert "samba-tool gpo del" in cmd
    assert gpo_guid in cmd


@given(
    container_dn=st.text(min_size=5, max_size=100).filter(lambda x: x.strip() and '"' not in x),
    gpo_guid=st.uuids().map(lambda x: f"{{{str(x).upper()}}}"),
)
@settings(max_examples=100)
def test_gpo_setlink_command_generation(container_dn: str, gpo_guid: str):
    """For any container DN and GPO GUID, generated setlink command should have correct syntax."""
    cmd = generate_gpo_setlink_command(container_dn, gpo_guid)
    
    assert "samba-tool gpo setlink" in cmd
    assert f'"{container_dn}"' in cmd
    assert gpo_guid in cmd


def test_dns_srv_record_command():
    """Test SRV record command generation."""
    cmd = generate_dns_add_command(
        server="dc1.domain.local",
        zone="domain.local",
        name="_ldap._tcp",
        record_type=DNSRecordType.SRV,
        data="dc1.domain.local",
        srv_priority=0,
        srv_weight=100,
        srv_port=389,
    )
    
    assert "samba-tool dns add" in cmd
    assert " SRV " in cmd
    assert "dc1.domain.local" in cmd
    assert "389" in cmd


def test_dns_txt_record_command():
    """Test TXT record command generation."""
    cmd = generate_dns_add_command(
        server="dc1.domain.local",
        zone="domain.local",
        name="@",
        record_type=DNSRecordType.TXT,
        data="v=spf1 include:_spf.domain.local ~all",
    )
    
    assert "samba-tool dns add" in cmd
    assert " TXT " in cmd
    assert '"v=spf1' in cmd
