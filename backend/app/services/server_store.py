"""Server configuration YAML storage"""
from pathlib import Path
from typing import Optional
import yaml

from app.config import settings
from app.models.server import ServerConfig, ServerServices, AuthType


class ServerStore:
    """YAML-based server configuration storage."""
    
    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path or settings.servers_file
    
    def _load_yaml(self) -> dict:
        """Load YAML file."""
        if not self.file_path.exists():
            return {"servers": []}
        
        with open(self.file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data if data else {"servers": []}
    
    def _save_yaml(self, data: dict) -> None:
        """Save data to YAML file."""
        with open(self.file_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
    
    def _dict_to_server(self, data: dict) -> ServerConfig:
        """Convert dictionary to ServerConfig."""
        services_data = data.get("services", {})
        services = ServerServices(
            ad=services_data.get("ad", False),
            dns=services_data.get("dns", False),
            dhcp=services_data.get("dhcp", False),
        )
        
        return ServerConfig(
            id=data["id"],
            name=data["name"],
            host=data["host"],
            port=data.get("port", 22),
            user=data.get("user", "root"),
            auth_type=AuthType(data.get("auth_type", "key")),
            key_path=data.get("key_path"),
            password=data.get("password"),
            services=services,
            domain=data.get("domain"),
            base_dn=data.get("base_dn"),
        )
    
    def _server_to_dict(self, server: ServerConfig) -> dict:
        """Convert ServerConfig to dictionary."""
        data = {
            "id": server.id,
            "name": server.name,
            "host": server.host,
            "port": server.port,
            "user": server.user,
            "auth_type": server.auth_type.value,
            "services": {
                "ad": server.services.ad,
                "dns": server.services.dns,
                "dhcp": server.services.dhcp,
            },
        }
        
        if server.key_path:
            data["key_path"] = server.key_path
        if server.password:
            data["password"] = server.password
        if server.domain:
            data["domain"] = server.domain
        if server.base_dn:
            data["base_dn"] = server.base_dn
        
        return data
    
    def get_all(self) -> list[ServerConfig]:
        """Get all servers."""
        data = self._load_yaml()
        return [self._dict_to_server(s) for s in data.get("servers", [])]
    
    def get_by_id(self, server_id: str) -> Optional[ServerConfig]:
        """Get server by ID."""
        servers = self.get_all()
        for server in servers:
            if server.id == server_id:
                return server
        return None
    
    def add(self, server: ServerConfig) -> ServerConfig:
        """Add a new server."""
        data = self._load_yaml()
        servers = data.get("servers", [])
        servers.append(self._server_to_dict(server))
        data["servers"] = servers
        self._save_yaml(data)
        return server
    
    def update(self, server: ServerConfig) -> Optional[ServerConfig]:
        """Update an existing server."""
        data = self._load_yaml()
        servers = data.get("servers", [])
        
        for i, s in enumerate(servers):
            if s["id"] == server.id:
                servers[i] = self._server_to_dict(server)
                data["servers"] = servers
                self._save_yaml(data)
                return server
        
        return None
    
    def delete(self, server_id: str) -> bool:
        """Delete a server by ID."""
        data = self._load_yaml()
        servers = data.get("servers", [])
        
        original_len = len(servers)
        servers = [s for s in servers if s["id"] != server_id]
        
        if len(servers) < original_len:
            data["servers"] = servers
            self._save_yaml(data)
            return True
        
        return False
    
    def exists(self, server_id: str) -> bool:
        """Check if server exists."""
        return self.get_by_id(server_id) is not None


# Global instance
server_store = ServerStore()
