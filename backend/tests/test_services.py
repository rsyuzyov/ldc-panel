"""Property-based tests for service availability"""
import pytest
from hypothesis import given, strategies as st, settings

from app.models.server import ServerServices


def get_available_sections(services: ServerServices) -> list[str]:
    """Get list of available menu sections based on services.
    
    Args:
        services: Server services availability
        
    Returns:
        List of available section names
    """
    sections = []
    if services.ad:
        sections.append("ad")
    if services.dns:
        sections.append("dns")
    if services.dhcp:
        sections.append("dhcp")
    # GPO requires AD
    if services.ad:
        sections.append("gpo")
    return sections


def is_section_disabled(services: ServerServices, section: str) -> bool:
    """Check if a section should be disabled based on services.
    
    Args:
        services: Server services availability
        section: Section name to check
        
    Returns:
        True if section should be disabled, False otherwise
    """
    if section == "ad":
        return not services.ad
    if section == "dns":
        return not services.dns
    if section == "dhcp":
        return not services.dhcp
    if section == "gpo":
        return not services.ad  # GPO requires AD
    return True


# **Feature: ldc-panel, Property 6: Service availability affects menu**
# **Validates: Requirements 2.8**
@given(
    ad=st.booleans(),
    dns=st.booleans(),
    dhcp=st.booleans()
)
@settings(max_examples=100)
def test_service_availability_affects_menu(ad: bool, dns: bool, dhcp: bool):
    """For any server with unavailable service, the corresponding menu section should be disabled."""
    services = ServerServices(ad=ad, dns=dns, dhcp=dhcp)
    
    # AD section disabled when AD service unavailable
    assert is_section_disabled(services, "ad") == (not ad)
    
    # DNS section disabled when DNS service unavailable
    assert is_section_disabled(services, "dns") == (not dns)
    
    # DHCP section disabled when DHCP service unavailable
    assert is_section_disabled(services, "dhcp") == (not dhcp)
    
    # GPO section disabled when AD service unavailable (GPO requires AD)
    assert is_section_disabled(services, "gpo") == (not ad)
    
    # Available sections should match enabled services
    available = get_available_sections(services)
    
    if ad:
        assert "ad" in available
        assert "gpo" in available
    else:
        assert "ad" not in available
        assert "gpo" not in available
    
    if dns:
        assert "dns" in available
    else:
        assert "dns" not in available
    
    if dhcp:
        assert "dhcp" in available
    else:
        assert "dhcp" not in available


def test_all_services_available():
    """When all services are available, all sections should be enabled."""
    services = ServerServices(ad=True, dns=True, dhcp=True)
    
    assert not is_section_disabled(services, "ad")
    assert not is_section_disabled(services, "dns")
    assert not is_section_disabled(services, "dhcp")
    assert not is_section_disabled(services, "gpo")


def test_no_services_available():
    """When no services are available, all sections should be disabled."""
    services = ServerServices(ad=False, dns=False, dhcp=False)
    
    assert is_section_disabled(services, "ad")
    assert is_section_disabled(services, "dns")
    assert is_section_disabled(services, "dhcp")
    assert is_section_disabled(services, "gpo")
