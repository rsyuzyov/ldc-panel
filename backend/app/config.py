"""Application configuration"""
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    app_name: str = "LDC Panel"
    debug: bool = False
    
    # JWT settings
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_ttl_hours: int = 8
    
    # Paths
    base_dir: Path = Path(__file__).parent.parent
    project_root: Path = base_dir.parent
    logs_dir: Path = project_root / "logs"
    keys_dir: Path = base_dir / "keys"
    servers_file: Path = base_dir / "servers.yaml"
    log_file: Path = logs_dir / "backend.log"
    backups_dir: Path = Path("/backups")
    
    class Config:
        env_prefix = "LDC_"


settings = Settings()

# Ensure directories exist
settings.keys_dir.mkdir(parents=True, exist_ok=True)
settings.logs_dir.mkdir(parents=True, exist_ok=True)
