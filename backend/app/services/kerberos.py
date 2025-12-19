"""Kerberos authentication helpers for samba-tool commands"""
from typing import Tuple
from app.services.ssh import SSHService

KEYTAB_PATH = "/etc/krb5.keytab"


def ensure_kerberos_ticket(ssh: SSHService, principal: str) -> Tuple[bool, str]:
    """Ensure valid Kerberos ticket exists, create if needed.
    
    Args:
        ssh: SSH service instance
        principal: Kerberos principal (AD user, e.g. root)
        
    Returns:
        Tuple of (success, error_message)
    """
    # Check if ticket exists and is valid
    exit_code, stdout, _ = ssh.execute("klist -s 2>/dev/null && echo 'VALID' || echo 'INVALID'")
    
    if "VALID" in stdout:
        return True, ""
    
    # No valid ticket - need to get one via keytab
    # First check if keytab exists
    exit_code, _, _ = ssh.execute(f"test -f {KEYTAB_PATH}")
    
    if exit_code != 0:
        # Create keytab
        success, error = create_keytab(ssh, principal)
        if not success:
            return False, error
    
    # Get ticket using keytab
    exit_code, stdout, stderr = ssh.execute(f"kinit -k -t {KEYTAB_PATH} {principal}")
    
    if exit_code != 0:
        return False, f"kinit failed: {stderr}"
    
    return True, ""


def create_keytab(ssh: SSHService, principal: str) -> Tuple[bool, str]:
    """Create Kerberos keytab file.
    
    Args:
        ssh: SSH service instance
        principal: Kerberos principal (AD user)
        
    Returns:
        Tuple of (success, error_message)
    """
    # Export keytab for the principal
    exit_code, stdout, stderr = ssh.execute(
        f"samba-tool domain exportkeytab {KEYTAB_PATH} --principal={principal} 2>&1"
    )
    
    if exit_code != 0:
        return False, f"Failed to create keytab: {stderr or stdout}"
    
    # Set permissions
    ssh.execute(f"chmod 600 {KEYTAB_PATH}")
    
    return True, ""
