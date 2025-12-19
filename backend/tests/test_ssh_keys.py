"""Property-based tests for SSH key management"""
import pytest
import tempfile
import os
import stat
from pathlib import Path
from hypothesis import given, strategies as st, settings
from unittest.mock import patch

from app.services.ssh_keys import save_ssh_key, delete_ssh_key, get_key_permissions, key_exists


# **Feature: ldc-panel, Property 4: SSH key permissions**
# **Validates: Requirements 2.3**
@given(
    server_id=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-_')),
    key_content=st.binary(min_size=100, max_size=5000)
)
@settings(max_examples=100)
def test_ssh_key_permissions(server_id: str, key_content: bytes):
    """For any uploaded SSH key, the file should have permissions 600 (owner read/write only)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_keys_dir = Path(temp_dir) / "keys"
        
        # Mock settings.keys_dir
        with patch('app.services.ssh_keys.settings') as mock_settings:
            mock_settings.keys_dir = temp_keys_dir
            
            # Save key
            relative_path, error = save_ssh_key(server_id, key_content)
            
            # Should succeed
            assert error == ""
            assert relative_path == f"keys/{server_id}.pem"
            
            # Check file exists
            key_path = temp_keys_dir / f"{server_id}.pem"
            assert key_path.exists()
            
            # Check permissions are 600 (0o600 = 384 in decimal)
            permissions = stat.S_IMODE(os.stat(key_path).st_mode)
            assert permissions == 0o600, f"Expected 0o600, got {oct(permissions)}"
            
            # Verify only owner can read/write
            assert permissions & stat.S_IRUSR  # Owner can read
            assert permissions & stat.S_IWUSR  # Owner can write
            assert not (permissions & stat.S_IRGRP)  # Group cannot read
            assert not (permissions & stat.S_IWGRP)  # Group cannot write
            assert not (permissions & stat.S_IROTH)  # Others cannot read
            assert not (permissions & stat.S_IWOTH)  # Others cannot write


def test_ssh_key_save_and_delete():
    """Test basic save and delete operations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_keys_dir = Path(temp_dir) / "keys"
        
        with patch('app.services.ssh_keys.settings') as mock_settings:
            mock_settings.keys_dir = temp_keys_dir
            
            # Save key
            key_content = b"-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----"
            relative_path, error = save_ssh_key("test-server", key_content)
            
            assert error == ""
            assert key_exists("test-server") is True
            
            # Delete key
            result = delete_ssh_key("test-server")
            assert result is True
            assert key_exists("test-server") is False


def test_get_key_permissions_nonexistent():
    """Test getting permissions for non-existent key."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_keys_dir = Path(temp_dir) / "keys"
        temp_keys_dir.mkdir()
        
        with patch('app.services.ssh_keys.settings') as mock_settings:
            mock_settings.keys_dir = temp_keys_dir
            
            permissions = get_key_permissions("nonexistent")
            assert permissions == 0
