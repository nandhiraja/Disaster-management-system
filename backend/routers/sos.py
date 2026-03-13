import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import get_db

router = APIRouter()


class SOSCreate(BaseModel):
    source_type: str = "app"
    phone: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    approx_loc: Optional[str] = None
    people_count: int = 1
    emergency_type: str = "unknown"


class SOSStatusUpdate(BaseModel):
    status: str


def calc_triage(emergency_type: str, people_count: int) -> tuple:
    """Returns (priority_score, triage_level where 1=Critical, 4=Low)."""
    score = 0
    triage = 4
    
    # Priority Score Logic
    if emergency_type == "medical": score += 50
    elif emergency_type == "flood": score += 30
    elif emergency_type == "trapped": score += 40
    elif emergency_type == "elderly": score += 35
    
    if people_count >= 10: score += 40
    elif people_count >= 5: score += 25
    elif people_count >= 2: score += 10
    
    # Triage Level Logic
    if score >= 80 or emergency_type == "medical": triage = 1
    elif score >= 60: triage = 2
    elif score >= 40: triage = 3
    else: triage = 4
    
    return score, triage


def _is_duplicate(phone: str, lat: float, lon: float, conn) -> bool:
    """Detect duplicate SOS: same phone + location within 5 minutes."""
    if not phone or lat is None or lon is None:
        return False
    cutoff = (datetime.utcnow() - timedelta(minutes=5)).isoformat()
    existing = conn.execute(
        "SELECT lat, lon FROM sos_requests WHERE phone=? AND created_at > ? AND status != 'closed'",
        (phone, cutoff)
    ).fetchall()
    for row in existing:
        import math
        dist = math.sqrt((row["lat"] - lat) ** 2 + (row["lon"] - lon) ** 2)
        if dist < 0.005:  # ~500m tolerance in degrees
            return True
    return False


@router.post("/create")
def create_sos(data: SOSCreate):
    conn = get_db()
    try:
        if _is_duplicate(data.phone, data.lat, data.lon, conn):
            conn.close()
            raise HTTPException(status_code=409, detail="Duplicate SOS detected within 5 minutes from same location")

        sos_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        priority, triage = calc_triage(data.emergency_type, data.people_count)

        conn.execute("""
            INSERT INTO sos_requests
            (sos_id, source_type, phone, lat, lon, approx_loc, people_count,
             emergency_type, status, priority_score, triage_level, verification_status, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (sos_id, data.source_type, data.phone, data.lat, data.lon,
              data.approx_loc or f"{data.lat},{data.lon}", data.people_count,
              data.emergency_type, "pending", priority, triage, "unverified", now, now))
        conn.commit()
        return {"sos_id": sos_id, "priority_score": priority, "triage_level": triage, "status": "pending"}
    finally:
        conn.close()


@router.get("")
@router.get("/all")
def get_all_sos(status: Optional[str] = None, limit: int = 100):
    conn = get_db()
    if status:
        rows = conn.execute(
            "SELECT * FROM sos_requests WHERE status=? ORDER BY priority_score DESC LIMIT ?",
            (status, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM sos_requests ORDER BY priority_score DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/nearby")
def get_nearby_sos(lat: float, lon: float, radius_km: float = 10.0):
    from services.matcher import haversine
    conn = get_db()
    rows = conn.execute("SELECT * FROM sos_requests WHERE status NOT IN ('rescued','closed')").fetchall()
    conn.close()
    result = []
    for r in rows:
        if r["lat"] and r["lon"]:
            dist = haversine(lat, lon, r["lat"], r["lon"])
            if dist <= radius_km:
                d = dict(r)
                d["distance_km"] = round(dist, 2)
                result.append(d)
    result.sort(key=lambda x: x["priority_score"], reverse=True)
    return result


@router.put("/{sos_id}/verify")
def verify_sos(sos_id: str, status: str):
    """Professional triage: mark as verified or rejected."""
    if status not in ["verified", "rejected"]:
        raise HTTPException(status_code=400, detail="Invalid verification status")
    conn = get_db()
    conn.execute("UPDATE sos_requests SET verification_status=?, updated_at=? WHERE sos_id=?", 
                (status, datetime.utcnow().isoformat(), sos_id))
    conn.commit()
    conn.close()
    return {"status": status}

@router.put("/{sos_id}/update-status")
def update_sos_status(sos_id: str, data: SOSStatusUpdate):
    valid = {"pending", "assigned", "in_progress", "rescued", "closed"}
    if data.status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Choose from: {valid}")
    conn = get_db()
    
    # NEW: Log to audit
    conn.execute("""
        INSERT INTO audit_logs (id, action, target_id, details, created_at)
        VALUES (?,?,?,?,?)
    """, (str(uuid.uuid4()), "SOS_STATUS_CHANGE", sos_id, f"to {data.status}", datetime.utcnow().isoformat()))
    
    result = conn.execute(
        "UPDATE sos_requests SET status=?, updated_at=? WHERE sos_id=?",
        (data.status, datetime.utcnow().isoformat(), sos_id)
    )
    conn.commit()
    conn.close()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="SOS not found")
    return {"message": "Status updated", "status": data.status}
