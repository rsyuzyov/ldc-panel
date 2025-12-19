"""Property-based tests for LDIF command generation"""
import pytest
import base64
from hypothesis import given, strategies as st, settings

from app.services.ldap_cmd import (
    encode_unicode_pwd,
    generate_ldif_add,
    generate_ldif_modify,
    generate_ldif_delete,
    generate_user_add_ldif,
    generate_user_modify_ldif,
    generate_password_change_ldif,
)


# Strategy for valid SAM account names
sam_account_names = st.text(
    min_size=1, 
    max_size=20, 
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-_')
)

# Strategy for valid common names
common_names = st.text(min_size=1, max_size=50).filter(lambda x: x.strip() and ',' not in x and '=' not in x)

# Strategy for passwords
passwords = st.text(min_size=8, max_size=50).filter(lambda x: x.strip())


# **Feature: ldc-panel, Property 10: Password encoding**
# **Validates: Requirements 3.6**
@given(password=passwords)
@settings(max_examples=100)
def test_password_encoding(password: str):
    """For any password, unicodePwd encoding should be: UTF-16LE string in quotes, then base64."""
    encoded = encode_unicode_pwd(password)
    
    # Should be valid base64
    decoded_bytes = base64.b64decode(encoded)
    
    # Should decode to UTF-16LE
    decoded_str = decoded_bytes.decode('utf-16-le')
    
    # Should be the password enclosed in quotes
    assert decoded_str == f'"{password}"'


# **Feature: ldc-panel, Property 8: LDIF add generation**
# **Validates: Requirements 3.3**
@given(
    sam_account_name=sam_account_names,
    cn=common_names,
    password=passwords,
)
@settings(max_examples=100)
def test_ldif_add_generation(sam_account_name: str, cn: str, password: str):
    """For any valid user data, generated LDIF for add should contain correct DN, objectClass and required attributes."""
    base_dn = "DC=domain,DC=local"
    ou = "CN=Users"
    
    ldif = generate_user_add_ldif(
        base_dn=base_dn,
        ou=ou,
        sam_account_name=sam_account_name,
        cn=cn,
        password=password,
    )
    
    # Should contain correct DN
    expected_dn = f"dn: CN={cn},{ou},{base_dn}"
    assert expected_dn in ldif
    
    # Should contain changetype: add
    assert "changetype: add" in ldif
    
    # Should contain objectClass
    assert "objectClass: user" in ldif
    assert "objectClass: person" in ldif
    
    # Should contain required attributes
    assert f"cn: {cn}" in ldif
    assert f"sAMAccountName: {sam_account_name}" in ldif
    assert "userAccountControl: 512" in ldif
    
    # Should contain encoded password (base64 indicator ::)
    assert "unicodePwd::" in ldif


# **Feature: ldc-panel, Property 9: LDIF modify generation**
# **Validates: Requirements 3.4**
@given(
    cn=common_names,
    mail=st.emails(),
)
@settings(max_examples=100)
def test_ldif_modify_generation(cn: str, mail: str):
    """For any attribute change, generated LDIF should contain changetype:modify and correct replace/add/delete operation."""
    dn = f"CN={cn},CN=Users,DC=domain,DC=local"
    
    ldif = generate_user_modify_ldif(
        dn=dn,
        mail=mail,
    )
    
    # Should contain correct DN
    assert f"dn: {dn}" in ldif
    
    # Should contain changetype: modify
    assert "changetype: modify" in ldif
    
    # Should contain replace operation for mail
    assert "replace: mail" in ldif
    assert f"mail: {mail}" in ldif


def test_ldif_delete_generation():
    """Test LDIF delete generation."""
    dn = "CN=TestUser,CN=Users,DC=domain,DC=local"
    
    ldif = generate_ldif_delete(dn)
    
    assert f"dn: {dn}" in ldif
    assert "changetype: delete" in ldif


def test_password_change_ldif():
    """Test password change LDIF generation."""
    dn = "CN=TestUser,CN=Users,DC=domain,DC=local"
    new_password = "NewP@ssw0rd!"
    
    ldif = generate_password_change_ldif(dn, new_password)
    
    assert f"dn: {dn}" in ldif
    assert "changetype: modify" in ldif
    assert "replace: unicodePwd" in ldif
    assert "unicodePwd::" in ldif


def test_ldif_add_with_optional_attributes():
    """Test LDIF add with optional attributes."""
    ldif = generate_user_add_ldif(
        base_dn="DC=test,DC=local",
        ou="OU=Staff",
        sam_account_name="jdoe",
        cn="John Doe",
        password="P@ssw0rd!",
        sn="Doe",
        given_name="John",
        mail="jdoe@test.local",
        user_principal_name="jdoe@test.local",
    )
    
    assert "sn: Doe" in ldif
    assert "givenName: John" in ldif
    assert "mail: jdoe@test.local" in ldif
    assert "userPrincipalName: jdoe@test.local" in ldif
