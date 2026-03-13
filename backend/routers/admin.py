import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import get_db, reset_showcase

router = APIRouter()


@router.post("/reset-showcase")
def do_reset_showcase():
    """Showcase/Demo mode: clear SOS + missions, keep responders as-is."""
    conn = get_db()
    reset_showcase(conn)
    conn.close()
    return {"message": "Showcase reset complete. DB is fresh for demo.", "ok": True}
