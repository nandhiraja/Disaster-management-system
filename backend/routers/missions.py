import uuid
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from database import get_db
from services.matcher import find_best_responder, get_top_candidates

router = APIRouter()


class MissionCreate(BaseModel):
    sos_id: str
    mission_type: Optional[str] = None


class MissionAssign(BaseModel):
    responder_id: str


class MissionStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None
    people_rescued: Optional[int] = None


class BackupRequest(BaseModel):
    request_type: str   # boat / medical / fire / evacuation / logistics
    message: Optional[str] = None


@router.post("/create")
def create_mission(data: MissionCreate):
    """Step 1: Create a mission for an SOS (does not yet assign a responder)."""
    conn = get_db()
    sos = conn.execute("SELECT * FROM sos_requests WHERE sos_id=?", (data.sos_id,)).fetchone()
    if not sos:
        conn.close()
        raise HTTPException(status_code=404, detail="SOS not found")
    if sos["status"] in ("rescued", "closed"):
        conn.close()
        raise HTTPException(status_code=400, detail="SOS is already resolved")

    mission_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    mtype = data.mission_type or sos["emergency_type"] + " rescue"

    conn.execute("""
        INSERT INTO missions (id, sos_id, responder_id, type, status, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?)
    """, (mission_id, data.sos_id, None, mtype, "created", now, now))
    conn.execute("UPDATE sos_requests SET status='assigned', assigned_mission=?, updated_at=? WHERE sos_id=?",
                 (mission_id, now, data.sos_id))
    conn.commit()
    conn.close()
    return {"mission_id": mission_id, "status": "created", "message": "Mission created. Now assign a responder."}


@router.post("/{mission_id}/assign")
def assign_responder(mission_id: str, data: MissionAssign):
    """Step 2: Assign a responder to an existing mission."""
    conn = get_db()
    mission = conn.execute("SELECT * FROM missions WHERE id=?", (mission_id,)).fetchone()
    if not mission:
        conn.close()
        raise HTTPException(status_code=404, detail="Mission not found")

    responder = conn.execute("SELECT * FROM responders WHERE id=? AND status='available'",
                             (data.responder_id,)).fetchone()
    if not responder:
        conn.close()
        raise HTTPException(status_code=400, detail="Responder not found or not available")

    now = datetime.utcnow().isoformat()
    conn.execute("UPDATE missions SET responder_id=?, status='assigned', assigned_at=?, updated_at=? WHERE id=?",
                 (data.responder_id, now, now, mission_id))
    conn.execute("UPDATE responders SET status='busy', updated_at=? WHERE id=?", (now, data.responder_id))
    conn.commit()
    conn.close()
    return {"message": "Responder assigned", "responder": dict(responder)}


@router.post("/auto-assign")
def auto_assign(data: MissionCreate):
    """Create mission AND auto-match the best responder in one step."""
    conn = get_db()
    sos = conn.execute("SELECT * FROM sos_requests WHERE sos_id=?", (data.sos_id,)).fetchone()
    if not sos:
        conn.close()
        raise HTTPException(status_code=404, detail="SOS not found")

    best = find_best_responder(sos["emergency_type"], sos["lat"] or 13.08, sos["lon"] or 80.27)
    if not best:
        conn.close()
        raise HTTPException(status_code=503, detail="No available responder found nearby")

    mission_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    mtype = data.mission_type or sos["emergency_type"] + " rescue"

    conn.execute("""
        INSERT INTO missions (id, sos_id, responder_id, type, status, created_at, assigned_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?)
    """, (mission_id, data.sos_id, best["id"], mtype, "assigned", now, now, now))
    conn.execute("UPDATE sos_requests SET status='assigned', assigned_mission=?, updated_at=? WHERE sos_id=?",
                 (mission_id, now, data.sos_id))
    conn.execute("UPDATE responders SET status='busy', updated_at=? WHERE id=?", (now, best["id"]))
    conn.commit()
    conn.close()
    return {"mission_id": mission_id, "assigned_responder": best, "status": "assigned"}


@router.get("/candidates")
def get_candidates(sos_id: str):
    """Get top 3 best-matched responders for manual selection."""
    conn = get_db()
    sos = conn.execute("SELECT * FROM sos_requests WHERE sos_id=?", (sos_id,)).fetchone()
    conn.close()
    if not sos:
        raise HTTPException(status_code=404, detail="SOS not found")
    candidates = get_top_candidates(sos["emergency_type"], sos["lat"] or 13.08, sos["lon"] or 80.27)
    return {"candidates": candidates, "sos": dict(sos)}


@router.get("")
def get_all_missions(status: Optional[str] = None):
    conn = get_db()
    if status:
        rows = conn.execute("""
            SELECT m.*, s.emergency_type, s.people_count, s.lat as sos_lat, s.lon as sos_lon,
                   s.priority_score, r.name as responder_name, r.type as responder_type, r.phone as responder_phone
            FROM missions m
            LEFT JOIN sos_requests s ON m.sos_id = s.sos_id
            LEFT JOIN responders r   ON m.responder_id = r.id
            WHERE m.status=? ORDER BY m.created_at DESC
        """, (status,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT m.*, s.emergency_type, s.people_count, s.lat as sos_lat, s.lon as sos_lon,
                   s.priority_score, r.name as responder_name, r.type as responder_type, r.phone as responder_phone
            FROM missions m
            LEFT JOIN sos_requests s ON m.sos_id = s.sos_id
            LEFT JOIN responders r   ON m.responder_id = r.id
            ORDER BY m.created_at DESC
        """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/my-assignments/{responder_id}")
def my_assignments(responder_id: str):
    """Volunteer app: get all missions assigned to this responder."""
    conn = get_db()
    rows = conn.execute("""
        SELECT m.*, s.emergency_type, s.people_count, s.lat as sos_lat, s.lon as sos_lon,
               s.approx_loc, s.phone as sos_phone, s.priority_score
        FROM missions m
        LEFT JOIN sos_requests s ON m.sos_id = s.sos_id
        WHERE m.responder_id=? AND m.status NOT IN ('completed','cancelled')
        ORDER BY m.created_at DESC
    """, (responder_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.put("/{mission_id}/accept")
def accept_mission(mission_id: str):
    """Volunteer accepts a mission → status becomes en_route."""
    conn = get_db()
    mission = conn.execute("SELECT * FROM missions WHERE id=?", (mission_id,)).fetchone()
    if not mission:
        conn.close()
        raise HTTPException(status_code=404, detail="Mission not found")
    if mission["status"] not in ("assigned", "created"):
        conn.close()
        raise HTTPException(status_code=400, detail=f"Cannot accept mission in status: {mission['status']}")
    now = datetime.utcnow().isoformat()
    conn.execute("UPDATE missions SET status='en_route', updated_at=? WHERE id=?", (now, mission_id))
    conn.execute("UPDATE sos_requests SET status='in_progress', updated_at=? WHERE sos_id=?",
                 (now, mission["sos_id"]))
    conn.commit()
    conn.close()
    return {"message": "Mission accepted – en route!", "status": "en_route"}


@router.put("/{mission_id}/status")
def update_mission_status(mission_id: str, data: MissionStatusUpdate):
    valid = {"created", "assigned", "en_route", "on_site", "rescue_in_progress", "completed", "cancelled"}
    if data.status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Choose from: {valid}")

    conn = get_db()
    mission = conn.execute("SELECT * FROM missions WHERE id=?", (mission_id,)).fetchone()
    if not mission:
        conn.close()
        raise HTTPException(status_code=404, detail="Mission not found")

    now = datetime.utcnow().isoformat()
    completed_at = now if data.status == "completed" else mission["completed_at"]

    conn.execute("""
        UPDATE missions SET status=?, notes=?, people_rescued=?, completed_at=?, updated_at=?
        WHERE id=?
    """, (data.status,
          data.notes or mission["notes"],
          data.people_rescued if data.people_rescued is not None else mission["people_rescued"],
          completed_at, now, mission_id))

    # When completed, free the responder and update SOS
    if data.status == "completed":
        conn.execute("UPDATE responders SET status='available', updated_at=? WHERE id=?",
                     (now, mission["responder_id"]))
        conn.execute("UPDATE sos_requests SET status='rescued', updated_at=? WHERE sos_id=?",
                     (now, mission["sos_id"]))

    conn.commit()
    conn.close()
    return {"message": "Mission status updated", "status": data.status}


@router.post("/{mission_id}/request-backup")
def request_backup(mission_id: str, data: BackupRequest):
    """Volunteer requests additional help during a mission."""
    valid_types = {"boat","medical","fire","evacuation","logistics"}
    if data.request_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid request_type. Use: {sorted(valid_types)}")

    conn = get_db()
    mission = conn.execute("SELECT * FROM missions WHERE id=?", (mission_id,)).fetchone()
    if not mission:
        conn.close()
        raise HTTPException(status_code=404, detail="Mission not found")

    now = datetime.utcnow().isoformat()
    req_id = str(uuid.uuid4())
    conn.execute("""
        INSERT INTO support_requests (id,mission_id,responder_id,request_type,message,status,created_at,updated_at)
        VALUES (?,?,?,?,?,?,?,?)
    """, (req_id, mission_id, mission["responder_id"], data.request_type, data.message, "pending", now, now))
    conn.execute("UPDATE missions SET backup_requested=1, updated_at=? WHERE id=?", (now, mission_id))

    # Auto-create alert for commander
    from services.matcher import find_best_responder as _fbr
    conn.execute("INSERT INTO alerts VALUES (?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), "backup",
         f"🆘 Backup requested: {data.request_type.upper()} needed – {data.message or 'No details'}",
         "critical", "Commander", 0, now))

    conn.commit(); conn.close()
    return {"support_request_id": req_id, "message": "Backup requested. Commander has been alerted."}


@router.get("/support-requests")
def get_support_requests(status: Optional[str] = None):
    """Commander: get all open backup requests."""
    conn = get_db()
    q = """
        SELECT sr.*, m.type as mission_type, r.name as responder_name, r.phone as responder_phone
        FROM support_requests sr
        LEFT JOIN missions m ON sr.mission_id = m.id
        LEFT JOIN responders r ON sr.responder_id = r.id
        WHERE 1=1
    """
    params = []
    if status:
        q += " AND sr.status=?"; params.append(status)
    q += " ORDER BY sr.created_at DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.put("/support-requests/{req_id}/dispatch")
def dispatch_backup(req_id: str):
    """Commander dispatches response to a backup request."""
    conn = get_db()
    now = datetime.utcnow().isoformat()
    result = conn.execute(
        "UPDATE support_requests SET status='dispatched', updated_at=? WHERE id=?", (now, req_id)
    )
    conn.commit(); conn.close()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Support request not found")
    return {"message": "Backup dispatched"}
