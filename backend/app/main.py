"""LDC Panel - Linux DC Panel Backend"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, servers, users, computers, groups, dns, dhcp, gpo, backup, logs

app = FastAPI(
    title="LDC Panel",
    description="Linux DC Panel - веб-панель администрирования Samba AD DC",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(servers.router)
app.include_router(users.router)
app.include_router(computers.router)
app.include_router(groups.router)
app.include_router(dns.router)
app.include_router(dhcp.router)
app.include_router(gpo.router)
app.include_router(backup.router)
app.include_router(logs.router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


# Mount static files (Frontend)
import os
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Get absolute path to project root
# backend/app/main.py -> backend/app -> backend -> project_root
BASE_DIR = Path(__file__).resolve().parent.parent.parent
frontend_dir = BASE_DIR / "frontend" / "dist"

if frontend_dir.exists():
    # Mount assets folder
    assets_dir = frontend_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    
    # SPA Fallback and root static files
    @app.get("/{full_path:path}")
    async def catch_all(full_path: str):
        # Allow API routes to pass through (though they should match above)
        if full_path.startswith("api/"):
             return {"error": "Not Found"}
        
        # Check if requested file exists in frontend_dir (e.g., favicon.svg)
        file_path = frontend_dir / full_path
        if full_path and file_path.is_file():
            return FileResponse(str(file_path))
            
        # Serve index.html for everything else (SPA routing)
        return FileResponse(str(frontend_dir / "index.html"))
else:
    print(f"Warning: Frontend directory {frontend_dir} not found. Frontend will not be served.")
