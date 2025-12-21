#!/usr/bin/env python3
"""LDC Panel Development Server"""
import os
import sys
import argparse
import subprocess
from pathlib import Path


def main():
    # Define root_dir first
    root_dir = Path(__file__).parent.resolve()

    # Load configuration
    import yaml
    config_file = root_dir / "config.yaml"
    default_config = {"port": 8000, "host": "127.0.0.1"}
    
    if not config_file.exists():
        try:
            with open(config_file, "w") as f:
                yaml.dump(default_config, f)
            print(f"Created default configuration: {config_file}")
            config = default_config
        except Exception as e:
            print(f"Warning: Could not create config file: {e}")
            config = default_config
    else:
        try:
            with open(config_file, "r") as f:
                config = yaml.safe_load(f) or {}
                # Merge with defaults to ensure all keys exist
                config = {**default_config, **config}
        except Exception as e:
            print(f"Warning: Could not read config file: {e}")
            config = default_config
            
    parser = argparse.ArgumentParser(description="LDC Panel Development Server")
    parser.add_argument("--host", default=config.get("host", "127.0.0.1"), help=f"Host to bind (default: {config.get('host', '127.0.0.1')})")
    parser.add_argument("--port", "-p", type=int, default=config.get("port", 8000), help=f"Port to bind (default: {config.get('port', 8000)})")
    parser.add_argument("--reload", "-r", action="store_true", help="Enable auto-reload")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    
    # Check if we should use venv
    # root_dir is already defined at the top
    backend_dir = root_dir / "backend"
    venv_dir = backend_dir / ".venv"
    
    # Basic check: if we are not in the venv, and venv exists, try to re-exec
    # Detection: sys.prefix check
    try:
        # Resolve paths to handle potential casing/symlink differences
        in_venv = (Path(sys.prefix).resolve() == venv_dir.resolve()) or (sys.base_prefix != sys.prefix)
    except Exception:
        in_venv = (sys.prefix == str(venv_dir)) or (sys.base_prefix != sys.prefix)
    
    if not in_venv and venv_dir.exists():
        if os.name == 'nt':
            venv_python = venv_dir / "Scripts" / "python.exe"
        else:
            venv_python = venv_dir / "bin" / "python"
        
        if venv_python.exists():
            print(f"  → Switching to virtual environment: {venv_python}")
            # Re-execute with the same arguments
            try:
                subprocess.run([str(venv_python), __file__] + sys.argv[1:], check=True)
                sys.exit(0)
            except KeyboardInterrupt:
                sys.exit(0)
            except subprocess.CalledProcessError as e:
                sys.exit(e.returncode)
            except Exception as e:
                print(f"Error switching to venv: {e}")
                # Continue and try normal execution (will likely fail)

    # Set environment
    if args.debug:
        os.environ["LDC_DEBUG"] = "true"
    
    # Ensure we're in the backend directory
    os.chdir(backend_dir)
    
    # Add backend to path
    sys.path.insert(0, str(backend_dir))
    
    print("=" * 50)
    print("LDC Panel Development Server")
    print("=" * 50)
    print(f"  Host: {args.host}")
    print(f"  Port: {args.port}")
    print(f"  Reload: {args.reload}")
    print(f"  Debug: {args.debug}")
    print("=" * 50)
    print(f"\n  → http://{args.host}:{args.port}")
    print(f"  → http://{args.host}:{args.port}/docs (Swagger UI)")
    print("\n  Press Ctrl+C to stop\n")
    
    # Check if port is already in use
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((args.host, args.port))
        sock.close()
    except OSError:
        print(f"\n  ✗ ОШИБКА: Порт {args.port} уже занят!")
        print(f"    Возможно, сервер уже запущен.")
        print(f"    Используйте другой порт: python run.py -p {args.port + 1}\n")
        sys.exit(1)
    
    try:
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level="info",
            access_log=True,
            use_colors=False,
        )
    except ImportError:
        print("Error: uvicorn not installed")
        print("Run: pip install uvicorn[standard]")
        print("Or ensure the virtual environment is created: python install.py")
        sys.exit(1)
    except KeyboardInterrupt:
        pass
    
    print("\nОстановлено пользователем.")


if __name__ == "__main__":
    main()
