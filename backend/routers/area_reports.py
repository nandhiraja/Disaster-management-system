import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import get_db

router = APIRouter()


class AreaReportCreate(BaseModel):
    responder_id: str
    lat: float
    lon: float
    condition: Optional[str] = None
    water_level: str = "none"          # none/ankle/knee/waist/chest/extreme
    road_blocked: bool = False
    fire_detected: bool = False
    building_damage: str = "none"      # none/partial/severe
    boat_needed: bool = False
    notes: Optional[str] = None
    district: str = "Chennai"


@router.post("")
def create_area_report(data: AreaReportCreate):
    valid_wl = {"none","ankle","knee","waist","chest","extreme"}
    valid_bd = {"none","partial","severe"}
    if data.water_level not in valid_wl:
        raise HTTPException(status_code=400, detail=f"water_level must be one of {sorted(valid_wl)}")
    if data.building_damage not in valid_bd:
        raise HTTPException(status_code=400, detail=f"building_damage must be one of {sorted(valid_bd)}")

    conn = get_db()
    rid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    conn.execute("""
        INSERT INTO area_reports
        (id,responder_id,lat,lon,condition,water_level,road_blocked,fire_detected,building_damage,boat_needed,notes,district,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (rid, data.responder_id, data.lat, data.lon, data.condition, data.water_level,
          int(data.road_blocked), int(data.fire_detected), data.building_damage,
          int(data.boat_needed), data.notes, data.district, now))

    # Auto-generate alert for extreme conditions
    if data.water_level in ("chest","extreme") or data.fire_detected or data.building_damage == "severe":
        conn.execute("INSERT INTO alerts VALUES (?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), "area",
             f"⚠️ Severe conditions reported: {data.water_level} water, fire={data.fire_detected}, damage={data.building_damage}. Location: {data.lat:.4f},{data.lon:.4f}",
             "critical", data.district, 0, now))

    conn.commit()
    conn.close()
    return {"id": rid, "message": "Area report submitted"}


@router.get("")
def get_area_reports(district: Optional[str] = None, limit: int = 50):
    conn = get_db()
    q = "SELECT * FROM area_reports WHERE 1=1"
    params = []
    if district:
        q += " AND district=?"; params.append(district)
    q += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]
