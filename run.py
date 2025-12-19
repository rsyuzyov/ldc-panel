#!/usr/bin/env python3
"""LDC Panel Development Server"""
import os
import sys
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="LDC Panel Development Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", "-p", type=int, default=8000, help="Port to bind (default: 8000)")
    parser.add_argument("--reload", "-r", action="store_true", help="Enable auto-reload")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    
    # Set environment
    if args.debug:
        os.environ["LDC_DEBUG"] = "true"
    
    # Ensure we're in the backend directory
    root_dir = Path(__file__).parent.resolve()
    backend_dir = root_dir / "backend"
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
    
    try:
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level="debug" if args.debug else "info",
        )
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
    except ImportError:
        print("Error: uvicorn not installed")
        print("Run: pip install uvicorn[standard]")
        sys.exit(1)


if __name__ == "__main__":
    main()
