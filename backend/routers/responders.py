import uuid
import json
import math
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from database import get_db

router = APIRouter()

VALID_TYPES = {"boat","medical","volunteer","ambulance","helicopter","logistics","fire"}
VALID_TIERS = {"government","ngo","certified_volunteer","local_volunteer"}
TRUST_BY_TIER = {"government":100,"ngo":80,"certified_volunteer":60,"local_volunteer":40}


class ResponderAdd(BaseModel):
    name: str
    type: str
    tier: str = "local_volunteer"
    phone: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    gps_accuracy: Optional[float] = None
    district: str = "Chennai"
    skills: Optional[List[str]] = []
    equipment: Optional[List[str]] = []
    vehicle_type: Optional[str] = None
    # Extended fields from devdoc.md
    department: Optional[str] = None
    team_leader_name: Optional[str] = None
    team_size: Optional[int] = 1
    operating_radius: Optional[float] = 10.0
    registration_number: Optional[str] = None
    metadata: Optional[dict] = {}


class StatusUpdate(BaseModel):
    status: str


class LocationUpdate(BaseModel):
    lat: float
    lon: float
    accuracy: Optional[float] = None


class VerifyUpdate(BaseModel):
    verification_status: str   # approved | rejected


# ── Helpers ──────────────────────────────────────────────────────
def haversine_km(lat1, lon1, lat2, lon2):
    """Straight-line distance between two GPS points in km."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


# ── Endpoints ────────────────────────────────────────────────────

@router.get("")
def get_all_responders(status: Optional[str] = None, type: Optional[str] = None, tier: Optional[str] = None):
    conn = get_db()
    query = "SELECT * FROM responders WHERE 1=1"
    params = []
    if status:
        query += " AND status=?"; params.append(status)
    if type:
        query += " AND type=?";   params.append(type)
    if tier:
        query += " AND tier=?";   params.append(tier)
    query += " ORDER BY trust_score DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/by-phone/{phone}")
def get_by_phone(phone: str):
    """Volunteer login: look up responder by phone number."""
    conn = get_db()
    row = conn.execute("SELECT * FROM responders WHERE phone=?", (phone,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="No volunteer found with this phone number")
    return dict(row)


@router.post("/login")
def login_responder(data: dict):
    """Simplified login for volunteer app using phone number."""
    phone = data.get("phone")
    if not phone:
        raise HTTPException(status_code=400, detail="Phone number required")
    
    conn = get_db()
    row = conn.execute("SELECT * FROM responders WHERE phone=?", (phone,)).fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Volunteer not found")
    
    return dict(row)


@router.get("/nearby")
def get_nearby(
    lat: float = Query(..., description="Center latitude"),
    lon: float = Query(..., description="Center longitude"),
    radius_km: float = Query(10.0, description="Search radius in km"),
    status: str = Query("available"),
    type: Optional[str] = Query(None)
):
    """Return responders within radius_km of (lat, lon), sorted by distance then trust_score."""
    conn = get_db()
    q = "SELECT * FROM responders WHERE status=? AND verification_status='approved'"
    params: list = [status]
    if type:
        q += " AND type=?"; params.append(type)
    rows = conn.execute(q, params).fetchall()
    conn.close()

    results = []
    for r in rows:
        if r["lat"] is None or r["lon"] is None:
            continue
        dist = haversine_km(lat, lon, r["lat"], r["lon"])
        if dist <= radius_km:
            d = dict(r)
            d["distance_km"] = round(dist, 2)
            # Composite score: trust + proximity bonus
            d["assignment_score"] = round(r["trust_score"] + max(0, (radius_km - dist) / radius_km * 40), 1)
            results.append(d)

    results.sort(key=lambda x: (-x["assignment_score"], x["distance_km"]))
    return results


@router.post("/add")
def add_responder(data: ResponderAdd):
    if not data.name:
        raise HTTPException(status_code=400, detail="Name is required")
    if data.type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid type. Choose from: {sorted(VALID_TYPES)}")
    if data.tier not in VALID_TIERS:
        raise HTTPException(status_code=400, detail=f"Invalid tier. Choose from: {sorted(VALID_TIERS)}")

    trust_score = TRUST_BY_TIER[data.tier]
    rid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    try:
        conn = get_db()
        conn.execute("""
            INSERT INTO responders
            (id,name,type,tier,trust_score,skills,equipment,vehicle_type,lat,lon,gps_accuracy,phone,status,verification_status,district,last_seen,created_at,updated_at,
             department, team_leader_name, team_size, operating_radius, registration_number, metadata)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (rid, data.name, data.type, data.tier, trust_score,
              json.dumps(data.skills or []), json.dumps(data.equipment or []),
              data.vehicle_type, data.lat, data.lon, data.gps_accuracy,
              data.phone, "available",
              "approved" if data.tier == "local_volunteer" else "pending",
              data.district, now, now, now,
              data.department, data.team_leader_name, data.team_size, data.operating_radius, data.registration_number, json.dumps(data.metadata or {})))
        conn.commit()
    except Exception as e:
        if "conn" in locals(): conn.close()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if "conn" in locals(): conn.close()
        
    return {
        "id": rid,
        "tier": data.tier,
        "trust_score": trust_score,
        "verification_status": "approved" if data.tier == "local_volunteer" else "pending",
        "message": "Registered successfully"
    }


@router.put("/{responder_id}/status")
def update_status(responder_id: str, data: StatusUpdate):
    valid = {"available","busy","offline"}
    if data.status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status")
    conn = get_db()
    now = datetime.utcnow().isoformat()
    result = conn.execute(
        "UPDATE responders SET status=?, updated_at=? WHERE id=?",
        (data.status, now, responder_id)
    )
    conn.commit(); conn.close()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Responder not found")
    return {"message": "Status updated"}


@router.put("/{responder_id}/location")
def update_location(responder_id: str, data: LocationUpdate):
    """Responder app continuously sends live GPS. Stores accuracy too."""
    conn = get_db()
    now = datetime.utcnow().isoformat()
    result = conn.execute(
        "UPDATE responders SET lat=?, lon=?, gps_accuracy=?, last_seen=?, updated_at=? WHERE id=?",
        (data.lat, data.lon, data.accuracy, now, now, responder_id)
    )
    conn.commit(); conn.close()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Responder not found")
    return {"message": "Location updated", "lat": data.lat, "lon": data.lon, "accuracy": data.accuracy}


@router.put("/{responder_id}/verify")
def verify_responder(responder_id: str, data: VerifyUpdate):
    """Admin approves or rejects a pending volunteer."""
    if data.verification_status not in ("approved","rejected"):
        raise HTTPException(status_code=400, detail="Use 'approved' or 'rejected'")
    conn = get_db()
    now = datetime.utcnow().isoformat()
    result = conn.execute(
        "UPDATE responders SET verification_status=?, updated_at=? WHERE id=?",
        (data.verification_status, now, responder_id)
    )
    conn.commit(); conn.close()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Responder not found")
    return {"message": f"Responder {data.verification_status}"}


@router.get("/summary")
def get_summary():
    conn = get_db()
    rows = conn.execute("""
        SELECT type,
               SUM(CASE WHEN status='available' THEN 1 ELSE 0 END) as available,
               SUM(CASE WHEN status='busy'      THEN 1 ELSE 0 END) as busy,
               SUM(CASE WHEN status='offline'   THEN 1 ELSE 0 END) as offline,
               COUNT(*) as total
        FROM responders GROUP BY type
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/{responder_id}")
def get_responder(responder_id: str):
    conn = get_db()
    row = conn.execute("SELECT * FROM responders WHERE id=?", (responder_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Responder not found")
    return dict(row)
