"""JWT session management"""
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt

from app.config import settings

# Set of invalidated tokens (in production, use Redis or database)
_invalidated_tokens: set[str] = set()

SESSION_TTL_SECONDS = settings.jwt_ttl_hours * 3600  # 8 hours = 28800 seconds


def create_session(username: str) -> tuple[str, int]:
    """Create a new JWT session token.
    
    Args:
        username: Username to create session for
        
    Returns:
        Tuple of (token, ttl_seconds)
    """
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=SESSION_TTL_SECONDS)
    
    payload = {
        "sub": username,
        "iat": now,
        "exp": exp,
    }
    
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, SESSION_TTL_SECONDS


def validate_session(token: str) -> Optional[str]:
    """Validate a JWT session token.
    
    Args:
        token: JWT token to validate
        
    Returns:
        Username if valid, None otherwise
    """
    if token in _invalidated_tokens:
        return None
    
    try:
        payload = jwt.decode(
            token, 
            settings.jwt_secret, 
            algorithms=[settings.jwt_algorithm]
        )
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def invalidate_session(token: str) -> None:
    """Invalidate a JWT session token (logout).
    
    Args:
        token: JWT token to invalidate
    """
    _invalidated_tokens.add(token)


def get_session_ttl() -> int:
    """Get session TTL in seconds.
    
    Returns:
        TTL in seconds (28800 for 8 hours)
    """
    return SESSION_TTL_SECONDS


def is_session_valid(token: str) -> bool:
    """Check if session token is valid.
    
    Args:
        token: JWT token to check
        
    Returns:
        True if valid, False otherwise
    """
    return validate_session(token) is not None


def clear_invalidated_tokens() -> None:
    """Clear all invalidated tokens (for testing)."""
    _invalidated_tokens.clear()
