import sys
import os
import asyncio
from app.services.server_store import server_store
from app.services.ssh import SSHService

async def check_dns():
    print("Checking DNS...")
    server = server_store.get_by_id("srv-dc1-ag-local")
    if not server:
        print("Server not found")
        return

    print(f"Server: {server.host}")
    print(f"Base DN: {server.base_dn}")

    ssh = SSHService(server)
    connected, err = ssh.connect()
    if not connected:
        print(f"SSH Failed: {err}")
        return

    domain_dn = server.base_dn
    
    partitions = [
        f"CN=MicrosoftDNS,DC=DomainDnsZones,{domain_dn}",
        f"CN=MicrosoftDNS,DC=ForestDnsZones,{domain_dn}"
    ]

    for base_dn in partitions:
        print(f"\nSearching in: {base_dn}")
        cmd = f'ldbsearch -H ldap://{server.host} -k yes -b "{base_dn}" "(objectClass=dnsZone)" name'
        print(f"CMD: {cmd}")
        
        exit_code, stdout, stderr = ssh.execute(cmd)
        print(f"Exit: {exit_code}")
        print("Stdout:")
        print(stdout)
        print("Stderr:")
        print(stderr)

    ssh.disconnect()

if __name__ == "__main__":
    asyncio.run(check_dns())
