from fastapi import APIRouter
from database import get_db

router = APIRouter()


@router.get("/summary")
def get_summary():
    conn = get_db()
    sos_total    = conn.execute("SELECT COUNT(*) FROM sos_requests").fetchone()[0]
    sos_active   = conn.execute("SELECT COUNT(*) FROM sos_requests WHERE status IN ('pending','assigned','in_progress')").fetchone()[0]
    sos_rescued  = conn.execute("SELECT COUNT(*) FROM sos_requests WHERE status='rescued'").fetchone()[0]
    sos_pending  = conn.execute("SELECT COUNT(*) FROM sos_requests WHERE status='pending'").fetchone()[0]
    missions_active = conn.execute("SELECT COUNT(*) FROM missions WHERE status NOT IN ('completed','cancelled')").fetchone()[0]
    resp_available  = conn.execute("SELECT COUNT(*) FROM responders WHERE status='available'").fetchone()[0]
    resp_busy       = conn.execute("SELECT COUNT(*) FROM responders WHERE status='busy'").fetchone()[0]
    shelters_over   = conn.execute("SELECT COUNT(*) FROM shelters WHERE occupancy >= capacity").fetchone()[0]
    conn.close()
    return {
        "sos_total": sos_total,
        "sos_active": sos_active,
        "sos_rescued": sos_rescued,
        "sos_pending": sos_pending,
        "missions_active": missions_active,
        "responders_available": resp_available,
        "responders_busy": resp_busy,
        "shelters_over_capacity": shelters_over,
    }


@router.get("/map-data")
def get_map_data():
    """All markers for the Leaflet map in one endpoint."""
    conn = get_db()
    sos_rows  = conn.execute(
        "SELECT sos_id, lat, lon, emergency_type, status, people_count, priority_score, created_at FROM sos_requests WHERE lat IS NOT NULL"
    ).fetchall()
    resp_rows = conn.execute(
        "SELECT id, name, type, lat, lon, status FROM responders WHERE lat IS NOT NULL"
    ).fetchall()
    shelter_rows = conn.execute(
        "SELECT id, name, lat, lon, capacity, occupancy, facilities FROM shelters"
    ).fetchall()
    report_rows = conn.execute(
        "SELECT id, lat, lon, condition, water_level, road_blocked FROM area_reports"
    ).fetchall()
    conn.close()

    def sos_colour(status):
        return {"pending": "red", "assigned": "orange", "in_progress": "yellow",
                "rescued": "green", "closed": "gray"}.get(status, "red")

    return {
        "sos": [{"id": r["sos_id"], "lat": r["lat"], "lon": r["lon"],
                 "type": r["emergency_type"], "status": r["status"],
                 "people": r["people_count"], "priority": r["priority_score"],
                 "color": sos_colour(r["status"]), "created_at": r["created_at"]} for r in sos_rows],
        "responders": [{"id": r["id"], "name": r["name"], "type": r["type"],
                        "lat": r["lat"], "lon": r["lon"], "status": r["status"]} for r in resp_rows],
        "shelters": [{"id": r["id"], "name": r["name"], "lat": r["lat"], "lon": r["lon"],
                      "capacity": r["capacity"], "occupancy": r["occupancy"],
                      "pct": round(r["occupancy"] / max(r["capacity"], 1) * 100, 1),
                      "facilities": r["facilities"]} for r in shelter_rows],
        "area_reports": [{"id": r["id"], "lat": r["lat"], "lon": r["lon"],
                          "condition": r["condition"], "water_level": r["water_level"],
                          "road_blocked": bool(r["road_blocked"])} for r in report_rows],
    }


@router.get("/alerts")
def get_alerts(dismissed: bool = False):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM alerts WHERE dismissed=? ORDER BY created_at DESC LIMIT 20",
        (1 if dismissed else 0,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.put("/alerts/{alert_id}/dismiss")
def dismiss_alert(alert_id: str):
    conn = get_db()
    conn.execute("UPDATE alerts SET dismissed=1 WHERE id=?", (alert_id,))
    conn.commit()
    conn.close()
    return {"message": "Alert dismissed"}


@router.get("/live")
def get_live_feed():
    """Polling endpoint – combines summary + recent SOS + active missions."""
    conn = get_db()
    recent_sos = conn.execute(
        "SELECT sos_id, emergency_type, status, people_count, priority_score, lat, lon, created_at FROM sos_requests ORDER BY created_at DESC LIMIT 10"
    ).fetchall()
    active_missions = conn.execute("""
        SELECT m.id, m.sos_id, m.status, m.type, r.name as responder_name, r.type as responder_type,
               s.emergency_type, s.people_count, s.lat, s.lon
        FROM missions m
        LEFT JOIN responders r ON m.responder_id = r.id
        LEFT JOIN sos_requests s ON m.sos_id = s.sos_id
        WHERE m.status NOT IN ('completed','cancelled')
        ORDER BY m.created_at DESC LIMIT 10
    """).fetchall()
    conn.close()
    return {
        "recent_sos": [dict(r) for r in recent_sos],
        "active_missions": [dict(r) for r in active_missions]
    }
