"""Property-based tests for DHCP parser"""
import pytest
from hypothesis import given, strategies as st, settings, assume

from app.models.dhcp import DHCPSubnet, DHCPReservation
from app.services.dhcp_parser import parse_dhcpd_conf, serialize_dhcpd_conf


# Strategies
ipv4_octets = st.integers(min_value=0, max_value=255)
ipv4_addresses = st.tuples(ipv4_octets, ipv4_octets, ipv4_octets, ipv4_octets).map(
    lambda t: f"{t[0]}.{t[1]}.{t[2]}.{t[3]}"
)
netmasks = st.sampled_from(["255.255.255.0", "255.255.0.0", "255.0.0.0", "255.255.255.128"])
hostnames = st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-'))
mac_addresses = st.tuples(
    *[st.integers(min_value=0, max_value=255) for _ in range(6)]
).map(lambda t: ":".join(f"{x:02x}" for x in t))


@st.composite
def dhcp_subnets(draw):
    """Generate valid DHCP subnets."""
    network = draw(ipv4_addresses)
    netmask = draw(netmasks)
    
    # Range must have both start and end, or neither (valid dhcpd.conf constraint)
    has_range = draw(st.booleans())
    if has_range:
        range_start = draw(ipv4_addresses)
        range_end = draw(ipv4_addresses)
    else:
        range_start = None
        range_end = None
    
    return DHCPSubnet(
        id=draw(st.text(min_size=4, max_size=8, alphabet=st.characters(whitelist_categories=('L', 'N')))),
        network=network,
        netmask=netmask,
        range_start=range_start,
        range_end=range_end,
        routers=draw(st.one_of(st.none(), ipv4_addresses)),
        domain_name_servers=draw(st.one_of(st.none(), ipv4_addresses)),
        domain_name=draw(st.one_of(st.none(), st.text(min_size=3, max_size=30, alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-.')))),
        default_lease_time=draw(st.integers(min_value=3600, max_value=604800)),
        max_lease_time=draw(st.integers(min_value=7200, max_value=1209600)),
    )


@st.composite
def dhcp_reservations(draw):
    """Generate valid DHCP reservations."""
    return DHCPReservation(
        id=draw(st.text(min_size=4, max_size=8, alphabet=st.characters(whitelist_categories=('L', 'N')))),
        hostname=draw(hostnames),
        mac=draw(mac_addresses),
        ip=draw(ipv4_addresses),
    )


# **Feature: ldc-panel, Property 12: DHCP config round-trip**
# **Validates: Requirements 7.4, 7.5, 7.6**
@given(
    subnets=st.lists(dhcp_subnets(), min_size=1, max_size=3),
    reservations=st.lists(dhcp_reservations(), min_size=0, max_size=5),
)
@settings(max_examples=100)
def test_dhcp_config_roundtrip(subnets: list, reservations: list):
    """For any valid dhcpd.conf, parse → serialize → parse should preserve structure and values."""
    # Ensure unique hostnames for reservations
    seen_hostnames = set()
    unique_reservations = []
    for r in reservations:
        if r.hostname not in seen_hostnames:
            seen_hostnames.add(r.hostname)
            unique_reservations.append(r)
    
    # Serialize
    config = serialize_dhcpd_conf(subnets, unique_reservations)
    
    # Parse
    parsed_subnets, parsed_reservations = parse_dhcpd_conf(config)
    
    # Verify subnets
    assert len(parsed_subnets) == len(subnets)
    
    for original, parsed in zip(subnets, parsed_subnets):
        assert parsed.network == original.network
        assert parsed.netmask == original.netmask
        assert parsed.range_start == original.range_start
        assert parsed.range_end == original.range_end
        assert parsed.routers == original.routers
        assert parsed.default_lease_time == original.default_lease_time
        assert parsed.max_lease_time == original.max_lease_time
    
    # Verify reservations
    assert len(parsed_reservations) == len(unique_reservations)
    
    for original, parsed in zip(unique_reservations, parsed_reservations):
        assert parsed.hostname == original.hostname
        assert parsed.mac.lower() == original.mac.lower()
        assert parsed.ip == original.ip


def test_parse_simple_config():
    """Test parsing a simple dhcpd.conf."""
    config = """
subnet 192.168.1.0 netmask 255.255.255.0 {
    range 192.168.1.100 192.168.1.200;
    option routers 192.168.1.1;
    option domain-name-servers 192.168.1.10;
    option domain-name "test.local";
    default-lease-time 86400;
    max-lease-time 172800;
}

host printer {
    hardware ethernet 00:11:22:33:44:55;
    fixed-address 192.168.1.50;
}
"""
    
    subnets, reservations = parse_dhcpd_conf(config)
    
    assert len(subnets) == 1
    assert subnets[0].network == "192.168.1.0"
    assert subnets[0].netmask == "255.255.255.0"
    assert subnets[0].range_start == "192.168.1.100"
    assert subnets[0].range_end == "192.168.1.200"
    assert subnets[0].routers == "192.168.1.1"
    assert subnets[0].domain_name == "test.local"
    
    assert len(reservations) == 1
    assert reservations[0].hostname == "printer"
    assert reservations[0].mac == "00:11:22:33:44:55"
    assert reservations[0].ip == "192.168.1.50"


def test_serialize_config():
    """Test serializing DHCP config."""
    subnets = [
        DHCPSubnet(
            id="test1",
            network="192.168.1.0",
            netmask="255.255.255.0",
            range_start="192.168.1.100",
            range_end="192.168.1.200",
            routers="192.168.1.1",
            default_lease_time=86400,
            max_lease_time=172800,
        )
    ]
    
    reservations = [
        DHCPReservation(
            id="res1",
            hostname="printer",
            mac="00:11:22:33:44:55",
            ip="192.168.1.50",
        )
    ]
    
    config = serialize_dhcpd_conf(subnets, reservations)
    
    assert "subnet 192.168.1.0 netmask 255.255.255.0" in config
    assert "range 192.168.1.100 192.168.1.200" in config
    assert "option routers 192.168.1.1" in config
    assert "host printer" in config
    assert "hardware ethernet 00:11:22:33:44:55" in config
    assert "fixed-address 192.168.1.50" in config
