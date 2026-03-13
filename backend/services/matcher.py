"""
Matching Engine – backend/services/matcher.py

Finds the best available responder for a given SOS request.
Scoring formula:
    score = (1 / distance_km) * 40 + trust_level * 5
Higher score = better match.
"""
import math
from database import get_db

BOAT_NEEDED_WATER_LEVELS = {"waist", "chest", "extreme"}


def haversine(lat1, lon1, lat2, lon2) -> float:
    """Return distance in kilometres between two GPS points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _area_requires_boat(lat: float, lon: float, radius_km: float = 1.5) -> bool:
    """Check area_reports near the SOS location to see if boat is required."""
    conn = get_db()
    reports = conn.execute("SELECT lat, lon, water_level, boat_needed FROM area_reports").fetchall()
    conn.close()
    for r in reports:
        dist = haversine(lat, lon, r["lat"], r["lon"])
        if dist <= radius_km and r["boat_needed"] == 1:
            return True
        if dist <= radius_km and r["water_level"] in BOAT_NEEDED_WATER_LEVELS:
            return True
    return False


def _get_capability_weight(emergency_type: str, responder_type: str) -> float:
    """
    Returns a weight (0.0 to 1.0) representing how suitable a responder type is for an emergency.
    This allows for fallback logic (greedy matching).
    """
    weights = {
        "medical": {"medical": 1.0, "ambulance": 0.9, "volunteer": 0.5, "logistics": 0.4, "boat": 0.2, "helicopter": 0.8},
        "trapped": {"boat": 1.0, "helicopter": 0.9, "volunteer": 0.7, "logistics": 0.5},
        "flood": {"boat": 1.0, "volunteer": 0.6, "logistics": 0.5, "helicopter": 0.8},
        "elderly": {"medical": 1.0, "ambulance": 0.9, "volunteer": 0.7},
        "fire": {"fire": 1.0, "volunteer": 0.4},
        "unknown": {"volunteer": 0.8, "boat": 0.8, "medical": 0.8, "ambulance": 0.8, "helicopter": 0.8, "logistics": 0.8}
    }
    etype = emergency_type.lower()
    rtype = responder_type.lower()
    
    if etype in weights:
        return weights[etype].get(rtype, 0.1)
    return 0.5 # Default fallback

def calculate_score(responder: dict, sos_lat: float, sos_lon: float, emergency_type: str) -> tuple[float, float]:
    """Returns (score, distance_km). Score blends distance, trust, and capability."""
    res_lat = responder.get("lat")
    res_lon = responder.get("lon")
    
    # Handle missing location
    if res_lat is None or res_lon is None:
        return 0.0, 999.9
    
    dist = haversine(sos_lat, sos_lon, res_lat, res_lon)
    cap_weight = _get_capability_weight(emergency_type, responder["type"])
    trust = responder.get("trust_level", 50) / 100.0  # Normalize trust to 0-1
    
    # Distance factor: exponential decay or inverse. 
    # Use 1/(dist+1) to avoid division by zero and give high weight to close ones.
    dist_factor = 1.0 / (dist + 0.5) 
    
    # Final score: 60% distance/capability, 20% trust, 20% capability weight
    # This ensures we pick the closest suitable candidate
    score = (dist_factor * 50 * cap_weight) + (trust * 20) + (cap_weight * 30)
    
    return score, dist

def find_best_responder(emergency_type: str, lat: float, lon: float,
                         max_radius_km: float = 50.0) -> dict | None:
    """
    Return the best available responder dict using greedy scoring.
    """
    conn = get_db()
    candidates = conn.execute("SELECT * FROM responders WHERE status='available'").fetchall()
    conn.close()

    scored = []
    for r in candidates:
        score, dist = calculate_score(dict(r), lat, lon, emergency_type)
        if dist > max_radius_km:
            continue
        if score <= 0:
            continue
        scored.append((score, dist, dict(r)))

    if not scored:
        return None

    # Sort by Score descending
    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_dist, best = scored[0]
    
    best["distance_km"] = round(best_dist, 2)
    best["match_score"] = round(best_score, 2)
    
    # Special instructions for distant specialization fallbacks
    if emergency_type == "medical" and best["type"] not in ("medical", "ambulance"):
        best["special_instruction"] = "TRANSPORT TO NEAREST MEDICAL STAGING AREA"
        
    return best


def get_top_candidates(emergency_type: str, lat: float, lon: float,
                         top_n: int = 5) -> list[dict]:
    """Return top N candidates ranked by greedy score."""
    conn = get_db()
    candidates = conn.execute("SELECT * FROM responders WHERE status='available'").fetchall()
    conn.close()

    scored = []
    for r in candidates:
        score, dist = calculate_score(dict(r), lat, lon, emergency_type)
        d = dict(r)
        d["distance_km"] = round(dist, 2) if dist < 999 else 0.0
        d["match_score"] = round(score, 2)
        scored.append(d)

    scored.sort(key=lambda x: x["match_score"], reverse=True)
    return scored[:top_n]
