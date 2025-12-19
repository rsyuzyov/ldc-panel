"""Property-based tests for authentication"""
import pytest
from hypothesis import given, strategies as st, settings

from app.auth.pam import is_root_user, authenticate_root


# **Feature: ldc-panel, Property 2: Non-root rejection**
# **Validates: Requirements 1.4**
@given(username=st.text(min_size=1).filter(lambda x: x != "root"))
@settings(max_examples=100)
def test_non_root_rejection(username: str):
    """For any user that is not root, authentication should be rejected."""
    # is_root_user should return False for non-root users
    assert is_root_user(username) is False
    
    # authenticate_root should reject non-root users regardless of password
    success, error = authenticate_root(username, "any_password")
    assert success is False
    assert error == "Доступ разрешён только для root"


def test_root_user_is_recognized():
    """Root user should be recognized as root."""
    assert is_root_user("root") is True
