"""PAM authentication for local root user"""
import os
import sys

# PAM доступен только на Linux
if sys.platform != "win32":
    import pam
else:
    pam = None  # type: ignore


def authenticate_pam(username: str, password: str) -> bool:
    """Authenticate user via PAM.
    
    Args:
        username: Username to authenticate
        password: Password to verify
        
    Returns:
        True if authentication successful, False otherwise
    """
    # Windows: режим разработки с тестовыми учётными данными
    if sys.platform == "win32" or os.environ.get("LDC_DEV_AUTH"):
        dev_password = os.environ.get("LDC_DEV_PASSWORD", "admin")
        return username == "root" and password == dev_password
    
    p = pam.pam()
    return p.authenticate(username, password)


def is_root_user(username: str) -> bool:
    """Check if user is root.
    
    Args:
        username: Username to check
        
    Returns:
        True if user is root, False otherwise
    """
    return username == "root"


def authenticate_root(username: str, password: str) -> tuple[bool, str]:
    """Authenticate root user via PAM.
    
    Args:
        username: Username (must be root)
        password: Password to verify
        
    Returns:
        Tuple of (success, error_message)
    """
    if not is_root_user(username):
        return False, "Доступ разрешён только для root"
    
    if not authenticate_pam(username, password):
        return False, "Неверные учётные данные"
    
    return True, ""
