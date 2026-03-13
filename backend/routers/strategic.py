from fastapi import APIRouter, Query
from database import get_db
from datetime import datetime
from typing import Optional

router = APIRouter()

# All 38 Tamil Nadu districts
TN_DISTRICTS = [
    "Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem",
    "Tirunelveli", "Vellore", "Erode", "Thoothukudi", "Thanjavur",
    "Dindigul", "Ranipet", "Karur", "Namakkal", "Krishnagiri",
    "Dharmapuri", "Villupuram", "Cuddalore", "Nagapattinam", "Tiruvarur",
    "Mayiladuthurai", "Ariyalur", "Perambalur", "Pudukkottai",
    "Sivaganga", "Virudhunagar", "Ramanathapuram", "Theni",
    "Nilgiris", "Tiruppur", "Kanchipuram", "Chengalpattu",
    "Kanyakumari",
    "Tiruvallur", "Kallakurichi", "Tirupattur", "Tenkasi",
    "Tiruvannamalai", "Vellore"
]


@router.get("/stats")
def get_stats():
    conn = get_db()
    total   = conn.execute("SELECT COUNT(*) FROM sos_requests").fetchone()[0]
    active  = conn.execute("SELECT COUNT(*) FROM sos_requests WHERE status IN ('pending','assigned','in_progress')").fetchone()[0]
    rescued = conn.execute("SELECT COUNT(*) FROM sos_requests WHERE status='rescued'").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM sos_requests WHERE status='pending'").fetchone()[0]
    responders = conn.execute("SELECT COUNT(*) FROM responders WHERE status='available'").fetchone()[0]
    
    missions_done = conn.execute("SELECT COUNT(*) FROM missions WHERE status='completed'").fetchone()[0]
    missions_all  = conn.execute("SELECT COUNT(*) FROM missions").fetchone()[0]
    success_rate  = round(missions_done / max(missions_all, 1) * 100, 1)
    conn.close()
    return {
        "total_sos": total,
        "active_sos": active,
        "rescued": rescued,
        "pending": pending,
        "responders_available": responders,
        "missions_completed": missions_done,
        "success_rate_pct": success_rate,
    }


@router.get("/by-region")
def by_region():
    conn = get_db()
    # Aggregate SOS by approximate district (using responder districts as proxy)
    rows = conn.execute("""
        SELECT r.district,
               COUNT(DISTINCT r.id) as total_responders,
               SUM(CASE WHEN r.status='available' THEN 1 ELSE 0 END) as available,
               SUM(CASE WHEN r.status='busy'      THEN 1 ELSE 0 END) as busy
        FROM responders r
        GROUP BY r.district
    """).fetchall()
    shelters = conn.execute(
        "SELECT district, COUNT(*) as count, SUM(capacity) as capacity, SUM(occupancy) as occupancy FROM shelters GROUP BY district"
    ).fetchall()
    shelter_map = {s["district"]: dict(s) for s in shelters}

    result = []
    for r in rows:
        d = dict(r)
        sh = shelter_map.get(r["district"], {})
        d["shelter_count"] = sh.get("count", 0)
        d["shelter_capacity"] = sh.get("capacity", 0)
        d["shelter_occupancy"] = sh.get("occupancy", 0)
        result.append(d)
    conn.close()
    return result


@router.get("/heatmap")
def get_heatmap():
    """Returns lat/lon + weight (priority_score) for Leaflet heatmap layer."""
    conn = get_db()
    rows = conn.execute(
        "SELECT lat, lon, priority_score FROM sos_requests WHERE lat IS NOT NULL AND status NOT IN ('rescued','closed')"
    ).fetchall()
    conn.close()
    return [{"lat": r["lat"], "lon": r["lon"], "weight": r["priority_score"]} for r in rows]


@router.get("/performance")
def get_performance():
    conn = get_db()
    # Average mission duration in minutes for completed missions
    completed = conn.execute(
        "SELECT created_at, completed_at FROM missions WHERE status='completed' AND completed_at IS NOT NULL"
    ).fetchall()
    durations = []
    for m in completed:
        try:
            start = datetime.fromisoformat(m["created_at"])
            end   = datetime.fromisoformat(m["completed_at"])
            dur   = (end - start).total_seconds() / 60
            durations.append(dur)
        except Exception:
            pass
    avg_time = round(sum(durations) / len(durations), 1) if durations else 0

    total_missions = conn.execute("SELECT COUNT(*) FROM missions").fetchone()[0]
    done_missions  = conn.execute("SELECT COUNT(*) FROM missions WHERE status='completed'").fetchone()[0]
    total_rescued  = conn.execute("SELECT SUM(people_rescued) FROM missions WHERE status='completed'").fetchone()[0] or 0
    conn.close()
    return {
        "avg_rescue_time_minutes": avg_time,
        "total_missions": total_missions,
        "completed_missions": done_missions,
        "success_rate_pct": round(done_missions / max(total_missions, 1) * 100, 1),
        "total_people_rescued": total_rescued,
    }


@router.get("/timeline")
def get_timeline():
    conn = get_db()
    sos_events = conn.execute(
        "SELECT 'SOS' as event_type, created_at as ts, emergency_type, status, people_count FROM sos_requests ORDER BY created_at DESC LIMIT 15"
    ).fetchall()
    mission_events = conn.execute(
        "SELECT 'MISSION' as event_type, created_at as ts, type, status, NULL as emergency_type, NULL as people_count FROM missions ORDER BY created_at DESC LIMIT 10"
    ).fetchall()

    events = []
    for r in list(sos_events) + list(mission_events):
        events.append(dict(r))
    events.sort(key=lambda x: x.get("ts") or "", reverse=True)
    conn.close()
    return events[:20]


@router.get("/districts")
def get_districts(district: Optional[str] = Query(None, description="Filter to a specific district")):
    """Per-district stats for Tamil Nadu authority dashboard."""
    conn = get_db()

    # Responders per district
    resp_rows = conn.execute("""
        SELECT district,
               COUNT(*) as total_responders,
               SUM(CASE WHEN status='available' THEN 1 ELSE 0 END) as available,
               SUM(CASE WHEN status='busy'      THEN 1 ELSE 0 END) as busy,
               SUM(CASE WHEN status='offline'   THEN 1 ELSE 0 END) as offline
        FROM responders GROUP BY district
    """).fetchall()
    resp_map = {r["district"]: dict(r) for r in resp_rows}

    # Shelters per district
    shelter_rows = conn.execute(
        "SELECT district, COUNT(*) as count, SUM(capacity) as capacity, SUM(occupancy) as occupancy FROM shelters GROUP BY district"
    ).fetchall()
    shelter_map = {s["district"]: dict(s) for s in shelter_rows}

    # Active SOS per district (approximate via nearby responder district — we store district only on responders,
    # so we also count any district-named SOS via approx_loc heuristic)
    sos_rows = conn.execute("""
        SELECT r.district, COUNT(DISTINCT m.sos_id) as active_missions
        FROM missions m
        JOIN responders r ON m.responder_id = r.id
        WHERE m.status NOT IN ('completed','cancelled')
        GROUP BY r.district
    """).fetchall()
    mission_map = {r["district"]: r["active_missions"] for r in sos_rows}

    # SOS counts seeded per district via approx_loc pattern
    sos_all = conn.execute("SELECT approx_loc, status, priority_score FROM sos_requests").fetchall()
    conn.close()

    # SOS intensity per district (using approx_loc)
    sos_dist_stats = {}
    for r in sos_all:
        loc = r["approx_loc"] or "Unknown"
        if loc not in sos_dist_stats:
            sos_dist_stats[loc] = {"total": 0, "open": 0}
        sos_dist_stats[loc]["total"] += 1
        if r["status"] in ("pending", "assigned", "in_progress"):
            sos_dist_stats[loc]["open"] += 1

    results = []
    districts_to_show = [district] if district else TN_DISTRICTS
    for dist in districts_to_show:
        resp = resp_map.get(dist, {})
        sh   = shelter_map.get(dist, {})
        active_missions = mission_map.get(dist, 0)
        total_r = resp.get("total_responders", 0)
        avail_r = resp.get("available", 0)
        sh_cap  = sh.get("capacity", 0)
        sh_occ  = sh.get("occupancy", 0)
        
        # SOS stats
        s_stats = sos_dist_stats.get(dist, {"total": 0, "open": 0})
        open_sos = s_stats["open"]

        # Utilization & Intensity
        util_pct = round((resp.get("busy", 0) / max(total_r, 1)) * 100, 1) if total_r > 0 else 0.0
        sos_intensity = round(open_sos / 5.0, 2) # Arbitrary normalization

        # Determine severity
        busy = resp.get("busy", 0)
        critical_shortage = False
        if open_sos > 0 and avail_r == 0:
            critical_shortage = True
            
        if critical_shortage or busy > 5 or (sh_cap > 0 and sh_occ / sh_cap > 0.9):
            severity = "critical"
        elif busy > 0 or active_missions > 0 or open_sos > 0:
            severity = "active"
        elif total_r > 0:
            severity = "standby"
        else:
            severity = "clear"

        results.append({
            "district": dist,
            "total_responders": total_r,
            "available_responders": avail_r,
            "busy_responders": busy,
            "active_missions": active_missions,
            "open_sos": open_sos,
            "utilization_pct": util_pct,
            "sos_intensity": sos_intensity,
            "critical_shortage": critical_shortage,
            "shelter_count": sh.get("count", 0),
            "shelter_capacity": sh_cap,
            "shelter_occupancy": sh_occ,
            "shelter_fill_pct": round(sh_occ / max(sh_cap, 1) * 100, 1),
            "severity": severity,
        })

    return results

@router.get("/districts/list")
def list_districts():
    """Return the full list of Tamil Nadu districts."""
    return TN_DISTRICTS
