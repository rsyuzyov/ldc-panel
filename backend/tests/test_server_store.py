"""Property-based tests for server storage"""
import pytest
import tempfile
from pathlib import Path
from hypothesis import given, strategies as st, settings

from app.models.server import ServerConfig, ServerServices, AuthType
from app.services.server_store import ServerStore


# Strategy for generating valid server configs
@st.composite
def server_configs(draw):
    """Generate valid ServerConfig objects."""
    server_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-_')))
    name = draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip()))
    host = draw(st.from_regex(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', fullmatch=True))
    port = draw(st.integers(min_value=1, max_value=65535))
    user = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))))
    auth_type = draw(st.sampled_from([AuthType.KEY, AuthType.PASSWORD]))
    
    services = ServerServices(
        ad=draw(st.booleans()),
        dns=draw(st.booleans()),
        dhcp=draw(st.booleans()),
    )
    
    domain = draw(st.one_of(st.none(), st.text(min_size=1, max_size=50).filter(lambda x: x.strip())))
    base_dn = draw(st.one_of(st.none(), st.text(min_size=1, max_size=100).filter(lambda x: x.strip())))
    
    return ServerConfig(
        id=server_id,
        name=name,
        host=host,
        port=port,
        user=user,
        auth_type=auth_type,
        key_path=f"keys/{server_id}.pem" if auth_type == AuthType.KEY else None,
        password="secret" if auth_type == AuthType.PASSWORD else None,
        services=services,
        domain=domain,
        base_dn=base_dn,
    )


# **Feature: ldc-panel, Property 5: Server config round-trip**
# **Validates: Requirements 2.5, 11.1, 11.2**
@given(server_config=server_configs())
@settings(max_examples=100)
def test_server_config_roundtrip(server_config: ServerConfig):
    """For any server configuration, saving to YAML and loading should return equivalent object."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        temp_path = Path(f.name)
    
    try:
        store = ServerStore(temp_path)
        
        # Save server
        store.add(server_config)
        
        # Load server
        loaded = store.get_by_id(server_config.id)
        
        # Should be equivalent
        assert loaded is not None
        assert loaded.id == server_config.id
        assert loaded.name == server_config.name
        assert loaded.host == server_config.host
        assert loaded.port == server_config.port
        assert loaded.user == server_config.user
        assert loaded.auth_type == server_config.auth_type
        assert loaded.services.ad == server_config.services.ad
        assert loaded.services.dns == server_config.services.dns
        assert loaded.services.dhcp == server_config.services.dhcp
        assert loaded.domain == server_config.domain
        assert loaded.base_dn == server_config.base_dn
    finally:
        temp_path.unlink(missing_ok=True)


# **Feature: ldc-panel, Property 15: Server deletion removes from config**
# **Validates: Requirements 11.3**
@given(server_config=server_configs())
@settings(max_examples=100)
def test_server_deletion_removes_from_config(server_config: ServerConfig):
    """For any deleted server, it should not be present in servers.yaml after saving."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        temp_path = Path(f.name)
    
    try:
        store = ServerStore(temp_path)
        
        # Add server
        store.add(server_config)
        assert store.exists(server_config.id) is True
        
        # Delete server
        result = store.delete(server_config.id)
        assert result is True
        
        # Server should not exist
        assert store.exists(server_config.id) is False
        assert store.get_by_id(server_config.id) is None
        
        # Verify by reloading
        store2 = ServerStore(temp_path)
        assert store2.exists(server_config.id) is False
    finally:
        temp_path.unlink(missing_ok=True)


def test_server_store_basic_operations():
    """Test basic CRUD operations."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        temp_path = Path(f.name)
    
    try:
        store = ServerStore(temp_path)
        
        server = ServerConfig(
            id="test-dc1",
            name="DC1.test.local",
            host="192.168.1.10",
            port=22,
            user="root",
            auth_type=AuthType.KEY,
            key_path="keys/dc1.pem",
            services=ServerServices(ad=True, dns=True, dhcp=False),
            domain="test.local",
            base_dn="DC=test,DC=local",
        )
        
        # Add
        store.add(server)
        assert store.exists("test-dc1")
        
        # Get
        loaded = store.get_by_id("test-dc1")
        assert loaded is not None
        assert loaded.name == "DC1.test.local"
        
        # Update
        server.name = "DC1-Updated.test.local"
        store.update(server)
        loaded = store.get_by_id("test-dc1")
        assert loaded.name == "DC1-Updated.test.local"
        
        # Delete
        store.delete("test-dc1")
        assert not store.exists("test-dc1")
    finally:
        temp_path.unlink(missing_ok=True)
