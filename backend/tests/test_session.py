"""Property-based tests for session management"""
import pytest
from hypothesis import given, strategies as st, settings

from app.auth.session import (
    create_session, 
    validate_session, 
    invalidate_session, 
    get_session_ttl,
    is_session_valid,
    clear_invalidated_tokens,
    SESSION_TTL_SECONDS
)


# **Feature: ldc-panel, Property 1: Session TTL correctness**
# **Validates: Requirements 1.2**
@given(username=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()))
@settings(max_examples=100)
def test_session_ttl_correctness(username: str):
    """For any successful authentication, session TTL should be exactly 8 hours (28800 seconds)."""
    token, ttl = create_session(username)
    
    # TTL should be exactly 28800 seconds (8 hours)
    assert ttl == 28800
    assert ttl == SESSION_TTL_SECONDS
    assert get_session_ttl() == 28800


# **Feature: ldc-panel, Property 3: Logout invalidates session**
# **Validates: Requirements 1.5**
@given(username=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()))
@settings(max_examples=100)
def test_logout_invalidates_session(username: str):
    """For any active session, after logout the token should be invalid."""
    clear_invalidated_tokens()  # Clean state for test
    
    # Create a session
    token, _ = create_session(username)
    
    # Session should be valid initially
    assert is_session_valid(token) is True
    assert validate_session(token) == username
    
    # Invalidate (logout)
    invalidate_session(token)
    
    # Session should be invalid after logout
    assert is_session_valid(token) is False
    assert validate_session(token) is None


def test_session_creation_returns_valid_token():
    """Created session should be immediately valid."""
    clear_invalidated_tokens()
    token, ttl = create_session("root")
    
    assert token is not None
    assert len(token) > 0
    assert ttl == 28800
    assert validate_session(token) == "root"
