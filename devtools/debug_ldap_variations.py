import asyncio
from app.services.server_store import server_store
from app.services.ssh import SSHService

async def test_variations():
    server = server_store.get_by_id("srv-dc1-ag-local")
    if not server:
        print("Server not found")
        return

    ssh = SSHService(server)
    ssh.connect()
    
    base_dn = "CN=MicrosoftDNS,DC=DomainDnsZones,DC=ag,DC=local"
    
    variations = [
        # Try without ldap:// prefix
        f'ldbsearch -H {server.host} -k yes -b "{base_dn}" "(objectClass=dnsZone)" name',
        # Try local path
        f'ldbsearch -H /var/lib/samba/private/sam.ldb -b "{base_dn}" "(objectClass=dnsZone)" name' 
    ]

    print(f"Testing variations for {server.host}...\n")
    
    with open("debug_output.txt", "w", encoding="utf-8") as f:
        for cmd in variations:
            f.write(f"CMD: {cmd}\n")
            f.flush()
            print(f"CMD: {cmd}")
            exit_code, stdout, stderr = ssh.execute(cmd)
            f.write(f"Exit: {exit_code}\n")
            if exit_code == 0:
                f.write("SUCCESS!\n")
                f.write(stdout)
            else:
                f.write(f"FAILED: {stderr.strip()}\n")
                if "NT_STATUS" in stdout:
                    f.write(f"STDOUT ERR: {stdout.strip()}\n")
            f.write("-" * 50 + "\n")
            f.flush()

    ssh.disconnect()

if __name__ == "__main__":
    asyncio.run(test_variations())
