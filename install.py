#!/usr/bin/env python3
"""LDC Panel Installation Script"""
import os
import sys
import subprocess
import platform
from pathlib import Path

IS_WINDOWS = os.name == 'nt'

def run_cmd(cmd: str, check: bool = True) -> bool:
    """Run a shell command."""
    print(f"  → {cmd}")
    result = subprocess.run(cmd, shell=True, check=False)
    if check and result.returncode != 0:
        print(f"  ✗ Command failed with code {result.returncode}")
        return False
    return result.returncode == 0

import shutil
def check_npm():
    """Check if npm is installed."""
    return shutil.which("npm") is not None



def main():
    print("=" * 50)
    print("LDC Panel Installation")
    print("=" * 50)
    
    # Check if running as root (Linux only)
    if not IS_WINDOWS:
        if os.geteuid() != 0:
            print("Error: This script must be run as root")
            print("Usage: sudo python3 install.py")
            sys.exit(1)
    
    root_dir = Path(__file__).parent.resolve()
    backend_dir = root_dir / "backend"
    venv_path = backend_dir / ".venv"
    
    # Step 1: Install system dependencies (Linux only)
    if not IS_WINDOWS:
        print("\n[1/7] Installing system dependencies...")
        if not run_cmd("apt-get update -qq"):
            sys.exit(1)
        if not run_cmd("apt-get install -y python3-pip python3-venv python3-dev libpam0g-dev nginx nodejs npm"):
            sys.exit(1)
    else:
        print("\n[1/7] Skipping system dependencies (Windows detected)...")
    
    # Step 2: Create virtual environment
    print("\n[2/7] Creating virtual environment...")
    if not venv_path.exists():
        if not run_cmd(f'"{sys.executable}" -m venv "{venv_path}"'):
            sys.exit(1)
    else:
        print("  → Virtual environment already exists")
    
    # Step 3: Install Python dependencies
    print("\n[3/7] Installing Python dependencies...")
    if IS_WINDOWS:
        pip_path = venv_path / "Scripts" / "pip.exe"
        python_path = venv_path / "Scripts" / "python.exe"
    else:
        pip_path = venv_path / "bin" / "pip"
        python_path = venv_path / "bin" / "python"

    requirements_path = backend_dir / "requirements.txt"
    
    # Use python -m pip to upgrade pip (pip can't upgrade itself directly)
    if not run_cmd(f'"{python_path}" -m pip install --upgrade pip'):
        sys.exit(1)

    # Allow modifying requirements for Windows on the fly or just warn?
    # Better approach: Read requirements, filter out incompatible ones, write temp file
    if IS_WINDOWS:
        print("  → Filtering Windows-incompatible dependencies...")
        reqs = requirements_path.read_text().splitlines()
        # Filter out gunicorn and python-pam which are typically Linux-only or problematic
        # python-pam needs libpam which is missing on Windows.
        # gunicorn is UNIX only.
        filtered_reqs = [r for r in reqs if not r.startswith("gunicorn") and not r.startswith("python-pam")]
        
        temp_reqs = backend_dir / "requirements_win.txt"
        temp_reqs.write_text("\n".join(filtered_reqs))
        if not run_cmd(f'"{pip_path}" install -r "{temp_reqs}"'):
            sys.exit(1)
        # Clean up
        if temp_reqs.exists():
            os.remove(temp_reqs)
    else:
        if not run_cmd(f'"{pip_path}" install -r "{requirements_path}"'):
            sys.exit(1)
    
    # Step 4: Create directories
    print("\n[4/7] Creating directories...")
    if IS_WINDOWS:
        # On Windows, keep everything local to avoid permission issues
        data_dir = root_dir / "data"
        dirs = [
            data_dir / "logs",
            data_dir / "backups" / "ldif",
            data_dir / "backups" / "dhcp",
            backend_dir / "keys",
        ]
    else:
        dirs = [
            Path("/var/log"),
            Path("/backups/ldif"),
            Path("/backups/dhcp"),
            backend_dir / "keys",
        ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        print(f"  → {d}")
    
    # Set permissions for keys directory (Linux only primarily, but good practice)
    keys_dir = backend_dir / "keys"
    if not IS_WINDOWS:
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
    
    # Step 6: Install systemd service (Linux only)
    if not IS_WINDOWS:
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
    else:
        print("\n[6/7] Skipping systemd service (Windows detected)...")
    
    # Step 7: Install logrotate config (Linux only)
    if not IS_WINDOWS:
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
    else:
        print("\n[7/7] Skipping logrotate config (Windows detected)...")
    
    # Done
    print("\n" + "=" * 50)
    print("✓ Installation complete!")
    print("=" * 50)
    print("\nNext steps:")
    # Step 8: Build Frontend
    print("\n[8/8] Building Frontend...")
    frontend_dir = root_dir / "frontend"
    if not check_npm():
        print("  ✗ Error: npm not found. Skipping frontend build.")
        print("    Please install Node.js and npm manually and run: cd frontend && npm install && npm run build")
    else:
        try:
            print("  → Installing frontend dependencies...")
            npm_cmd = "npm" 
            # On Windows we might need npm.cmd, but check_npm uses shutil.which which handles it. 
            # However, for subprocess on Windows, shell=True helps or using full path.
            # Since install.py for Windows skips apt, we rely on user having Node installed.
            
            if IS_WINDOWS:
                 npm_cmd = "npm.cmd"
            
            # Using quotes to handle paths with spaces
            if not run_cmd(f'cd "{frontend_dir}" && {npm_cmd} install'):
                 print("  ✗ Frontend install failed")
            elif not run_cmd(f'cd "{frontend_dir}" && {npm_cmd} run build'):
                 print("  ✗ Frontend build failed")
            else:
                 print("  ✓ Frontend built successfully")
        except Exception as e:
            print(f"  ✗ Error building frontend: {e}")

    # Done
    print("\n" + "=" * 50)
    print("✓ Installation complete!")
    print("=" * 50)
    print("\nNext steps:")
    if not (frontend_dir / "dist").exists():
         print(f"  1. Build frontend (if failed above): cd frontend && npm install && npm run build")
    if not IS_WINDOWS:

        print("  2. Configure nginx: cp nginx.conf /etc/nginx/sites-available/ldc-panel")
        print("  3. Enable nginx site: ln -s /etc/nginx/sites-available/ldc-panel /etc/nginx/sites-enabled/")
        print("  4. Create SSL certificate or use Let's Encrypt")
        print("  5. Start the service: systemctl start ldc-panel")
        print("  6. Restart nginx: systemctl restart nginx")
        print("\nDefault login: root (system password)")
    else:
        print(f"  2. Run the server: python {root_dir}/run.py")

    print(f"\nTo run in development mode: python {root_dir}/run.py")


if __name__ == "__main__":
    main()
