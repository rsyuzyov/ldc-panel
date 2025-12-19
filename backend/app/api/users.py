"""AD Users API endpoints"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List

from app.api.auth import get_current_user
from app.models.ad import ADUser, ADUserCreate, ADUserUpdate
from app.services.server_store import server_store
from app.services.ssh import SSHService
from app.services.ad import ADService

router = APIRouter(prefix="/api/ad/users", tags=["ad-users"])


class UserResponse(BaseModel):
    dn: str
    sAMAccountName: str
    cn: str
    sn: Optional[str] = None
    givenName: Optional[str] = None
    mail: Optional[str] = None
    userPrincipalName: Optional[str] = None
    memberOf: List[str] = []
    enabled: bool


class PasswordChangeRequest(BaseModel):
    password: str


def get_ad_service(server_id: str) -> ADService:
    """Get AD service for a server."""
    server = server_store.get_by_id(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Сервер не найден")
    
    if not server.services.ad:
        raise HTTPException(status_code=400, detail="AD сервис недоступен на этом сервере")
    
    ssh = SSHService(server)
    success, error = ssh.connect()
    if not success:
        raise HTTPException(status_code=500, detail=f"Ошибка подключения: {error}")
    
    return ADService(server, ssh)


@router.get("", response_model=List[UserResponse])
async def get_users(
    server_id: str = Query(..., description="ID сервера"),
    search: Optional[str] = Query(None, description="Поисковый запрос"),
    username: str = Depends(get_current_user),
):
    """Get list of AD users."""
    ad_service = get_ad_service(server_id)
    
    try:
        users, error = ad_service.search_users(search)
        if error:
            raise HTTPException(status_code=500, detail=error)
        
        return [
            UserResponse(
                dn=u.dn,
                sAMAccountName=u.sAMAccountName,
                cn=u.cn,
                sn=u.sn,
                givenName=u.givenName,
                mail=u.mail,
                userPrincipalName=u.userPrincipalName,
                memberOf=u.memberOf,
                enabled=u.enabled,
            )
            for u in users
        ]
    finally:
        ad_service.ssh.disconnect()


@router.post("", response_model=dict)
async def create_user(
    server_id: str = Query(..., description="ID сервера"),
    user: ADUserCreate = ...,
    username: str = Depends(get_current_user),
):
    """Create a new AD user."""
    ad_service = get_ad_service(server_id)
    
    try:
        success, error = ad_service.add_user(
            sam_account_name=user.sAMAccountName,
            cn=user.cn,
            password=user.password,
            ou=user.ou,
            sn=user.sn,
            given_name=user.givenName,
            mail=user.mail,
        )
        
        if not success:
            raise HTTPException(status_code=500, detail=error)
        
        return {"message": "Пользователь создан", "sAMAccountName": user.sAMAccountName}
    finally:
        ad_service.ssh.disconnect()


@router.patch("/{dn:path}")
async def update_user(
    dn: str,
    server_id: str = Query(..., description="ID сервера"),
    user: ADUserUpdate = ...,
    username: str = Depends(get_current_user),
):
    """Update an AD user."""
    ad_service = get_ad_service(server_id)
    
    try:
        success, error = ad_service.modify_user(
            dn=dn,
            cn=user.cn,
            sn=user.sn,
            given_name=user.givenName,
            mail=user.mail,
            user_account_control=user.userAccountControl,
        )
        
        if not success:
            raise HTTPException(status_code=500, detail=error)
        
        return {"message": "Пользователь обновлён"}
    finally:
        ad_service.ssh.disconnect()


@router.delete("/{dn:path}")
async def delete_user(
    dn: str,
    server_id: str = Query(..., description="ID сервера"),
    username: str = Depends(get_current_user),
):
    """Delete an AD user."""
    ad_service = get_ad_service(server_id)
    
    try:
        success, error = ad_service.delete_user(dn)
        
        if not success:
            raise HTTPException(status_code=500, detail=error)
        
        return {"message": "Пользователь удалён"}
    finally:
        ad_service.ssh.disconnect()


@router.post("/{dn:path}/password")
async def change_user_password(
    dn: str,
    server_id: str = Query(..., description="ID сервера"),
    request: PasswordChangeRequest = ...,
    username: str = Depends(get_current_user),
):
    """Change AD user password."""
    ad_service = get_ad_service(server_id)
    
    try:
        success, error = ad_service.change_password(dn, request.password)
        
        if not success:
            raise HTTPException(status_code=500, detail=error)
        
        return {"message": "Пароль изменён"}
    finally:
        ad_service.ssh.disconnect()
