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
