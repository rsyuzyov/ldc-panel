"""Active Directory operations service"""
from typing import List, Optional, Tuple
import tempfile
import os

from app.models.server import ServerConfig
from app.models.ad import ADUser, ADComputer, ADGroup
from app.services.ssh import SSHService
from app.services.ldap_cmd import (
    generate_user_add_ldif,
    generate_user_modify_ldif,
    generate_password_change_ldif,
    generate_ldif_delete,
    generate_ldif_add,
    generate_group_member_add_ldif,
    generate_group_member_delete_ldif,
)


class ADService:
    """Service for AD operations via SSH."""
    
    def __init__(self, server: ServerConfig, ssh: SSHService):
        self.server = server
        self.ssh = ssh
        self.base_dn = server.base_dn or ""
    
    def _parse_ldbsearch_output(self, output: str) -> List[dict]:
        """Parse ldbsearch output into list of dictionaries."""
        entries = []
        current_entry = {}
        
        for line in output.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                if current_entry:
                    entries.append(current_entry)
                    current_entry = {}
                continue
            
            if ': ' in line:
                key, value = line.split(': ', 1)
                if key in current_entry:
                    if isinstance(current_entry[key], list):
                        current_entry[key].append(value)
                    else:
                        current_entry[key] = [current_entry[key], value]
                else:
                    current_entry[key] = value
        
        if current_entry:
            entries.append(current_entry)
        
        return entries
    
    def search_users(self, filter_str: Optional[str] = None) -> Tuple[List[ADUser], str]:
        """Search for users in AD.
        
        Args:
            filter_str: Optional search filter
            
        Returns:
            Tuple of (users, error_message)
        """
        ldap_filter = "(objectClass=user)"
        if filter_str:
            ldap_filter = f"(&(objectClass=user)(|(cn=*{filter_str}*)(sAMAccountName=*{filter_str}*)(mail=*{filter_str}*)))"
        
        cmd = f'ldbsearch -H /var/lib/samba/private/sam.ldb "{ldap_filter}" dn cn sAMAccountName sn givenName mail userPrincipalName memberOf userAccountControl'
        
        exit_code, stdout, stderr = self.ssh.execute(cmd)
        
        if exit_code != 0:
            return [], stderr
        
        entries = self._parse_ldbsearch_output(stdout)
        users = []
        
        for entry in entries:
            if 'dn' not in entry or 'sAMAccountName' not in entry:
                continue
            
            member_of = entry.get('memberOf', [])
            if isinstance(member_of, str):
                member_of = [member_of]
            
            users.append(ADUser(
                dn=entry['dn'],
                sAMAccountName=entry['sAMAccountName'],
                cn=entry.get('cn', entry['sAMAccountName']),
                sn=entry.get('sn'),
                givenName=entry.get('givenName'),
                mail=entry.get('mail'),
                userPrincipalName=entry.get('userPrincipalName'),
                memberOf=member_of,
                userAccountControl=int(entry.get('userAccountControl', 512)),
            ))
        
        return users, ""
    
    def add_user(
        self,
        sam_account_name: str,
        cn: str,
        password: str,
        ou: str = "CN=Users",
        sn: Optional[str] = None,
        given_name: Optional[str] = None,
        mail: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Add a new user to AD.
        
        Returns:
            Tuple of (success, error_message)
        """
        domain = self.server.domain or "domain.local"
        upn = f"{sam_account_name}@{domain}"
        
        ldif = generate_user_add_ldif(
            base_dn=self.base_dn,
            ou=ou,
            sam_account_name=sam_account_name,
            cn=cn,
            password=password,
            sn=sn,
            given_name=given_name,
            mail=mail,
            user_principal_name=upn,
        )
        
        # Write LDIF to temp file and execute
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ldif', delete=False) as f:
            f.write(ldif)
            temp_path = f.name
        
        try:
            # Copy LDIF to server
            sftp = self.ssh.client.open_sftp()
            remote_path = f"/tmp/add_user_{sam_account_name}.ldif"
            sftp.put(temp_path, remote_path)
            sftp.close()
            
            # Execute ldapmodify
            cmd = f'ldapmodify -H ldapi:/// -f {remote_path}'
            exit_code, stdout, stderr = self.ssh.execute(cmd)
            
            # Cleanup
            self.ssh.execute(f'rm -f {remote_path}')
            
            if exit_code != 0:
                return False, stderr
            
            return True, ""
        finally:
            os.unlink(temp_path)
    
    def modify_user(
        self,
        dn: str,
        cn: Optional[str] = None,
        sn: Optional[str] = None,
        given_name: Optional[str] = None,
        mail: Optional[str] = None,
        user_account_control: Optional[int] = None,
    ) -> Tuple[bool, str]:
        """Modify an existing user.
        
        Returns:
            Tuple of (success, error_message)
        """
        ldif = generate_user_modify_ldif(
            dn=dn,
            cn=cn,
            sn=sn,
            given_name=given_name,
            mail=mail,
            user_account_control=user_account_control,
        )
        
        if not ldif.strip() or "changetype: modify" not in ldif:
            return True, ""  # Nothing to modify
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ldif', delete=False) as f:
            f.write(ldif)
            temp_path = f.name
        
        try:
            sftp = self.ssh.client.open_sftp()
            remote_path = "/tmp/modify_user.ldif"
            sftp.put(temp_path, remote_path)
            sftp.close()
            
            cmd = f'ldapmodify -H ldapi:/// -f {remote_path}'
            exit_code, stdout, stderr = self.ssh.execute(cmd)
            
            self.ssh.execute(f'rm -f {remote_path}')
            
            if exit_code != 0:
                return False, stderr
            
            return True, ""
        finally:
            os.unlink(temp_path)
    
    def delete_user(self, dn: str) -> Tuple[bool, str]:
        """Delete a user from AD.
        
        Returns:
            Tuple of (success, error_message)
        """
        cmd = f'ldapdelete -H ldapi:/// "{dn}"'
        exit_code, stdout, stderr = self.ssh.execute(cmd)
        
        if exit_code != 0:
            return False, stderr
        
        return True, ""
    
    def change_password(self, dn: str, new_password: str) -> Tuple[bool, str]:
        """Change user password.
        
        Returns:
            Tuple of (success, error_message)
        """
        ldif = generate_password_change_ldif(dn, new_password)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ldif', delete=False) as f:
            f.write(ldif)
            temp_path = f.name
        
        try:
            sftp = self.ssh.client.open_sftp()
            remote_path = "/tmp/change_pwd.ldif"
            sftp.put(temp_path, remote_path)
            sftp.close()
            
            cmd = f'ldapmodify -H ldapi:/// -f {remote_path}'
            exit_code, stdout, stderr = self.ssh.execute(cmd)
            
            self.ssh.execute(f'rm -f {remote_path}')
            
            if exit_code != 0:
                return False, stderr
            
            return True, ""
        finally:
            os.unlink(temp_path)
    
    def search_computers(self, filter_str: Optional[str] = None) -> Tuple[List[ADComputer], str]:
        """Search for computers in AD."""
        ldap_filter = "(objectClass=computer)"
        if filter_str:
            ldap_filter = f"(&(objectClass=computer)(cn=*{filter_str}*))"
        
        cmd = f'ldbsearch -H /var/lib/samba/private/sam.ldb "{ldap_filter}" dn cn sAMAccountName operatingSystem operatingSystemVersion dNSHostName lastLogonTimestamp userAccountControl'
        
        exit_code, stdout, stderr = self.ssh.execute(cmd)
        
        if exit_code != 0:
            return [], stderr
        
        entries = self._parse_ldbsearch_output(stdout)
        computers = []
        
        for entry in entries:
            if 'dn' not in entry:
                continue
            
            computers.append(ADComputer(
                dn=entry['dn'],
                cn=entry.get('cn', ''),
                sAMAccountName=entry.get('sAMAccountName', ''),
                operatingSystem=entry.get('operatingSystem'),
                operatingSystemVersion=entry.get('operatingSystemVersion'),
                dNSHostName=entry.get('dNSHostName'),
                lastLogonTimestamp=entry.get('lastLogonTimestamp'),
                userAccountControl=int(entry.get('userAccountControl', 4096)),
            ))
        
        return computers, ""
    
    def search_groups(self, filter_str: Optional[str] = None) -> Tuple[List[ADGroup], str]:
        """Search for groups in AD."""
        ldap_filter = "(objectClass=group)"
        if filter_str:
            ldap_filter = f"(&(objectClass=group)(cn=*{filter_str}*))"
        
        cmd = f'ldbsearch -H /var/lib/samba/private/sam.ldb "{ldap_filter}" dn cn sAMAccountName description member groupType'
        
        exit_code, stdout, stderr = self.ssh.execute(cmd)
        
        if exit_code != 0:
            return [], stderr
        
        entries = self._parse_ldbsearch_output(stdout)
        groups = []
        
        for entry in entries:
            if 'dn' not in entry:
                continue
            
            members = entry.get('member', [])
            if isinstance(members, str):
                members = [members]
            
            groups.append(ADGroup(
                dn=entry['dn'],
                cn=entry.get('cn', ''),
                sAMAccountName=entry.get('sAMAccountName', ''),
                description=entry.get('description'),
                member=members,
                groupType=int(entry.get('groupType', -2147483646)),
            ))
        
        return groups, ""
    
    def add_group_member(self, group_dn: str, member_dn: str) -> Tuple[bool, str]:
        """Add a member to a group."""
        ldif = generate_group_member_add_ldif(group_dn, member_dn)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ldif', delete=False) as f:
            f.write(ldif)
            temp_path = f.name
        
        try:
            sftp = self.ssh.client.open_sftp()
            remote_path = "/tmp/add_member.ldif"
            sftp.put(temp_path, remote_path)
            sftp.close()
            
            cmd = f'ldapmodify -H ldapi:/// -f {remote_path}'
            exit_code, stdout, stderr = self.ssh.execute(cmd)
            
            self.ssh.execute(f'rm -f {remote_path}')
            
            if exit_code != 0:
                return False, stderr
            
            return True, ""
        finally:
            os.unlink(temp_path)
    
    def remove_group_member(self, group_dn: str, member_dn: str) -> Tuple[bool, str]:
        """Remove a member from a group."""
        ldif = generate_group_member_delete_ldif(group_dn, member_dn)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ldif', delete=False) as f:
            f.write(ldif)
            temp_path = f.name
        
        try:
            sftp = self.ssh.client.open_sftp()
            remote_path = "/tmp/del_member.ldif"
            sftp.put(temp_path, remote_path)
            sftp.close()
            
            cmd = f'ldapmodify -H ldapi:/// -f {remote_path}'
            exit_code, stdout, stderr = self.ssh.execute(cmd)
            
            self.ssh.execute(f'rm -f {remote_path}')
            
            if exit_code != 0:
                return False, stderr
            
            return True, ""
        finally:
            os.unlink(temp_path)
