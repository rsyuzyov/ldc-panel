"""LDIF command generation for AD operations"""
import base64
from typing import Optional, Dict, Any, List


def encode_unicode_pwd(password: str) -> str:
    """Encode password for unicodePwd attribute.
    
    The password must be enclosed in quotes, encoded as UTF-16LE, then base64 encoded.
    
    Args:
        password: Plain text password
        
    Returns:
        Base64 encoded password for unicodePwd attribute
    """
    # Password must be enclosed in quotes
    quoted_password = f'"{password}"'
    # Encode as UTF-16LE
    utf16_password = quoted_password.encode('utf-16-le')
    # Base64 encode
    return base64.b64encode(utf16_password).decode('ascii')


def generate_ldif_add(dn: str, attributes: Dict[str, Any]) -> str:
    """Generate LDIF for adding a new entry.
    
    Args:
        dn: Distinguished name of the entry
        attributes: Dictionary of attributes
        
    Returns:
        LDIF string for add operation (without changetype for ldbadd)
    """
    lines = [
        f"dn: {dn}",
    ]
    
    for key, value in attributes.items():
        if isinstance(value, list):
            for v in value:
                if key == "unicodePwd":
                    lines.append(f"{key}:: {v}")
                else:
                    lines.append(f"{key}: {v}")
        else:
            if key == "unicodePwd":
                lines.append(f"{key}:: {value}")
            else:
                lines.append(f"{key}: {value}")
    
    return "\n".join(lines) + "\n"


def generate_ldif_modify(dn: str, modifications: List[Dict[str, Any]]) -> str:
    """Generate LDIF for modifying an entry.
    
    Args:
        dn: Distinguished name of the entry
        modifications: List of modifications, each with 'operation', 'attribute', 'value'
                      operation can be 'replace', 'add', 'delete'
        
    Returns:
        LDIF string for modify operation
    """
    lines = [
        f"dn: {dn}",
        "changetype: modify",
    ]
    
    for i, mod in enumerate(modifications):
        operation = mod.get("operation", "replace")
        attribute = mod["attribute"]
        value = mod.get("value")
        
        lines.append(f"{operation}: {attribute}")
        
        if value is not None:
            if attribute == "unicodePwd":
                lines.append(f"{attribute}:: {value}")
            else:
                lines.append(f"{attribute}: {value}")
        
        # Add separator between modifications (except for last one)
        if i < len(modifications) - 1:
            lines.append("-")
    
    return "\n".join(lines) + "\n"


def generate_ldif_delete(dn: str) -> str:
    """Generate LDIF for deleting an entry.
    
    Args:
        dn: Distinguished name of the entry
        
    Returns:
        LDIF string for delete operation
    """
    return f"dn: {dn}\nchangetype: delete\n"


def generate_user_add_ldif(
    base_dn: str,
    ou: str,
    sam_account_name: str,
    cn: str,
    password: str,
    sn: Optional[str] = None,
    given_name: Optional[str] = None,
    mail: Optional[str] = None,
    user_principal_name: Optional[str] = None,
) -> str:
    """Generate LDIF for adding a new user.
    
    Args:
        base_dn: Base DN of the domain (e.g., DC=domain,DC=local)
        ou: Organizational unit (e.g., CN=Users)
        sam_account_name: SAM account name (login)
        cn: Common name
        password: User password
        sn: Surname
        given_name: Given name
        mail: Email address
        user_principal_name: UPN (e.g., user@domain.local)
        
    Returns:
        LDIF string for adding user
    """
    dn = f"CN={cn},{ou},{base_dn}"
    
    attributes = {
        "objectClass": ["top", "person", "organizationalPerson", "user"],
        "cn": cn,
        "sAMAccountName": sam_account_name,
        "userAccountControl": "512",  # Normal account
        "unicodePwd": encode_unicode_pwd(password),
    }
    
    if sn:
        attributes["sn"] = sn
    if given_name:
        attributes["givenName"] = given_name
    if mail:
        attributes["mail"] = mail
    if user_principal_name:
        attributes["userPrincipalName"] = user_principal_name
    
    return generate_ldif_add(dn, attributes)


def generate_user_modify_ldif(
    dn: str,
    cn: Optional[str] = None,
    sn: Optional[str] = None,
    given_name: Optional[str] = None,
    mail: Optional[str] = None,
    user_account_control: Optional[int] = None,
) -> str:
    """Generate LDIF for modifying a user.
    
    Args:
        dn: User DN
        cn: New common name
        sn: New surname
        given_name: New given name
        mail: New email
        user_account_control: New UAC value
        
    Returns:
        LDIF string for modifying user
    """
    modifications = []
    
    if cn is not None:
        modifications.append({"operation": "replace", "attribute": "cn", "value": cn})
    if sn is not None:
        modifications.append({"operation": "replace", "attribute": "sn", "value": sn})
    if given_name is not None:
        modifications.append({"operation": "replace", "attribute": "givenName", "value": given_name})
    if mail is not None:
        modifications.append({"operation": "replace", "attribute": "mail", "value": mail})
    if user_account_control is not None:
        modifications.append({"operation": "replace", "attribute": "userAccountControl", "value": str(user_account_control)})
    
    return generate_ldif_modify(dn, modifications)


def generate_password_change_ldif(dn: str, new_password: str) -> str:
    """Generate LDIF for changing user password.
    
    Args:
        dn: User DN
        new_password: New password
        
    Returns:
        LDIF string for password change
    """
    encoded_pwd = encode_unicode_pwd(new_password)
    modifications = [
        {"operation": "replace", "attribute": "unicodePwd", "value": encoded_pwd}
    ]
    return generate_ldif_modify(dn, modifications)


def generate_group_member_add_ldif(group_dn: str, member_dn: str) -> str:
    """Generate LDIF for adding a member to a group.
    
    Args:
        group_dn: Group DN
        member_dn: Member DN to add
        
    Returns:
        LDIF string for adding member
    """
    modifications = [
        {"operation": "add", "attribute": "member", "value": member_dn}
    ]
    return generate_ldif_modify(group_dn, modifications)


def generate_group_member_delete_ldif(group_dn: str, member_dn: str) -> str:
    """Generate LDIF for removing a member from a group.
    
    Args:
        group_dn: Group DN
        member_dn: Member DN to remove
        
    Returns:
        LDIF string for removing member
    """
    modifications = [
        {"operation": "delete", "attribute": "member", "value": member_dn}
    ]
    return generate_ldif_modify(group_dn, modifications)
