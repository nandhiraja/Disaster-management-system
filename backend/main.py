from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from routers import sos, responders, missions, dashboard, strategic, admin, area_reports

app = FastAPI(
    title="Disaster Management System",
    description="5-Layer Flood Disaster Response Platform",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "null"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# ── Startup ───────────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    init_db()
    print("🚨 Disaster Management System v3 running on http://localhost:8000")
    print("📄 API Docs: http://localhost:8000/docs")

# ── Health ────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def health():
    return {"status": "running", "system": "Disaster Management Platform v3", "version": "3.0.0"}

# ── Routers ───────────────────────────────────────────────────────
app.include_router(sos.router,          prefix="/api/sos",          tags=["Layer 1 – SOS"])
app.include_router(responders.router,   prefix="/api/responders",   tags=["Layer 2 – Responders"])
app.include_router(missions.router,     prefix="/api/missions",     tags=["Layer 3 – Missions"])
app.include_router(dashboard.router,    prefix="/api/dashboard",    tags=["Layer 4 – Command Dashboard"])
app.include_router(strategic.router,    prefix="/api/strategic",    tags=["Layer 5 – Strategic"])
app.include_router(admin.router,        prefix="/api/admin",        tags=["Admin"])
app.include_router(area_reports.router, prefix="/api/area-reports", tags=["Area Reports"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

