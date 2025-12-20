"""Active Directory operations service"""
from typing import List, Optional, Tuple
import tempfile
import os
import base64

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
        """Parse ldbsearch output into list of dictionaries.
        
        Handles base64 encoded values (format: key:: base64value)
        and LDIF line continuation (lines starting with space)
        """
        entries = []
        current_entry = {}
        
        # Сначала объединяем продолжения строк (строки начинающиеся с пробела)
        lines = []
        for line in output.split('\n'):
            if line.startswith(' ') and lines:
                # Продолжение предыдущей строки
                lines[-1] += line[1:]
            else:
                lines.append(line)
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                if current_entry:
                    entries.append(current_entry)
                    current_entry = {}
                continue
            
            # Base64 encoded value (key:: value)
            if ':: ' in line:
                key, value = line.split(':: ', 1)
                try:
                    decoded = base64.b64decode(value)
                    # Пробуем UTF-8, затем latin-1
                    try:
                        value = decoded.decode('utf-8')
                    except UnicodeDecodeError:
                        value = decoded.decode('latin-1')
                except Exception:
                    pass  # Keep original if decode fails
            elif ': ' in line:
                key, value = line.split(': ', 1)
            else:
                continue
                
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
        # Пользователи: исключаем компьютеры ($) и managed service accounts
        ldap_filter = "(&(objectClass=user)(!(objectClass=computer))(!(objectClass=msDS-ManagedServiceAccount))(!(objectClass=msDS-GroupManagedServiceAccount)))"
        if filter_str:
            ldap_filter = f"(&(objectClass=user)(!(objectClass=computer))(!(objectClass=msDS-ManagedServiceAccount))(!(objectClass=msDS-GroupManagedServiceAccount))(|(cn=*{filter_str}*)(sAMAccountName=*{filter_str}*)(mail=*{filter_str}*)))"
        
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
        """Add a new user to AD using samba-tool.
        
        Returns:
            Tuple of (success, error_message)
        """
        # Use samba-tool for user creation (more reliable than ldbadd)
        cmd = f'samba-tool user create "{sam_account_name}" "{password}" --given-name="{cn}"'
        
        if mail:
            cmd += f' --mail-address="{mail}"'
        
        exit_code, stdout, stderr = self.ssh.execute(cmd)
        
        print(f"[DEBUG] samba-tool exit_code={exit_code}")
        print(f"[DEBUG] samba-tool stdout={stdout}")
        print(f"[DEBUG] samba-tool stderr={stderr}")
        
        if exit_code != 0:
            return False, stderr or stdout
        
        return True, ""
    
    def modify_user(
        self,
        dn: str,
        cn: Optional[str] = None,
        sn: Optional[str] = None,
        given_name: Optional[str] = None,
        mail: Optional[str] = None,
        user_account_control: Optional[int] = None,
    ) -> Tuple[bool, str]:
        """Modify an existing user using samba-tool.
        
        Returns:
            Tuple of (success, error_message)
        """
        print(f"[DEBUG] modify_user dn={dn}, cn={cn}, mail={mail}")
        
        # Extract sAMAccountName from DN for samba-tool
        # DN format: CN=...,CN=Users,DC=...
        sam_name = None
        users, _ = self.search_users()
        for u in users:
            if u.dn == dn:
                sam_name = u.sAMAccountName
                break
        
        if not sam_name:
            return False, f"Пользователь с DN {dn} не найден"
        
        # Use samba-tool user setexpiry or direct ldbmodify with proper format
        # For mail, use ldbmodify
        if mail:
            cmd = f'ldbmodify -H /var/lib/samba/private/sam.ldb <<EOF\ndn: {dn}\nchangetype: modify\nreplace: mail\nmail: {mail}\nEOF'
            exit_code, stdout, stderr = self.ssh.execute(cmd)
            print(f"[DEBUG] ldbmodify mail exit_code={exit_code}, stderr={stderr}")
            if exit_code != 0 and "No such attribute" not in stderr:
                return False, stderr or stdout
        
        return True, ""
    
    def delete_user(self, dn: str) -> Tuple[bool, str]:
        """Delete a user from AD.
        
        Returns:
            Tuple of (success, error_message)
        """
        cmd = f'ldbdel -H /var/lib/samba/private/sam.ldb "{dn}"'
        exit_code, stdout, stderr = self.ssh.execute(cmd)
        
        if exit_code != 0:
            return False, stderr or stdout
        
        return True, ""
    
    def find_user_dn(self, sam_account_name: str) -> Optional[str]:
        """Find user DN by sAMAccountName.
        
        Returns:
            DN string or None if not found
        """
        cmd = f'ldbsearch -H /var/lib/samba/private/sam.ldb "(&(objectClass=user)(sAMAccountName={sam_account_name}))" dn'
        exit_code, stdout, stderr = self.ssh.execute(cmd)
        
        print(f"[DEBUG] find_user_dn sam={sam_account_name}, exit_code={exit_code}")
        print(f"[DEBUG] find_user_dn stdout={stdout}")
        
        if exit_code != 0:
            return None
        
        entries = self._parse_ldbsearch_output(stdout)
        for entry in entries:
            if 'dn' in entry:
                print(f"[DEBUG] find_user_dn found dn={entry['dn']}")
                return entry['dn']
        
        return None
    
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
            
            cmd = f'ldbmodify -H /var/lib/samba/private/sam.ldb {remote_path}'
            exit_code, stdout, stderr = self.ssh.execute(cmd)
            
            self.ssh.execute(f'rm -f {remote_path}')
            
            if exit_code != 0:
                return False, stderr or stdout
            
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
            
            # cn может быть списком, берём первый элемент
            cn = entry.get('cn', '')
            if isinstance(cn, list):
                cn = cn[0] if cn else ''
            
            sam = entry.get('sAMAccountName', '')
            if isinstance(sam, list):
                sam = sam[0] if sam else ''
            
            groups.append(ADGroup(
                dn=entry['dn'],
                cn=cn,
                sAMAccountName=sam,
                description=entry.get('description'),
                member=members,
                groupType=int(entry.get('groupType', -2147483646)),
            ))
        
        return groups, ""
    
    def add_group_member(self, group_dn: str, member_dn: str) -> Tuple[bool, str]:
        """Add a member to a group using samba-tool."""
        # Извлекаем CN группы из DN
        import re
        match = re.match(r'CN=([^,]+)', group_dn, re.IGNORECASE)
        if not match:
            return False, f"Invalid group DN: {group_dn}"
        group_cn = match.group(1)
        
        # Извлекаем sAMAccountName пользователя из DN
        match = re.match(r'CN=([^,]+)', member_dn, re.IGNORECASE)
        if not match:
            return False, f"Invalid member DN: {member_dn}"
        member_cn = match.group(1)
        
        cmd = f'samba-tool group addmembers "{group_cn}" "{member_cn}"'
        exit_code, stdout, stderr = self.ssh.execute(cmd)
        
        if exit_code != 0:
            return False, stderr or stdout
        
        return True, ""
    
    def remove_group_member(self, group_dn: str, member_dn: str) -> Tuple[bool, str]:
        """Remove a member from a group using samba-tool."""
        # Извлекаем CN группы из DN
        import re
        match = re.match(r'CN=([^,]+)', group_dn, re.IGNORECASE)
        if not match:
            return False, f"Invalid group DN: {group_dn}"
        group_cn = match.group(1)
        
        # Извлекаем sAMAccountName пользователя из DN
        match = re.match(r'CN=([^,]+)', member_dn, re.IGNORECASE)
        if not match:
            return False, f"Invalid member DN: {member_dn}"
        member_cn = match.group(1)
        
        cmd = f'samba-tool group removemembers "{group_cn}" "{member_cn}"'
        exit_code, stdout, stderr = self.ssh.execute(cmd)
        
        if exit_code != 0:
            return False, stderr or stdout
        
        return True, ""
