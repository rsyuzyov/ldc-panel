"""SSH service for remote command execution"""
from typing import Optional, Tuple
import paramiko
from pathlib import Path

from app.config import settings
from app.models.server import ServerConfig, AuthType, ServerServices


class SSHService:
    """SSH service for connecting to remote servers."""
    
    def __init__(self, server: ServerConfig):
        self.server = server
        self.client: Optional[paramiko.SSHClient] = None
    
    def connect(self) -> Tuple[bool, str]:
        """Connect to the server.
        
        Returns:
            Tuple of (success, error_message)
        """
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if self.server.auth_type == AuthType.KEY:
                key_path = settings.base_dir / self.server.key_path if self.server.key_path else None
                if not key_path or not key_path.exists():
                    return False, f"SSH ключ не найден: {self.server.key_path}"
                
                self.client.connect(
                    hostname=self.server.host,
                    port=self.server.port,
                    username=self.server.user,
                    key_filename=str(key_path),
                    timeout=10,
                )
            else:
                self.client.connect(
                    hostname=self.server.host,
                    port=self.server.port,
                    username=self.server.user,
                    password=self.server.password,
                    timeout=10,
                )
            
            return True, ""
        except paramiko.AuthenticationException:
            return False, "Ошибка аутентификации SSH: проверьте ключ или пароль"
        except paramiko.SSHException as e:
            return False, f"Ошибка SSH: {str(e)}"
        except TimeoutError:
            return False, "Превышено время ожидания подключения"
        except Exception as e:
            return False, f"Не удалось подключиться к серверу: {str(e)}"
    
    def disconnect(self) -> None:
        """Disconnect from the server."""
        if self.client:
            self.client.close()
            self.client = None
    
    def execute(self, command: str, timeout: int = 30) -> Tuple[int, str, str]:
        """Execute a command on the server.
        
        Args:
            command: Command to execute
            timeout: Command timeout in seconds
            
        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        if not self.client:
            raise RuntimeError("Not connected to server")
        
        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
            exit_code = stdout.channel.recv_exit_status()
            return exit_code, stdout.read().decode("utf-8"), stderr.read().decode("utf-8")
        except Exception as e:
            return -1, "", str(e)
    
    def check_services(self) -> ServerServices:
        """Check which services are available on the server.
        
        Returns:
            ServerServices with availability flags
        """
        services = ServerServices()
        
        if not self.client:
            return services
        
        # Check samba-ad-dc
        exit_code, _, _ = self.execute("systemctl is-active samba-ad-dc")
        services.ad = exit_code == 0
        
        # Check DNS - bind9 or samba internal DNS
        exit_code, _, _ = self.execute("systemctl is-active bind9")
        if exit_code == 0:
            services.dns = True
        else:
            # Samba AD DC includes internal DNS by default
            # If AD is running, DNS is available (Samba internal DNS)
            services.dns = services.ad
            print(f"[DEBUG] DNS check: dns={services.dns} (based on AD status)")
        
        # Check isc-dhcp-server
        exit_code, _, _ = self.execute("systemctl is-active isc-dhcp-server")
        services.dhcp = exit_code == 0
        
        print(f"[DEBUG] Services: ad={services.ad}, dns={services.dns}, dhcp={services.dhcp}")
        
        return services
    
    def detect_domain(self) -> Tuple[Optional[str], Optional[str]]:
        """Detect domain and base_dn from Samba AD.
        
        Returns:
            Tuple of (domain, base_dn) or (None, None) if not detected
        """
        if not self.client:
            return None, None
        
        # Get realm from samba config
        exit_code, stdout, _ = self.execute("grep -i '^\\s*realm' /etc/samba/smb.conf | head -1 | cut -d'=' -f2 | tr -d ' '")
        if exit_code == 0 and stdout.strip():
            realm = stdout.strip().upper()
            domain = realm.lower()
            # Convert domain to base_dn: domain.local -> DC=domain,DC=local
            parts = domain.split('.')
            base_dn = ','.join(f'DC={p}' for p in parts)
            return domain, base_dn
        
        # Fallback: try ldbsearch for defaultNamingContext
        exit_code, stdout, _ = self.execute('ldbsearch -H /var/lib/samba/private/sam.ldb -b "" -s base defaultNamingContext 2>/dev/null | grep defaultNamingContext | cut -d: -f2 | tr -d " "')
        if exit_code == 0 and stdout.strip():
            base_dn = stdout.strip()
            # Extract domain from base_dn: DC=domain,DC=local -> domain.local
            parts = [p.split('=')[1] for p in base_dn.split(',') if p.startswith('DC=')]
            domain = '.'.join(parts).lower()
            return domain, base_dn
        
        return None, None
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


def test_connection(server: ServerConfig) -> Tuple[bool, str, ServerServices]:
    """Test SSH connection and check services.
    
    Args:
        server: Server configuration
        
    Returns:
        Tuple of (success, error_message, services)
    """
    ssh = SSHService(server)
    success, error = ssh.connect()
    
    if not success:
        return False, error, ServerServices()
    
    try:
        services = ssh.check_services()
        
        # Auto-detect domain and base_dn from Samba if AD is available
        if services.ad and not server.base_dn:
            domain, base_dn = ssh.detect_domain()
            if domain:
                server.domain = domain
            if base_dn:
                server.base_dn = base_dn
        
        return True, "", services
    finally:
        ssh.disconnect()
