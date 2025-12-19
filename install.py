#!/usr/bin/env python3
"""LDC Panel Installation Script"""
import os
import sys
import subprocess
from pathlib import Path


def run_cmd(cmd: str, check: bool = True) -> bool:
    """Run a shell command."""
    print(f"  → {cmd}")
    result = subprocess.run(cmd, shell=True, check=False)
    if check and result.returncode != 0:
        print(f"  ✗ Command failed with code {result.returncode}")
        return False
    return result.returncode == 0


def main():
    print("=" * 50)
    print("LDC Panel Installation")
    print("=" * 50)
    
    # Check if running as root
    if os.geteuid() != 0:
        print("Error: This script must be run as root")
        print("Usage: sudo python3 install.py")
        sys.exit(1)
    
    root_dir = Path(__file__).parent.resolve()
    backend_dir = root_dir / "backend"
    venv_path = backend_dir / "venv"
    
    # Step 1: Install system dependencies
    print("\n[1/7] Installing system dependencies...")
    if not run_cmd("apt-get update -qq"):
        sys.exit(1)
    if not run_cmd("apt-get install -y python3-pip python3-venv python3-dev libpam0g-dev nginx"):
        sys.exit(1)
    
    # Step 2: Create virtual environment
    print("\n[2/7] Creating virtual environment...")
    if not venv_path.exists():
        if not run_cmd(f"python3 -m venv {venv_path}"):
            sys.exit(1)
    else:
        print("  → Virtual environment already exists")
    
    # Step 3: Install Python dependencies
    print("\n[3/7] Installing Python dependencies...")
    pip_path = venv_path / "bin" / "pip"
    requirements_path = backend_dir / "requirements.txt"
    if not run_cmd(f"{pip_path} install --upgrade pip"):
        sys.exit(1)
    if not run_cmd(f"{pip_path} install -r {requirements_path}"):
        sys.exit(1)
    
    # Step 4: Create directories
    print("\n[4/7] Creating directories...")
    dirs = [
        Path("/var/log"),
        Path("/backups/ldif"),
        Path("/backups/dhcp"),
        backend_dir / "keys",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        print(f"  → {d}")
    
    # Set permissions for keys directory
    keys_dir = backend_dir / "keys"
    os.chmod(keys_dir, 0o700)
    print(f"  → Set {keys_dir} permissions to 700")
    
    # Step 5: Create servers.yaml if not exists
    print("\n[5/7] Creating default configuration...")
    servers_yaml = backend_dir / "servers.yaml"
    if not servers_yaml.exists():
        servers_yaml.write_text("""# LDC Panel - Server Configuration
servers: []
""")
        print(f"  → Created {servers_yaml}")
    else:
        print(f"  → {servers_yaml} already exists")
    
    # Step 6: Install systemd service
    print("\n[6/7] Installing systemd service...")
    service_content = f"""[Unit]
Description=LDC Panel - Linux DC Panel
After=network.target

[Service]
Type=exec
User=root
WorkingDirectory={backend_dir}
ExecStart={venv_path}/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8000
Restart=always
RestartSec=5
Environment=LDC_DEBUG=false

[Install]
WantedBy=multi-user.target
"""
    
    service_path = Path("/etc/systemd/system/ldc-panel.service")
    service_path.write_text(service_content)
    print(f"  → Created {service_path}")
    
    run_cmd("systemctl daemon-reload")
    run_cmd("systemctl enable ldc-panel")
    
    # Step 7: Install logrotate config
    print("\n[7/7] Installing logrotate config...")
    logrotate_content = """/var/log/ldc-panel.log {
    yearly
    rotate 1
    compress
    delaycompress
    missingok
    notifempty
    create 640 root root
}
"""
    logrotate_dst = Path("/etc/logrotate.d/ldc-panel")
    logrotate_dst.write_text(logrotate_content)
    print(f"  → Created {logrotate_dst}")
    
    # Done
    print("\n" + "=" * 50)
    print("✓ Installation complete!")
    print("=" * 50)
    print("\nNext steps:")
    print(f"  1. Build frontend: cd {root_dir}/frontend && npm install && npm run build")
    print("  2. Configure nginx: cp nginx.conf /etc/nginx/sites-available/ldc-panel")
    print("  3. Enable nginx site: ln -s /etc/nginx/sites-available/ldc-panel /etc/nginx/sites-enabled/")
    print("  4. Create SSL certificate or use Let's Encrypt")
    print("  5. Start the service: systemctl start ldc-panel")
    print("  6. Restart nginx: systemctl restart nginx")
    print("\nDefault login: root (system password)")
    print(f"\nTo run in development mode: python3 {root_dir}/run.py")


if __name__ == "__main__":
    main()
