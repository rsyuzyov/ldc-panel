"""SSH connection pool for reusing connections."""
from typing import Dict, Optional, Tuple
import time
import threading

from app.services.ssh import SSHService
from app.models.server import ServerConfig


class SSHPool:
    """Пул SSH соединений с TTL."""
    
    def __init__(self, ttl: int = 300):  # 5 минут по умолчанию
        self._connections: Dict[str, Tuple[SSHService, float]] = {}
        self._lock = threading.Lock()
        self.ttl = ttl
    
    def _make_key(self, server: ServerConfig) -> str:
        return f"{server.host}:{server.port}:{server.user}"
    
    def _is_alive(self, ssh: SSHService) -> bool:
        """Проверить, что соединение живое."""
        try:
            if not ssh.client:
                return False
            transport = ssh.client.get_transport()
            return transport is not None and transport.is_active()
        except:
            return False
    
    def get(self, server: ServerConfig) -> SSHService:
        """Получить соединение из пула или создать новое."""
        key = self._make_key(server)
        now = time.time()
        
        with self._lock:
            if key in self._connections:
                ssh, created = self._connections[key]
                if now - created < self.ttl and self._is_alive(ssh):
                    return ssh
                # Соединение устарело или разорвано
                try:
                    ssh.disconnect()
                except:
                    pass
                del self._connections[key]
            
            # Новое соединение
            ssh = SSHService(server)
            success, error = ssh.connect()
            if not success:
                raise ConnectionError(error)
            
            self._connections[key] = (ssh, now)
            return ssh
    
    def release(self, server: ServerConfig) -> None:
        """Вернуть соединение в пул (ничего не делаем, оставляем открытым)."""
        pass
    
    def close(self, server: ServerConfig) -> None:
        """Принудительно закрыть соединение."""
        key = self._make_key(server)
        with self._lock:
            if key in self._connections:
                ssh, _ = self._connections[key]
                try:
                    ssh.disconnect()
                except:
                    pass
                del self._connections[key]
    
    def close_all(self) -> None:
        """Закрыть все соединения."""
        with self._lock:
            for ssh, _ in self._connections.values():
                try:
                    ssh.disconnect()
                except:
                    pass
            self._connections.clear()
    
    def cleanup_expired(self) -> int:
        """Удалить устаревшие соединения. Возвращает количество закрытых."""
        now = time.time()
        closed = 0
        with self._lock:
            expired_keys = [
                key for key, (ssh, created) in self._connections.items()
                if now - created >= self.ttl or not self._is_alive(ssh)
            ]
            for key in expired_keys:
                ssh, _ = self._connections[key]
                try:
                    ssh.disconnect()
                except:
                    pass
                del self._connections[key]
                closed += 1
        return closed


# Глобальный пул
ssh_pool = SSHPool()
