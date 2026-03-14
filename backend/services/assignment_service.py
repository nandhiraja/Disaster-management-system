import uuid
from datetime import datetime
from database import get_db

class AssignmentError(Exception):
    pass

def assign_mission(sos_id: str, responder_id: str, mission_type: str = "rescue", notes: str = "") -> dict:
    """
    Assignment Service: Creates a mission, updates responder status to busy,
    and updates SOS status to 'assigned'. Safely handles double assignments.
    """
    conn = get_db()
    try:
        # Check if responder is still available
        resp = conn.execute("SELECT status FROM responders WHERE id=?", (responder_id,)).fetchone()
        if not resp:
            raise AssignmentError("Responder not found")
        if resp["status"] != "available":
            raise AssignmentError(f"Responder is currently {resp['status']} and cannot be assigned.")
            
        # Check if SOS is still pending or not closed
        sos = conn.execute("SELECT status FROM sos_requests WHERE sos_id=?", (sos_id,)).fetchone()
        if not sos:
            raise AssignmentError("SOS request not found.")
        if sos["status"] in ["assigned", "in_progress", "rescued", "closed"]:
            raise AssignmentError(f"SOS is already being handled (status: {sos['status']}).")
            
        now = datetime.utcnow().isoformat()
        mission_id = str(uuid.uuid4())
        
        # Update Responder Status
        conn.execute("UPDATE responders SET status='busy', updated_at=? WHERE id=?", (now, responder_id))
        
        # Update SOS Status
        conn.execute("UPDATE sos_requests SET status='assigned', assigned_mission=?, updated_at=? WHERE sos_id=?", 
                     (mission_id, now, sos_id))
                     
        # Create Mission Record
        conn.execute("""
            INSERT INTO missions (id, sos_id, responder_id, type, status, notes, created_at, assigned_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (mission_id, sos_id, responder_id, mission_type, 'assigned', notes, now, now, now))
        
        # Log to Audit
        conn.execute("""
            INSERT INTO audit_logs (id, action, target_id, details, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), "SYSTEM_ASSIGNED_MISSION", mission_id, f"Res: {responder_id} to SOS: {sos_id}", now))
        
        conn.commit()
        return {"mission_id": mission_id, "status": "assigned"}
        
    finally:
        conn.close()
