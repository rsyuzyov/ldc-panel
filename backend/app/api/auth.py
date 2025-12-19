"""Authentication API endpoints"""
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional

from app.auth.pam import authenticate_root
from app.auth.session import create_session, validate_session, invalidate_session

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    ttl: int
    username: str


class UserResponse(BaseModel):
    username: str


def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    """Dependency to get current authenticated user."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    
    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Неверный формат токена")
    
    token = parts[1]
    username = validate_session(token)
    
    if not username:
        raise HTTPException(status_code=401, detail="Недействительный или истёкший токен")
    
    return username


def get_token(authorization: Optional[str] = Header(None)) -> str:
    """Dependency to get current token."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Неверный формат токена")
    
    return parts[1]


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authenticate user and create session."""
    success, error = authenticate_root(request.username, request.password)
    
    if not success:
        # Log failed attempt would go here
        raise HTTPException(status_code=401, detail=error)
    
    token, ttl = create_session(request.username)
    
    return LoginResponse(token=token, ttl=ttl, username=request.username)


@router.post("/logout")
async def logout(token: str = Depends(get_token)):
    """Logout and invalidate session."""
    invalidate_session(token)
    return {"message": "Сессия завершена"}


@router.get("/me", response_model=UserResponse)
async def get_me(username: str = Depends(get_current_user)):
    """Get current authenticated user."""
    return UserResponse(username=username)
