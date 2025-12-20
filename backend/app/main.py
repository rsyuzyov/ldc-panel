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
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Adjust path to point to frontend/dist relative to backend/app/main.py
# backend/app/main.py -> backend/ -> repo/ -> frontend/dist
frontend_dir = "../frontend/dist"

if os.path.exists(frontend_dir):
    app.mount("/assets", StaticFiles(directory=f"{frontend_dir}/assets"), name="assets")
    
    # SPA Fallback
    @app.get("/{full_path:path}")
    async def catch_all(full_path: str):
        # Allow API routes to pass through (though they should match above)
        if full_path.startswith("api/"):
             return {"error": "Not Found"}
        
        # Serve index.html for everything else (SPA routing)
        return FileResponse(f"{frontend_dir}/index.html")
else:
    print(f"Warning: Frontend directory {frontend_dir} not found. Frontend will not be served.")
