"""Property-based tests for search filter"""
import pytest
from hypothesis import given, strategies as st, settings
from typing import List


def filter_objects(objects: List[dict], query: str, fields: List[str]) -> List[dict]:
    """Filter objects by search query.
    
    Args:
        objects: List of objects to filter
        query: Search query string
        fields: Fields to search in
        
    Returns:
        Filtered list of objects containing the query substring
    """
    if not query:
        return objects
    
    query_lower = query.lower()
    result = []
    
    for obj in objects:
        for field in fields:
            value = obj.get(field, "")
            if value and query_lower in str(value).lower():
                result.append(obj)
                break
    
    return result


# **Feature: ldc-panel, Property 7: Search filter correctness**
# **Validates: Requirements 3.2**
@given(
    query=st.text(min_size=1, max_size=20),
    objects=st.lists(
        st.fixed_dictionaries({
            'cn': st.text(min_size=1, max_size=50),
            'sAMAccountName': st.text(min_size=1, max_size=20),
            'mail': st.one_of(st.none(), st.emails()),
        }),
        min_size=0,
        max_size=20,
    ),
)
@settings(max_examples=100)
def test_search_filter_correctness(query: str, objects: List[dict]):
    """For any search query and list of objects, result should contain only objects with matching substring."""
    fields = ['cn', 'sAMAccountName', 'mail']
    result = filter_objects(objects, query, fields)
    
    query_lower = query.lower()
    
    # All results should contain the query substring in at least one field
    for obj in result:
        found = False
        for field in fields:
            value = obj.get(field, "")
            if value and query_lower in str(value).lower():
                found = True
                break
        assert found, f"Object {obj} does not contain query '{query}'"
    
    # All objects containing the query should be in results
    for obj in objects:
        should_match = False
        for field in fields:
            value = obj.get(field, "")
            if value and query_lower in str(value).lower():
                should_match = True
                break
        
        if should_match:
            assert obj in result, f"Object {obj} should be in results for query '{query}'"


def test_empty_query_returns_all():
    """Empty query should return all objects."""
    objects = [
        {'cn': 'John Doe', 'sAMAccountName': 'jdoe', 'mail': 'jdoe@test.local'},
        {'cn': 'Jane Smith', 'sAMAccountName': 'jsmith', 'mail': 'jsmith@test.local'},
    ]
    
    result = filter_objects(objects, "", ['cn', 'sAMAccountName', 'mail'])
    assert result == objects


def test_case_insensitive_search():
    """Search should be case insensitive."""
    objects = [
        {'cn': 'John Doe', 'sAMAccountName': 'jdoe', 'mail': 'jdoe@test.local'},
    ]
    
    result1 = filter_objects(objects, "john", ['cn', 'sAMAccountName', 'mail'])
    result2 = filter_objects(objects, "JOHN", ['cn', 'sAMAccountName', 'mail'])
    result3 = filter_objects(objects, "John", ['cn', 'sAMAccountName', 'mail'])
    
    assert result1 == result2 == result3 == objects
