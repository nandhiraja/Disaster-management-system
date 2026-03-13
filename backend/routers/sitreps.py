from fastapi import APIRouter, HTTPException
from database import get_db
from pydantic import BaseModel
from typing import List, Optional
import uuid
from datetime import datetime

router = APIRouter()

class SitrepCreate(BaseModel):
    responder_id: str
    mission_id: Optional[str] = None
    message: str
    lat: Optional[float] = None
    lon: Optional[float] = None

@router.post("/submit")
@router.post("/create")
def submit_sitrep(data: SitrepCreate):
    conn = get_db()
    sid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    conn.execute("""
        INSERT INTO sitreps (id, responder_id, mission_id, message, lat, lon, created_at)
        VALUES (?,?,?,?,?,?,?)
    """, (sid, data.responder_id, data.mission_id, data.message, data.lat, data.lon, now))
    
    # Also log to audit
    conn.execute("""
        INSERT INTO audit_logs (id, user_id, action, target_id, details, created_at)
        VALUES (?,?,?,?,?,?)
    """, (str(uuid.uuid4()), data.responder_id, "SITREP_SUBMIT", data.mission_id or "GENERAL", data.message[:50], now))
    
    conn.commit()
    conn.close()
    return {"id": sid, "status": "published"}

@router.get("/recent")
def get_recent_sitreps(limit: int = 50):
    conn = get_db()
    rows = conn.execute("""
        SELECT s.*, r.name as responder_name, r.type as responder_type 
        FROM sitreps s
        JOIN responders r ON s.responder_id = r.id
        ORDER BY s.created_at DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/my/{responder_id}")
def get_my_sitreps(responder_id: str, limit: int = 20):
    """Volunteer app: get history of reports by this specific responder."""
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM sitreps WHERE responder_id=? 
        ORDER BY created_at DESC LIMIT ?
    """, (responder_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
