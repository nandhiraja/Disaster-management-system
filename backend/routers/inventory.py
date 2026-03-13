from fastapi import APIRouter, HTTPException
from database import get_db
from pydantic import BaseModel
from typing import List, Optional
import uuid
from datetime import datetime

router = APIRouter()

class InventoryUpdate(BaseModel):
    owner_id: str
    item_name: str
    category: str
    quantity: float
    unit: str

@router.get("/owner/{owner_id}")
def get_inventory(owner_id: str):
    conn = get_db()
    rows = conn.execute("SELECT * FROM inventory WHERE owner_id=?", (owner_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.put("/update")
def update_inventory(data: InventoryUpdate):
    conn = get_db()
    now = datetime.utcnow().isoformat()
    
    # Check if exists
    existing = conn.execute("SELECT id FROM inventory WHERE owner_id=? AND item_name=?", (data.owner_id, data.item_name)).fetchone()
    
    if existing:
        conn.execute("UPDATE inventory SET quantity=?, updated_at=? WHERE id=?", (data.quantity, now, existing["id"]))
    else:
        conn.execute("""
            INSERT INTO inventory (id, owner_id, item_name, item_category, quantity, unit, updated_at)
            VALUES (?,?,?,?,?,?,?)
        """, (str(uuid.uuid4()), data.owner_id, data.item_name, data.category, data.quantity, data.unit, now))
    
    conn.commit()
    conn.close()
    return {"status": "updated"}

@router.get("/summary/all")
def get_all_inventory():
    conn = get_db()
    rows = conn.execute("SELECT * FROM inventory").fetchall()
    conn.close()
    return [dict(r) for r in rows]
