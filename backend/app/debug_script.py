import sys
import os
import asyncio
from app.auth.pam import authenticate_root
from app.services.server_store import server_store
from app.services.ssh import SSHService
from app.api.dns import get_domain_dn
import traceback

print(f"Platform: {sys.platform}")
print(f"LDC_DEV_AUTH: {os.environ.get('LDC_DEV_AUTH')}")
print(f"LDC_DEV_PASSWORD: {os.environ.get('LDC_DEV_PASSWORD')}")

# Test Auth
success, error = authenticate_root("root", "admin")
print(f"Auth root/admin: {success} ({error})")

success, error = authenticate_root("root", "root")
print(f"Auth root/root: {success} ({error})")

# Test DNS
async def test_dns():
    print("\nTesting DNS...")
    # Assuming we have the server
    server = server_store.get_by_id("srv-dc1-ag-local")
    if not server:
        print("Server 'srv-dc1-ag-local' not found. Available servers:")
        for s in server_store.servers:
            print(f"- {s.id}")
        return

    print(f"Found server: {server.host}")
    ssh = SSHService(server)
    connected, err = ssh.connect()
    if not connected:
        print(f"SSH Connect failed: {err}")
        return
    print("SSH Connected")

    try:
        # Test get_domain_dn
        print("Testing get_domain_dn...")
        dn = get_domain_dn(ssh, server)
        print(f"Domain DN: {dn}")

        # Test ldbsearch for zones
        print("\nTesting ldbsearch for zones (DomainDnsZones)...")
        parts = dn.split(',') # Assuming dn is correct
        base_dn = f"CN=MicrosoftDNS,DC=DomainDnsZones,{dn}"
        cmd = f'ldbsearch -H ldap://{server.host} -k yes -b "{base_dn}" "(objectClass=dnsZone)" name'
        print(f"Command: {cmd}")
        exit_code, stdout, stderr = ssh.execute(cmd)
        print(f"Exit: {exit_code}")
        print(f"Stdout partial: {stdout[:200]}")
        print(f"Stderr: {stderr}")

    except Exception:
        traceback.print_exc()
    finally:
        ssh.disconnect()

if __name__ == "__main__":
    asyncio.run(test_dns())
