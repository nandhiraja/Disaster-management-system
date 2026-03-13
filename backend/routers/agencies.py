from fastapi import APIRouter, HTTPException
from database import get_db
from pydantic import BaseModel
from typing import List, Optional
import uuid
from datetime import datetime

router = APIRouter()

class AgencyBase(BaseModel):
    name: str
    type: str
    hq_contact: Optional[str] = None
    priority: int = 5

@router.get("/all")
def get_agencies():
    conn = get_db()
    rows = conn.execute("SELECT * FROM agencies ORDER BY priority ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.get("/{agency_id}/teams")
def get_agency_teams(agency_id: str):
    conn = get_db()
    rows = conn.execute("SELECT * FROM teams WHERE agency_id=?", (agency_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.get("/directory")
def get_directory():
    """Returns a high-density lookup of all agencies and their total active resources."""
    conn = get_db()
    agencies = conn.execute("SELECT * FROM agencies ORDER BY priority ASC").fetchall()
    result = []
    for a in agencies:
        stats = conn.execute("""
            SELECT 
                COUNT(*) as total_teams,
                SUM(active_size) as total_personnel
            FROM teams WHERE agency_id=?
        """, (a["id"],)).fetchone()
        
        responders = conn.execute("""
            SELECT type, COUNT(*) as count 
            FROM responders 
            WHERE agency_id=? 
            GROUP BY type
        """, (a["id"],)).fetchall()
        
        result.append({
            **dict(a),
            "teams_count": stats["total_teams"] or 0,
            "personnel_count": stats["total_personnel"] or 0,
            "assets": {r["type"]: r["count"] for r in responders}
        })
    conn.close()
    return result
