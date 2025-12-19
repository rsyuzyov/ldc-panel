"""SSH key management service"""
import os
import stat
from pathlib import Path
from typing import Tuple

from app.config import settings


def save_ssh_key(server_id: str, key_content: bytes) -> Tuple[str, str]:
    """Save SSH key to keys directory with proper permissions.
    
    Args:
        server_id: Server ID for naming the key file
        key_content: SSH key content as bytes
        
    Returns:
        Tuple of (relative_path, error_message)
    """
    try:
        # Ensure keys directory exists
        settings.keys_dir.mkdir(parents=True, exist_ok=True)
        
        # Create key file path
        key_filename = f"{server_id}.pem"
        key_path = settings.keys_dir / key_filename
        relative_path = f"keys/{key_filename}"
        
        # Write key content
        with open(key_path, "wb") as f:
            f.write(key_content)
        
        # Set permissions to 600 (owner read/write only)
        os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)
        
        return relative_path, ""
    except Exception as e:
        return "", f"Ошибка сохранения ключа: {str(e)}"


def delete_ssh_key(server_id: str) -> bool:
    """Delete SSH key for a server.
    
    Args:
        server_id: Server ID
        
    Returns:
        True if deleted, False otherwise
    """
    key_path = settings.keys_dir / f"{server_id}.pem"
    
    if key_path.exists():
        key_path.unlink()
        return True
    
    return False


def get_key_permissions(server_id: str) -> int:
    """Get SSH key file permissions.
    
    Args:
        server_id: Server ID
        
    Returns:
        File permissions as octal integer (e.g., 0o600)
    """
    key_path = settings.keys_dir / f"{server_id}.pem"
    
    if not key_path.exists():
        return 0
    
    return stat.S_IMODE(os.stat(key_path).st_mode)


def key_exists(server_id: str) -> bool:
    """Check if SSH key exists for a server.
    
    Args:
        server_id: Server ID
        
    Returns:
        True if key exists, False otherwise
    """
    key_path = settings.keys_dir / f"{server_id}.pem"
    return key_path.exists()
