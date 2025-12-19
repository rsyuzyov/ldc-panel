"""Server management API endpoints"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional

from app.api.auth import get_current_user
from app.models.server import ServerConfig, ServerCreate, ServerResponse, ServerStatus, ServerServices, AuthType
from app.services.server_store import server_store
from app.services.ssh import test_connection
from app.services.ssh_keys import save_ssh_key, delete_ssh_key

router = APIRouter(prefix="/api/servers", tags=["servers"])


class ServerCreateRequest(BaseModel):
    id: str
    name: str
    host: str
    port: int = 22
    user: str = "root"
    auth_type: str = "key"
    password: Optional[str] = None
    domain: Optional[str] = None
    base_dn: Optional[str] = None


class TestConnectionResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    services: ServerServices


@router.get("", response_model=list[ServerResponse])
async def get_servers(username: str = Depends(get_current_user)):
    """Get all servers."""
    servers = server_store.get_all()
    return [
        ServerResponse(
            id=s.id,
            name=s.name,
            host=s.host,
            port=s.port,
            user=s.user,
            auth_type=s.auth_type,
            services=s.services,
            domain=s.domain,
            base_dn=s.base_dn,
        )
        for s in servers
    ]


@router.post("", response_model=ServerResponse)
async def create_server(
    id: str = Form(...),
    name: str = Form(...),
    host: str = Form(...),
    port: int = Form(22),
    user: str = Form("root"),
    auth_type: str = Form("key"),
    password: Optional[str] = Form(None),
    domain: Optional[str] = Form(None),
    base_dn: Optional[str] = Form(None),
    key_file: Optional[UploadFile] = File(None),
    username: str = Depends(get_current_user),
):
    """Create a new server."""
    if server_store.exists(id):
        raise HTTPException(status_code=400, detail="Сервер с таким ID уже существует")
    
    key_path = None
    if auth_type == "key" and key_file:
        key_content = await key_file.read()
        key_path, error = save_ssh_key(id, key_content)
        if error:
            raise HTTPException(status_code=400, detail=error)
    
    server = ServerConfig(
        id=id,
        name=name,
        host=host,
        port=port,
        user=user,
        auth_type=AuthType(auth_type),
        key_path=key_path,
        password=password if auth_type == "password" else None,
        services=ServerServices(),
        domain=domain,
        base_dn=base_dn,
    )
    
    server_store.add(server)
    
    return ServerResponse(
        id=server.id,
        name=server.name,
        host=server.host,
        port=server.port,
        user=server.user,
        auth_type=server.auth_type,
        services=server.services,
        domain=server.domain,
        base_dn=server.base_dn,
    )


@router.put("/{server_id}", response_model=ServerResponse)
async def update_server(
    server_id: str,
    name: str = Form(...),
    host: str = Form(...),
    port: int = Form(22),
    user: str = Form("root"),
    auth_type: str = Form("key"),
    password: Optional[str] = Form(None),
    key_file: Optional[UploadFile] = File(None),
    username: str = Depends(get_current_user),
):
    """Update an existing server."""
    server = server_store.get_by_id(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Сервер не найден")
    
    # Update key if provided
    key_path = server.key_path
    if auth_type == "key" and key_file:
        key_content = await key_file.read()
        key_path, error = save_ssh_key(server_id, key_content)
        if error:
            raise HTTPException(status_code=400, detail=error)
    
    # Update server fields
    server.name = name
    server.host = host
    server.port = port
    server.user = user
    server.auth_type = AuthType(auth_type)
    server.key_path = key_path if auth_type == "key" else None
    server.password = password if auth_type == "password" else None
    
    server_store.update(server)
    
    return ServerResponse(
        id=server.id,
        name=server.name,
        host=server.host,
        port=server.port,
        user=server.user,
        auth_type=server.auth_type,
        services=server.services,
        domain=server.domain,
        base_dn=server.base_dn,
    )


@router.delete("/{server_id}")
async def delete_server(server_id: str, username: str = Depends(get_current_user)):
    """Delete a server."""
    if not server_store.exists(server_id):
        raise HTTPException(status_code=404, detail="Сервер не найден")
    
    # Delete SSH key if exists
    delete_ssh_key(server_id)
    
    # Delete server from store
    server_store.delete(server_id)
    
    return {"message": "Сервер удалён"}


@router.post("/{server_id}/test", response_model=TestConnectionResponse)
async def test_server_connection(server_id: str, username: str = Depends(get_current_user)):
    """Test SSH connection to server and check services."""
    server = server_store.get_by_id(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Сервер не найден")
    
    success, error, services = test_connection(server)
    
    if success:
        # Update server services in store
        server.services = services
        server_store.update(server)
    
    return TestConnectionResponse(success=success, error=error if error else None, services=services)


@router.post("/{server_id}/select")
async def select_server(server_id: str, username: str = Depends(get_current_user)):
    """Select a server as current."""
    server = server_store.get_by_id(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Сервер не найден")
    
    return ServerResponse(
        id=server.id,
        name=server.name,
        host=server.host,
        port=server.port,
        user=server.user,
        auth_type=server.auth_type,
        services=server.services,
        domain=server.domain,
        base_dn=server.base_dn,
    )
