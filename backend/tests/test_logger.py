"""Property-based tests for operation logging"""
import pytest
import tempfile
from pathlib import Path
from hypothesis import given, strategies as st, settings
from unittest.mock import patch

from app.logger import OperationLogger


# **Feature: ldc-panel, Property 11: Operation logging**
# **Validates: Requirements 3.7, 10.1**
@given(
    operator=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))),
    action=st.sampled_from(["CREATE", "UPDATE", "DELETE", "LOGIN", "LOGOUT"]),
    obj=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() and '|' not in x),
    details=st.text(min_size=0, max_size=100).filter(lambda x: '|' not in x),
)
@settings(max_examples=100)
def test_operation_logging(operator: str, action: str, obj: str, details: str):
    """For any CRUD operation, a log entry should be created with timestamp, operator, and details."""
    with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
        temp_path = Path(f.name)
    
    try:
        logger = OperationLogger(temp_path)
        
        # Log operation
        logger.log_operation(
            operator=operator,
            action=action,
            obj=obj,
            details=details if details else None,
        )
        
        # Read log file
        with open(temp_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Should contain timestamp (ISO format pattern)
        assert content.strip()  # Not empty
        
        # Should contain operator
        assert operator in content
        
        # Should contain action
        assert action in content
        
        # Should contain object
        assert obj in content
        
        # Get logs via API
        logs = logger.get_logs(limit=10)
        assert len(logs) >= 1
        
        # Latest log should match
        latest = logs[0]
        assert latest["operator"] == operator
        assert latest["action"] == action
        assert latest["object"] == obj
    finally:
        temp_path.unlink(missing_ok=True)


def test_log_filtering():
    """Test log filtering by operator."""
    with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
        temp_path = Path(f.name)
    
    try:
        logger = OperationLogger(temp_path)
        
        # Log operations from different operators
        logger.log_operation("admin", "CREATE", "user1")
        logger.log_operation("root", "DELETE", "user2")
        logger.log_operation("admin", "UPDATE", "user3")
        
        # Filter by admin
        admin_logs = logger.get_logs(filter_operator="admin")
        assert len(admin_logs) == 2
        assert all(log["operator"] == "admin" for log in admin_logs)
        
        # Filter by root
        root_logs = logger.get_logs(filter_operator="root")
        assert len(root_logs) == 1
        assert root_logs[0]["operator"] == "root"
    finally:
        temp_path.unlink(missing_ok=True)


def test_log_limit():
    """Test log limit."""
    with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
        temp_path = Path(f.name)
    
    try:
        logger = OperationLogger(temp_path)
        
        # Log many operations
        for i in range(20):
            logger.log_operation("admin", "CREATE", f"object{i}")
        
        # Get limited logs
        logs = logger.get_logs(limit=5)
        assert len(logs) == 5
    finally:
        temp_path.unlink(missing_ok=True)
