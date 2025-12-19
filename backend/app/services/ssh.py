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
        
        # Check bind9 (DNS)
        exit_code, _, _ = self.execute("systemctl is-active bind9")
        services.dns = exit_code == 0
        
        # Check isc-dhcp-server
        exit_code, _, _ = self.execute("systemctl is-active isc-dhcp-server")
        services.dhcp = exit_code == 0
        
        return services
    
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
        return True, "", services
    finally:
        ssh.disconnect()
